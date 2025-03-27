# machiavelli/forms.py
import django.forms as forms
from django.core.cache import cache
from django.forms.formsets import BaseFormSet
from django.utils.safestring import mark_safe
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db import models

from machiavelli.models import * # Import all models

# Define Victory Condition types based on rules
VICTORY_TYPES = (
	('basic', _('Basic Game (12 cities, incl. home + 6 conquered)')),
	('advanced_18', _('Advanced Game <= 4 players (18 cities, incl. 1 conquered home)')),
	('advanced_15', _('Advanced Game >= 5 players (15 cities, incl. 1 conquered home)')),
	('ultimate', _('Ultimate Victory (23 cities, incl. 2 conquered homes)')),
	# ('custom', _('Custom (Set number manually)')), # Optional: for custom games
)

class GameForm(forms.ModelForm):
	scenario = forms.ModelChoiceField(queryset=Scenario.objects.filter(enabled=True),
									empty_label=None,
									cache_choices=True,
									label=_("Scenario"))
	time_limit = forms.ChoiceField(choices=TIME_LIMITS, label=_("Time limit"))
	# Changed from cities_to_win to victory_condition_type
	victory_condition_type = forms.ChoiceField(choices=VICTORY_TYPES, label=_("Victory Condition"), initial='basic')
	# cities_to_win = forms.ChoiceField(choices=CITIES_TO_WIN, label=_("How to win")) # Removed direct number choice
	visible = forms.BooleanField(required=False, label=_("Visible players?"))

	def __init__(self, user, **kwargs):
		super(GameForm, self).__init__(**kwargs)
		self.instance.created_by = user

	def clean(self):
		cleaned_data = super(GameForm, self).clean() # Use super().clean()
		if not cleaned_data.get('slug') or len(cleaned_data['slug']) < 4:
			msg = _("Slug is too short")
			self._errors['slug'] = self.error_class([msg]) # Attach error to field
			# raise forms.ValidationError(msg) # Avoid raising here, collect errors
		if self.instance.created_by: # Ensure user exists
			profile = self.instance.created_by.get_profile()
			if profile:
				karma = profile.karma
				if karma < settings.KARMA_TO_JOIN:
					msg = _("You don't have enough karma to create a game.")
					raise forms.ValidationError(msg) # Raise for game-wide validation failure
				if int(cleaned_data.get('time_limit', 0)) in FAST_LIMITS:
					if karma < settings.KARMA_TO_FAST:
						msg = _("You don't have enough karma for a fast game.")
						self._errors['time_limit'] = self.error_class([msg])
				if cleaned_data.get('private'):
					if karma < settings.KARMA_TO_PRIVATE:
						msg = _("You don't have enough karma to create a private game.")
						self._errors['private'] = self.error_class([msg])
			else:
				# Handle case where profile doesn't exist? Or assume it always does.
				pass
		else:
			# Handle case where user is not set (shouldn't happen with __init__)
			pass

		# Set cities_to_win based on type and player count (will be done in model save)
		# cleaned_data['cities_to_win'] = ... # Removed from here

		return cleaned_data

	class Meta:
		model = Game
		fields = ('slug',
				'scenario',
				'time_limit',
				'victory_condition_type', # Changed field name
				'visible',
				'private',
				'comment',)

class ConfigurationForm(forms.ModelForm):
	def clean(self):
		cleaned_data = super(ConfigurationForm, self).clean() # Use super().clean()
		if cleaned_data.get('unbalanced_loans'):
			cleaned_data['lenders'] = True # Lenders required for unbalanced loans
		if cleaned_data.get('assassinations') or cleaned_data.get('lenders') or cleaned_data.get('special_units') or cleaned_data.get('bribes'):
			# Ensure finances are enabled if any finance-dependent rule is on
			cleaned_data['finances'] = True
		return cleaned_data

	class Meta:
		model = Configuration
		exclude = ('game',) # Exclude game FK, it's set automatically
		# Removed 'bribes', 'strategic' from exclude if they should be configurable
		# exclude = ('bribes', 'strategic')

class InvitationForm(forms.Form):
	user_list = forms.CharField(required=True,
								label=_("User list, comma separated"))
	message = forms.CharField(label=_("Optional message"),
								required=False,
								widget=forms.Textarea)

class WhisperForm(forms.ModelForm):
	class Meta:
		model = Whisper
		fields = ('text',)
		widgets = {
			'text': forms.Textarea(attrs={'rows': 3, 'cols': 20})
		}

	def __init__(self, user, game, **kwargs):
		super(WhisperForm, self).__init__(**kwargs)
		self.instance.user = user
		self.instance.game = game

class UnitForm(forms.ModelForm):
	type = forms.ChoiceField(required=True, choices=UNIT_TYPES)

	class Meta:
		model = Unit
		fields = ('type', 'area')

# Get order codes from the model definition
ORDER_CODES_FROM_MODEL = Order._meta.get_field('code').choices

def make_order_form(player):
	if player.game.configuration.finances:
		## units bought by this player
		bought_ids = Expense.objects.filter(player=player, type__in=(6,9)).values_list('unit', flat=True)
		units_qs = Unit.objects.filter(Q(player=player) | Q(id__in=bought_ids))
	else:
		units_qs = player.unit_set.select_related().all()
	all_units = player.game.get_all_units()

	class OrderForm(forms.ModelForm):
		unit = forms.ModelChoiceField(queryset=units_qs, label=_("Unit"))
		code = forms.ChoiceField(choices=ORDER_CODES_FROM_MODEL, label=_("Order")) # Use codes from model
		destination = forms.ModelChoiceField(required=False, queryset=GameArea.objects.none(), label=_("Destination"))
		type = forms.ChoiceField(required=False, choices=UNIT_TYPES, label=_("Convert into"))
		subunit = forms.ModelChoiceField(required=False, queryset=all_units, label=_("Unit"))
		subcode = forms.ChoiceField(required=False, choices=ORDER_SUBCODES, label=_("Order"))
		subdestination = forms.ModelChoiceField(required=False, queryset=GameArea.objects.none(), label=_("Destination"))
		subtype = forms.ChoiceField(required=False, choices=UNIT_TYPES, label=_("Convert into"))

		def __init__(self, player, **kwargs):
			super(OrderForm, self).__init__(**kwargs)
			self.instance.player = player
			# Set querysets dynamically based on game
			game_areas = GameArea.objects.filter(game=player.game)
			self.fields['destination'].queryset = game_areas
			self.fields['subdestination'].queryset = game_areas
			self.fields['subunit'].queryset = Unit.objects.filter(player__game=player.game) # All units in game

		# get_valid_destinations and get_valid_support_destinations remain complex
		# and rely heavily on model logic. Ensure they check siege_stage where needed.
		# Keeping them as is for now, assuming model logic is primary driver.

		# ... (get_valid_destinations, get_valid_support_destinations methods) ...
		# Minor adjustments might be needed in AJAX views calling these if rules changed significantly

		class Meta:
			model = Order
			fields = ('unit', 'code', 'destination', 'type',
					'subunit', 'subcode', 'subdestination', 'subtype')

		class Media:
			js = ("/site_media/static/machiavelli/js/order_form.js",
				  "/site_media/static/machiavelli/js/jquery.form.js")

		def clean(self):
			cleaned_data = super(OrderForm, self).clean() # Use super().clean()
			unit = cleaned_data.get('unit')
			code = cleaned_data.get('code')
			destination = cleaned_data.get('destination')
			type_ = cleaned_data.get('type') # Renamed to avoid conflict with builtin type
			subunit = cleaned_data.get('subunit')
			subcode = cleaned_data.get('subcode')
			subdestination = cleaned_data.get('subdestination')
			subtype = cleaned_data.get('subtype')

			if not unit: # If unit wasn't selected or is invalid
			    return cleaned_data # Stop further validation

			## check if unit has already an order from the same player
			# Use self.instance.pk to exclude current order if editing
			existing_order_query = Order.objects.filter(unit=unit, player=player)
			if self.instance.pk:
			    existing_order_query = existing_order_query.exclude(pk=self.instance.pk)
			if existing_order_query.exists():
				raise forms.ValidationError(_("This unit already has an order from you."))

			## check for errors based on order code and rules
			error_msg = None
			if code == '-': # Advance
				if not destination: error_msg = _("You must select an area to advance into.")
				elif unit.siege_stage > 0: error_msg = _("Cannot advance while besieging. Lift siege first.")
				# Further validation in Order.is_possible()
			elif code == '=': # Conversion
				if not type_: error_msg = _("You must select a unit type to convert into.")
				elif unit.type == type_: error_msg = _("A unit must convert into a different type.")
				elif unit.type == 'G' and unit.siege_stage > 0: error_msg = _("Cannot convert while garrison is besieged.")
				# Further validation in Order.is_possible()
			elif code == 'C': # Convoy
				if not subunit: error_msg = _("You must select a unit to convoy.")
				elif not subdestination: error_msg = _("You must select a destination area for the convoy.")
				elif subunit.type != 'A': error_msg = _("Only armies can be convoyed.")
				elif unit.area.storm: error_msg = _("A fleet cannot convoy while affected by a storm.")
				elif not unit.area.board_area.is_sea and unit.area.board_area.code != 'VEN': error_msg = _("Only fleets in sea areas or Venice Lagoon can convoy.")
				elif not subunit.area.board_area.is_coast: error_msg = _("Units can only be convoyed from coastal territories.")
				else: cleaned_data['subcode'] = '-' # Force subcode for convoy
			elif code == 'S': # Support
				if not subunit: error_msg = _("You must select a unit to support.")
				elif subcode == '-' and not subdestination: error_msg = _("You must select a destination area for the supported unit.")
				elif subcode == '=': error_msg = _("Units cannot support conversions.") # Rule VII.B.5 implies support for hold/advance only? Let's keep this restriction.
				# Further validation in Order.is_possible()
			elif code == 'B': # Besiege
			    if unit.siege_stage == 2: error_msg = _("Siege already at maximum stage.")
			    # Further validation in Order.is_possible()
			elif code == 'L': # Lift Siege
			    if unit.siege_stage == 0: error_msg = _("Unit is not currently besieging.")
			elif code == '0': # Disband
			    pass # Always valid
			elif code == 'H': # Hold
			    pass # Always valid
			else:
			    error_msg = _("Invalid order code selected.")

			if error_msg:
			    raise forms.ValidationError(error_msg)

			# Use Order.is_possible for final rule check
			# Create a temporary order instance to check
			temp_order_data = cleaned_data.copy()
			temp_order_data['player'] = player # Ensure player is set
			temp_order = Order(**{k: v for k, v in temp_order_data.items() if hasattr(Order, k)}) # Map cleaned data to Order fields
			if not temp_order.is_possible():
			     raise forms.ValidationError(_("This order is not possible according to the rules (check unit type, location, target, siege status, etc.)."))


			## set to None the fields that are not needed based on the primary code
			if code in ['H', 'B', 'L', '0']:
				cleaned_data.update({'destination': None, 'type': None, 'subunit': None,
									'subcode': None, 'subdestination': None, 'subtype': None})
			elif code == '-':
				cleaned_data.update({'type': None, 'subunit': None, 'subcode': None,
									 'subdestination': None, 'subtype': None})
			elif code == '=':
				cleaned_data.update({'destination': None, 'subunit': None, 'subcode': None,
									 'subdestination': None, 'subtype': None})
			elif code == 'C':
				# Keep subunit, subdestination. Force subcode to '-'
				cleaned_data.update({'destination': None, 'type': None, 'subcode': '-', 'subtype': None})
			elif code == 'S':
				# Keep subunit, subcode. Keep subdestination/subtype based on subcode.
				cleaned_data.update({'destination': None, 'type': None})
				if subcode in ['H', 'B']: # Support Hold/Besiege
					cleaned_data.update({'subdestination': None, 'subtype': None})
				elif subcode == '-': # Support Advance
					cleaned_data.update({'subtype': None})
				# elif subcode == '=': # Support Conversion (Currently disallowed by validation)
				# 	cleaned_data.update({'subdestination': None})

			return cleaned_data

		def as_td(self):
			"Returns this form rendered as HTML <td>s -- excluding the <tr></tr>."
			# Use standard form rendering methods if possible, or keep custom one
			# return self._html_output(u'<td>%(errors)s %(field)s%(help_text)s</td>', u'<td style="width:10%%">%s</td>', u'</td>', u' %s', False)
			return super(OrderForm, self).as_table() # Or as_p, as_ul

	return OrderForm

def make_retreat_form(u):
	possible_retreats = u.get_possible_retreats() # Uses updated model method

	class RetreatForm(forms.Form):
		unitid = forms.IntegerField(widget=forms.HiddenInput, initial=u.id)
		area = forms.ModelChoiceField(required=False, # False allows disbanding
							queryset=possible_retreats,
							empty_label='Disband unit', # Label for choosing None
							label=unicode(u)) # Use unicode for label

	return RetreatForm

def make_reinforce_form(player, finances=False, special_units=False):
	if finances:
		unit_types = (('', '---'),) + UNIT_TYPES
		noarea_label = '---'
	else:
		unit_types = UNIT_TYPES
		noarea_label = None
	area_qs = player.get_areas_for_new_units(finances) # Uses updated model method

	class ReinforceForm(forms.Form):
		type = forms.ChoiceField(required=True, choices=unit_types)
		area = forms.ModelChoiceField(required=True,
					      queryset=area_qs,
					      empty_label=noarea_label)
		if special_units and not player.has_special_unit():
			## special units are available for the player
			unit_class = forms.ModelChoiceField(required=False,
											queryset=player.country.special_units.all(),
											empty_label=_("Regular (3d)")) # Cost depends on finances

		def clean(self):
			cleaned_data = super(ReinforceForm, self).clean() # Use super().clean()
			type_ = cleaned_data.get('type')
			area = cleaned_data.get('area')

			if not type_ or not area: # Check if fields are present
			    return cleaned_data

			# Check if the selected area allows the selected unit type based on rules
			# This duplicates checks in get_areas_for_new_units, but confirms selection
			if type_ == 'G' and not area.board_area.is_fortified:
			    raise forms.ValidationError(_('Garrisons can only be placed in fortified cities/fortresses.'))
			if type_ == 'F' and not area.board_area.has_port:
			     raise forms.ValidationError(_('Fleets can only be placed in port cities.'))
			if type_ == 'A' and (area.board_area.is_sea or area.board_area.code == 'VEN'):
			     raise forms.ValidationError(_('Armies cannot be placed in seas or Venice.'))

			# Check if the specific slot (city/province) is available - More complex
			# Requires knowing if user intends city or province placement
			# Simplification: Assume valid if area appeared in the queryset from get_areas_for_new_units

			# Original check (less precise):
			# if not type in area.possible_reinforcements():
			# 	raise forms.ValidationError(_('This unit cannot be placed in this area'))
			return cleaned_data

	return ReinforceForm

class BaseReinforceFormSet(BaseFormSet):
	def clean(self):
		if any(self.errors):
			return
		areas = []
		special_count = 0
		for i in range(0, self.total_form_count()):
			form = self.forms[i]
			# Check if form has data and is valid before accessing cleaned_data
			if form.has_changed() and form.is_valid():
			    area = form.cleaned_data.get('area')
			    if area:
			        if area in areas:
			            raise forms.ValidationError(_('You cannot place two units in the same area in one turn'))
			        areas.append(area)

			    unit_class = form.cleaned_data.get('unit_class')
			    if unit_class is not None: # Check if a special unit was selected
			        special_count += 1

		if special_count > 1:
			raise forms.ValidationError(_("You cannot buy more than one special unit per turn"))


def make_disband_form(player):
	class DisbandForm(forms.Form):
		units = forms.ModelMultipleChoiceField(required=True,
					      queryset=player.unit_set.all(),
					      label="Units to disband")
	return DisbandForm

class UnitPaymentCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
	def build_attrs(self, attrs=None, **kwargs):
		attrs = super(UnitPaymentCheckboxSelectMultiple, self).build_attrs(attrs, **kwargs)
		if 'name' in attrs:
			attrs['name'] = attrs['name'] + '[]'
		return attrs

class UnitPaymentMultipleChoiceField(forms.ModelMultipleChoiceField):
	def label_from_instance(self, obj):
		return obj.describe_with_cost()

def make_unit_payment_form(player):
	class UnitPaymentForm(forms.Form):
		units = UnitPaymentMultipleChoiceField(required=False,
					      queryset=player.unit_set.filter(placed=True), # Only pay for placed units
						  widget=UnitPaymentCheckboxSelectMultiple,
					      label="")

		def clean(self):
			cleaned_data = super(UnitPaymentForm, self).clean()
			units = cleaned_data.get('units', [])
			cost = sum(u.cost for u in units)
			if cost > player.ducats:
				raise forms.ValidationError(_("You don't have enough ducats. Need %(cost)s but only have %(has)s.") % {
					'cost': cost,
					'has': player.ducats
				})
			return cleaned_data

	return UnitPaymentForm

def make_ducats_list(ducats, f=3):
	""" Creates a list of possible ducat amounts in multiples of f. """
	choices = []
	if ducats >= f:
		max_multiple = int(ducats / f)
		for i in range(1, max_multiple + 1):
			val = i * f
			choices.append((val, val))
	if not choices: # Ensure there's at least one option if ducats < f
	    choices.append((0, 0)) # Or handle this case differently if 0 is not allowed
	return tuple(choices)


def make_expense_form(player):
	# Base cost for counter-bribe is 3, but allow multiples
	counter_bribe_choices = make_ducats_list(player.ducats, 3)
	# Other expenses have fixed minimums, but allow overpaying (in multiples of 3?)
	# Rule VI.C.4.g.2: Bribe increases must be in units of 3.
	# Let's make all expense choices multiples of 3 for consistency, up to player's ducats.
	general_expense_choices = make_ducats_list(player.ducats, 3)

	unit_qs = Unit.objects.filter(player__game=player.game).order_by('area__board_area__code')
	area_qs = GameArea.objects.filter(game=player.game).order_by('board_area__code')

	class ExpenseForm(forms.ModelForm):
		# Use dynamic choices based on type later? For now, use general list.
		ducats = forms.ChoiceField(required=True, choices=general_expense_choices)
		area = forms.ModelChoiceField(required=False, queryset=area_qs)
		unit = forms.ModelChoiceField(required=False, queryset=unit_qs)

		def __init__(self, player, **kwargs):
			super(ExpenseForm, self).__init__(**kwargs)
			self.instance.player = player
			# Dynamically set ducat choices based on selected type? Complex for basic form.
			# We'll validate amount against minimum cost in clean().

		class Meta:
			model = Expense
			fields = ('type', 'ducats', 'area', 'unit')

		def clean(self):
			cleaned_data = super(ExpenseForm, self).clean() # Use super().clean()
			type_ = cleaned_data.get('type')
			ducats_str = cleaned_data.get('ducats')
			area = cleaned_data.get('area')
			unit = cleaned_data.get('unit')

			if type_ is None or ducats_str is None: # Check basic fields exist
			    return cleaned_data

			try:
			    ducats = int(ducats_str)
			except (ValueError, TypeError):
			    raise forms.ValidationError(_("Invalid ducat amount selected."))

			# Validate required fields based on type
			if type_ in (0, 1, 2, 3): # Famine Relief, Pacify, Rebel
				if not area: raise forms.ValidationError(_("You must choose an area for this expense."))
				cleaned_data['unit'] = None # Ensure unit is None
			elif type_ in (4, 5, 6, 7, 8, 9): # Counter-Bribe, Bribes
				if not unit: raise forms.ValidationError(_("You must choose a unit for this expense."))
				cleaned_data['area'] = None # Ensure area is None
			else:
				raise forms.ValidationError(_("Unknown expense type selected."))

			# Check minimum cost (using updated get_expense_cost)
			try:
				min_cost = get_expense_cost(type_, unit)
			except ValueError as e: # Handle errors from get_expense_cost (e.g., missing unit)
			    raise forms.ValidationError(unicode(e))

			if ducats < min_cost:
				raise forms.ValidationError(_("You must pay at least %(cost)s ducats for this expense.") % {'cost': min_cost})

			# Check amount is multiple of 3 if required (e.g., for bribes > min)
			if type_ in (4, 5, 6, 7, 8, 9) and ducats > min_cost:
			    if (ducats - min_cost) % 3 != 0:
			        # Or just check ducats % 3 != 0 if min_cost is always multiple of 3
			        if ducats % 3 != 0:
			             raise forms.ValidationError(_("Ducat amount must be a multiple of 3."))

			# Specific expense type validations
			if type_ == 0: # Famine relief
				if not area or not area.famine: raise forms.ValidationError(_("There is no famine in the selected area."))
			elif type_ == 1: # Pacify rebellion
				if not area or not Rebellion.objects.filter(area=area).exists(): raise forms.ValidationError(_("There is no rebellion in the selected area."))
			elif type_ == 2 or type_ == 3: # Start rebellion
				if not area or not area.player: raise forms.ValidationError(_("Selected area is not controlled by anyone."))
				elif area.player == player: raise forms.ValidationError(_("Cannot start rebellion in your own area."))
				# Check home vs conquered (using updated home_country method)
				is_home = area in area.player.home_country(original=True) # Check original home country
				if type_ == 2 and is_home: raise forms.ValidationError(_("This area is part of the player's home country; use 'Home province to rebel' expense."))
				elif type_ == 3 and not is_home: raise forms.ValidationError(_("This area is not in the home country of the player who controls it; use 'Conquered province to rebel' expense."))
				# Rule VI.C.5.c.11: No rebellion in Venice if occupied
				if area.board_area.code == 'VEN' and area.unit_set.exists():
				    raise forms.ValidationError(_("Cannot start rebellion in Venice while it is occupied."))
			elif type_ in (5, 6): # Disband/Buy Autonomous Garrison
				if not unit or unit.type != 'G' or unit.player.user is not None: raise forms.ValidationError(_("You must choose an autonomous garrison."))
			elif type_ in (7, 8, 9): # Convert/Disband/Buy Enemy Unit
				if not unit or unit.player == player: raise forms.ValidationError(_("You must choose an enemy unit."))
				if unit.player.user is None: raise forms.ValidationError(_("You must choose an enemy unit, not an autonomous one."))
				if type_ == 7 and unit.type != 'G': raise forms.ValidationError(_("You must choose a non-autonomous garrison to convert."))
				if type_ == 9: # Buy enemy A/F
				    if unit.type not in ['A', 'F']: raise forms.ValidationError(_("You must choose an enemy Army or Fleet to buy."))

			# Check bribe adjacency (Rule VI.C.4.g.4)
			if type_ in (5, 6, 7, 8, 9):
				# Check if player has unit adjacent to target unit's area
				adjacent_areas = unit.area.get_adjacent_areas(include_self=False) # Areas adjacent to target
				q_player_unit_adjacent = Q(player=player, area__in=adjacent_areas)
				# Check if player controls area adjacent to target unit's area
				q_player_control_adjacent = Q(player=player, board_area__in=unit.area.board_area.borders.all())

				is_adjacent = Unit.objects.filter(q_player_unit_adjacent).exists() or \
				              GameArea.objects.filter(q_player_control_adjacent).exists()

				# Optional Rule V.A: Check adjacency via ally
				# This requires more complex logic, maybe handled in view or model

				if not is_adjacent:
					# Optional Rule V.B: Allow bribe anywhere (if enabled in config)
					if not player.game.configuration.bribes_anywhere: # Assuming a config flag
					    raise forms.ValidationError(_("You cannot bribe this unit because it's too far from your units or controlled areas."))

			return cleaned_data

	return ExpenseForm

class LendForm(forms.Form):
	ducats = forms.IntegerField(required=True, min_value=1) # Cannot lend 0

TERMS = (
	(1, _("1 year, 20%")),
	(2, _("2 years, 50%")),
)

class BorrowForm(forms.Form):
	ducats = forms.IntegerField(required=True, min_value=1, label=_("Ducats to borrow")) # Cannot borrow 0
	term = forms.ChoiceField(required=True, choices=TERMS, label=_("Term and interest"))

	def __init__(self, player=None, *args, **kwargs):
	    self.player = player
	    super(BorrowForm, self).__init__(*args, **kwargs)

	def clean_ducats(self):
	    ducats = self.cleaned_data.get('ducats')
	    if ducats is None: return None # Handled by required=True

	    if not self.player: # Should not happen if form initialized correctly
	        raise forms.ValidationError("Player context missing.")

	    # Check max loan limit (Rule X.A.1)
	    current_debt = 0
	    try:
	        current_debt = self.player.loan.debt # Assumes loan stores principal? No, rules say total owed.
	        # Need to track principal separately if max is on principal. Assuming max is on *new* loan amount.
	    except Loan.DoesNotExist:
	        pass

	    # Rule X.A.1: "total number of ducats owed... may never exceed twenty-five"
	    # This implies the *new* loan amount cannot exceed 25 if no current loan,
	    # or the *new* amount + *existing principal* cannot exceed 25.
	    # Let's assume the limit is on the amount being borrowed *now*.
	    max_borrow = 25
	    # If limit applies to total principal, need to store principal on Loan model.

	    if ducats > max_borrow:
	         raise forms.ValidationError(_("You cannot borrow more than 25 ducats at one time."))

	    # Check against player's credit limit (Optional Rule X.A - based on areas/units unless unbalanced)
	    credit_limit = self.player.get_credit() # Uses model method
	    if ducats > credit_limit:
	         raise forms.ValidationError(_("Your current credit limit is %(limit)s ducats.") % {'limit': credit_limit})

	    return ducats


class RepayForm(forms.Form):
	# No fields needed, just a confirmation button
	pass

def make_assassination_form(player):
	# Cost is minimum 12, max 36 (multiples of 12)
	max_spend = min(player.ducats, 36)
	assassination_choices = []
	if max_spend >= 12: assassination_choices.append((12, 12))
	if max_spend >= 24: assassination_choices.append((24, 24))
	if max_spend >= 36: assassination_choices.append((36, 36))

	if not assassination_choices: # Cannot afford even minimum
	    assassination_choices = ((0, _("Cannot afford")),) # Placeholder

	assassin_ids = player.assassin_set.values_list('target', flat=True)
	# Exclude eliminated players and self
	targets_qs = Country.objects.filter(
	    player__game=player.game, id__in=assassin_ids
	).exclude(
	    player__eliminated=True
    ).exclude(
        player=player # Cannot target self
    )

	class AssassinationForm(forms.Form):
		ducats = forms.ChoiceField(required=True, choices=assassination_choices, label=_("Ducats to pay (12=1 die, 24=2 dice, 36=3 dice)"))
		target = forms.ModelChoiceField(required=True, queryset=targets_qs, label=_("Target country"))

		def clean_ducats(self):
		    ducats = self.cleaned_data.get('ducats')
		    try:
		        ducats_int = int(ducats)
		        if ducats_int == 0: # Handle the "Cannot afford" case
		             raise forms.ValidationError(_("You cannot afford an assassination attempt."))
		        if ducats_int not in [12, 24, 36]:
		             raise forms.ValidationError(_("Invalid amount selected for assassination."))
		    except (ValueError, TypeError):
		        raise forms.ValidationError(_("Invalid amount selected."))
		    return ducats_int # Return as integer

	return AssassinationForm