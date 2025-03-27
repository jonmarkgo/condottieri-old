import django.forms as forms
from django.core.cache import cache
from django.forms.formsets import BaseFormSet
from django.utils.safestring import mark_safe
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db import models
from .models import VICTORY_TYPES # Import from models

class GameForm(forms.ModelForm):
    scenario = forms.ModelChoiceField(queryset=Scenario.objects.filter(enabled=True),
                                    empty_label=None,
                                    cache_choices=True,
                                    label=_("Scenario"))
    time_limit = forms.ChoiceField(choices=TIME_LIMITS, label=_("Time limit"))
    # Use victory_condition_type field with choices from VICTORY_TYPES
    victory_condition_type = forms.ChoiceField(choices=VICTORY_TYPES, label=_("Victory Condition"), initial='basic')
    # cities_to_win = forms.ChoiceField(choices=CITIES_TO_WIN, label=_("How to win")) # REMOVED
    visible = forms.BooleanField(required=False, label=_("Visible players?"))

    def __init__(self, user, **kwargs):
        super(GameForm, self).__init__(**kwargs)
        self.instance.created_by = user
        # Dynamically adjust victory condition choices based on scenario players?
        # Example: Remove advanced_18 if scenario players >= 5
        # scenario_id = self.initial.get('scenario') or (self.instance and self.instance.scenario_id)
        # if scenario_id:
        #     try:
        #         scenario = Scenario.objects.get(pk=scenario_id)
        #         num_players = scenario.get_slots()
        #         current_choices = list(self.fields['victory_condition_type'].choices)
        #         if num_players >= 5:
        #             current_choices = [c for c in current_choices if c[0] != 'advanced_18']
        #         else: # num_players <= 4
        #             current_choices = [c for c in current_choices if c[0] != 'advanced_15']
        #         self.fields['victory_condition_type'].choices = current_choices
        #     except Scenario.DoesNotExist:
        #         pass # Keep default choices if scenario not found

    def clean(self):
        cleaned_data = super(GameForm, self).clean()
        # ... (slug validation) ...
        if not cleaned_data.get('slug') or len(cleaned_data['slug']) < 4:
            msg = _("Slug is too short")
            self.add_error('slug', msg) # Use add_error

        # ... (karma validation - unchanged) ...
        if self.instance.created_by:
            profile = self.instance.created_by.get_profile()
            if profile:
                karma = profile.karma
                if karma < settings.KARMA_TO_JOIN:
                    raise forms.ValidationError(_("You don't have enough karma to create a game."))
                if int(cleaned_data.get('time_limit', 0)) in FAST_LIMITS:
                    if karma < settings.KARMA_TO_FAST:
                        self.add_error('time_limit', _("You don't have enough karma for a fast game."))
                if cleaned_data.get('private'):
                    if karma < settings.KARMA_TO_PRIVATE:
                        self.add_error('private', _("You don't have enough karma to create a private game."))
            else: # Handle profile missing case
                 raise forms.ValidationError(_("User profile not found."))
        else: # Should not happen
             raise forms.ValidationError(_("Game creator not set."))


        # Validate victory condition choice against player count
        scenario = cleaned_data.get('scenario')
        vic_type = cleaned_data.get('victory_condition_type')
        if scenario and vic_type:
             num_players = scenario.get_slots()
             if vic_type == 'advanced_18' and num_players >= 5:
                  self.add_error('victory_condition_type', _("Advanced (18 cities) requires 4 or fewer players."))
             elif vic_type == 'advanced_15' and num_players <= 4:
                  self.add_error('victory_condition_type', _("Advanced (15 cities) requires 5 or more players."))

        # cities_to_win is set in model save, no need to clean here.

        return cleaned_data

    class Meta:
        model = Game
        fields = ('slug',
                'scenario',
                'time_limit',
                'victory_condition_type', # Use the type field
                'visible',
                'private',
                'comment',)

class ConfigurationForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super(ConfigurationForm, self).clean()
        # Optional Rule X requires Finances
        if cleaned_data.get('lenders') or cleaned_data.get('unbalanced_loans'):
            cleaned_data['finances'] = True
        # Optional Rule IV requires Finances
        if cleaned_data.get('special_units'):
            cleaned_data['finances'] = True
        # Advanced Rule VI requires Finances
        if cleaned_data.get('assassinations') or cleaned_data.get('bribes'):
            cleaned_data['finances'] = True
        # Optional Rule III (Disasters) don't strictly require finances, but Famine Relief does
        # No automatic enabling needed here.

        return cleaned_data

    class Meta:
        model = Configuration
        # Exclude game FK, it's set automatically in Game.save()
        exclude = ('game',)
        # Ensure all boolean flags are included unless they should never be user-settable
        # fields = '__all__' # Or list all fields explicitly if exclude isn't sufficient
		
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
from collections import defaultdict # Add defaultdict
# Get order codes from the model definition
ORDER_CODES_FROM_MODEL = Order._meta.get_field('code').choices
# Define Coast Choices dynamically? For now, use model choices.
COAST_CHOICES = Unit._meta.get_field('coast').choices # Get choices like (('nc', 'NC'), ...)
BLANK_COAST_CHOICE = (('', '---'),) # Add a blank option

def make_order_form(player):
    game = player.game # Get game object
    # Determine units the player can order
    units_qs = Unit.objects.none() # Start with empty queryset
    if player.user: # Ensure player is not autonomous
        # Base: Units owned by the player
        q_owned = Q(player=player)
        # Advanced: Include units bought via bribe this turn (requires tracking)
        # Simplification: Assume only owned units can be ordered via this form for now.
        # Bribe logic might need separate handling or flag on unit.
        # if game.configuration.finances:
        #    bought_ids = Expense.objects.filter(player=player, type__in=(6, 10), confirmed=False).values_list('unit', flat=True) # Unconfirmed buys?
        #    q_owned |= Q(id__in=bought_ids)

        units_qs = Unit.objects.filter(q_owned) \
                        .select_related('area__board_area', 'player__country') \
                        .order_by('type', 'area__board_area__code') # Consistent ordering

    # All units in the game (for subunit selection)
    all_units_qs = Unit.objects.filter(player__game=game) \
                        .select_related('area__board_area', 'player__country') \
                        .order_by('player__country__name', 'type', 'area__board_area__code')

    class OrderForm(forms.ModelForm):
        unit = forms.ModelChoiceField(queryset=units_qs, label=_("Unit"), required=True)
        code = forms.ChoiceField(choices=ORDER_CODES_FROM_MODEL, label=_("Order"), required=True)
        # Destination for Advance (-), Support Move (S -)
        destination = forms.ModelChoiceField(required=False, queryset=GameArea.objects.none(), label=_("Destination"))
        # Coast for Destination (if applicable)
        destination_coast = forms.ChoiceField(choices=BLANK_COAST_CHOICE + COAST_CHOICES, required=False, label=_("Dest. Coast"))

        # Type for Conversion (=)
        type = forms.ChoiceField(required=False, choices=UNIT_TYPES, label=_("Convert into"))

        # Subunit for Support (S), Convoy (C)
        subunit = forms.ModelChoiceField(required=False, queryset=all_units_qs, label=_("Target Unit"))
        # Subcode for Support (S)
        subcode = forms.ChoiceField(required=False, choices=ORDER_SUBCODES, label=_("Target Order"))
        # Subdestination for Support Move (S -), Convoy (C -)
        subdestination = forms.ModelChoiceField(required=False, queryset=GameArea.objects.none(), label=_("Target Dest."))
        # Coast for Subdestination (if applicable)
        subdestination_coast = forms.ChoiceField(choices=BLANK_COAST_CHOICE + COAST_CHOICES, required=False, label=_("Target Dest. Coast"))

        # Subtype for Support Conversion (S =) - Currently disallowed by rules check
        subtype = forms.ChoiceField(required=False, choices=UNIT_TYPES, label=_("Target Type"))

        def __init__(self, player, **kwargs):
            super(OrderForm, self).__init__(**kwargs)
            self.instance.player = player # Set player instance for saving
            game_areas = GameArea.objects.filter(game=player.game).select_related('board_area') # Optimize
            self.fields['destination'].queryset = game_areas
            self.fields['subdestination'].queryset = game_areas
            # Queryset for subunit already set above

        class Meta:
            model = Order
            # Include new coast fields
            fields = ('unit', 'code', 'destination', 'destination_coast', 'type',
                      'subunit', 'subcode', 'subdestination', 'subdestination_coast', 'subtype')

        class Media:
            # JS file needs updates to handle showing/hiding/populating coast fields
            js = (settings.STATIC_URL + "machiavelli/js/jquery.form.js", # Use STATIC_URL
                  settings.STATIC_URL + "machiavelli/js/order_form.js",) # Needs update!

        def clean(self):
            cleaned_data = super(OrderForm, self).clean()
            unit = cleaned_data.get('unit')
            code = cleaned_data.get('code')
            destination = cleaned_data.get('destination')
            destination_coast = cleaned_data.get('destination_coast')
            type_ = cleaned_data.get('type')
            subunit = cleaned_data.get('subunit')
            subcode = cleaned_data.get('subcode')
            subdestination = cleaned_data.get('subdestination')
            subdestination_coast = cleaned_data.get('subdestination_coast')
            subtype = cleaned_data.get('subtype')

            if not unit: return cleaned_data # Stop if unit not selected

            # --- Basic Field Requirements by Order Code ---
            error_msg = None
            if code == '-': # Advance
                if not destination: error_msg = _("Advance requires a destination area.")
            elif code == '=': # Conversion
                if not type_: error_msg = _("Conversion requires a target unit type.")
            elif code == 'C': # Convoy
                if not subunit: error_msg = _("Convoy requires a target unit (Army).")
                elif subunit.type != 'A': error_msg = _("Only armies can be convoyed.")
                elif not subdestination: error_msg = _("Convoy requires a destination area for the army.")
                cleaned_data['subcode'] = '-' # Force subcode for convoy
            elif code == 'S': # Support
                if not subunit: error_msg = _("Support requires a target unit.")
                if not subcode: subcode = 'H'; cleaned_data['subcode'] = 'H' # Default to Support Hold
                if subcode == '-' and not subdestination: error_msg = _("Support Move requires a destination area.")
                # if subcode == '=' and not subtype: error_msg = _("Support Conversion requires a target type.") # If supporting conversion
            elif code == 'B': # Besiege
                 pass # No extra fields needed
            elif code == 'L': # Lift Siege
                 pass # No extra fields needed
            elif code == '0': # Disband
                 pass # No extra fields needed
            elif code == 'H': # Hold
                 pass # No extra fields needed
            else:
                 error_msg = _("Invalid order code selected.")

            if error_msg:
                # Use add_error for field-specific or non-field errors
                # Guess the most relevant field or use None for non-field
                field_key = None
                if code in ['-', 'C', 'S'] and 'destination' in error_msg.lower(): field_key = 'destination' if code == '-' else 'subdestination'
                elif code in ['=', 'S'] and 'type' in error_msg.lower(): field_key = 'type' if code == '=' else 'subtype'
                elif code in ['C', 'S'] and 'unit' in error_msg.lower(): field_key = 'subunit'
                self.add_error(field_key, error_msg)
                return cleaned_data # Stop further validation if basic fields missing

            # --- Coast Validation ---
            dest_requires_coast = False
            subdest_requires_coast = False

            # Check Destination Coast
            if destination and destination.board_area.has_multiple_coasts():
                 # Fleet advancing to multi-coast OR Army being convoyed to multi-coast
                 if (code == '-' and unit.type == 'F') or code == 'C':
                     dest_requires_coast = True

            if dest_requires_coast and not destination_coast:
                 self.add_error('destination_coast', _("Must specify coast for this destination."))
            elif not dest_requires_coast and destination_coast:
                 # Clear coast if specified but not needed/allowed
                 cleaned_data['destination_coast'] = None

            # Check Subdestination Coast (for Support Move / Convoy)
            if subdestination and subdestination.board_area.has_multiple_coasts():
                 # Convoying army to multi-coast OR Supporting fleet move to multi-coast
                 if code == 'C' or (code == 'S' and subcode == '-' and subunit and subunit.type == 'F'):
                      subdest_requires_coast = True

            if subdest_requires_coast and not subdestination_coast:
                 self.add_error('subdestination_coast', _("Must specify coast for this support/convoy destination."))
            elif not subdest_requires_coast and subdestination_coast:
                 # Clear coast if specified but not needed/allowed
                 cleaned_data['subdestination_coast'] = None


            # --- Final Rule Check using Order.is_possible() ---
            # Create a temporary Order instance with cleaned data to test possibility
            temp_order_data = cleaned_data.copy()
            temp_order_data['player'] = player # Ensure player is set
            # Ensure only valid fields are passed to Order constructor
            valid_order_fields = {f.name for f in Order._meta.get_fields()}
            init_kwargs = {k: v for k, v in temp_order_data.items() if k in valid_order_fields and v is not None}

            try:
                 # Check if unit already has a confirmed order from this player
                 # Allow replacing unconfirmed orders
                 existing_order = Order.objects.filter(unit=unit, player=player, confirmed=True).first()
                 if existing_order and (not self.instance or self.instance.pk != existing_order.pk):
                      raise forms.ValidationError(_("This unit already has a confirmed order from you."))

                 # Create temporary order for validation
                 temp_order = Order(**init_kwargs)
                 if not temp_order.is_possible():
                      # Provide a more generic error, as specific reason is hard to pinpoint here
                      # is_possible() should ideally log the specific failure reason
                      raise forms.ValidationError(_("This order (including coast selection) is not possible according to the rules."))
            except Exception as e:
                 # Catch potential errors during temp order creation or validation
                 self.add_error(None, f"Validation Error: {e}")
                 return cleaned_data


            # --- Clear Unused Fields ---
            # Clear fields based on primary code to ensure clean data saving
            if code in ['H', 'B', 'L', '0']:
                cleaned_data.update({'destination': None, 'destination_coast': None, 'type': None, 'subunit': None,
                                     'subcode': None, 'subdestination': None, 'subdestination_coast': None, 'subtype': None})
            elif code == '-':
                cleaned_data.update({'type': None, 'subunit': None, 'subcode': None,
                                     'subdestination': None, 'subdestination_coast': None, 'subtype': None})
                # Keep destination, destination_coast
            elif code == '=':
                cleaned_data.update({'destination': None, 'destination_coast': None, 'subunit': None, 'subcode': None,
                                     'subdestination': None, 'subdestination_coast': None, 'subtype': None})
                # Keep type
            elif code == 'C':
                cleaned_data.update({'destination': None, 'destination_coast': None, 'type': None, 'subcode': '-', 'subtype': None})
                # Keep subunit, subdestination, subdestination_coast (force subcode='-')
            elif code == 'S':
                cleaned_data.update({'destination': None, 'destination_coast': None, 'type': None})
                # Keep subunit, subcode
                if subcode in ['H', 'B']: # Assuming support besiege is like support hold
                    cleaned_data.update({'subdestination': None, 'subdestination_coast': None, 'subtype': None})
                elif subcode == '-':
                    cleaned_data.update({'subtype': None})
                    # Keep subdestination, subdestination_coast
                # elif subcode == '=': # Support Conversion (Currently disallowed by is_possible)
                #     cleaned_data.update({'subdestination': None, 'subdestination_coast': None})
                #     # Keep subtype

            return cleaned_data

    return OrderForm

@login_required
def get_valid_destinations(request, slug):
    """
    AJAX view to get valid destinations for a unit based on order type ('-' or '=').
    For '-', includes direct moves and potential convoy moves, plus valid coasts.
    For '=', includes the current area and valid conversion types.
    """
    game = get_object_or_404(Game, slug=slug)
    unit_id = request.GET.get('unit_id')
    order_type = request.GET.get('order_type')

    response_data = {'destinations': []} # Default empty

    try:
        # Select related area and board_area for efficiency
        unit = Unit.objects.select_related('area__board_area', 'player').get(id=unit_id, player__game=game)
        player = Player.objects.get(user=request.user, game=game) # Ensure request user is in game

        # --- Permission Check ---
        can_order = (unit.player == player)
        # Add finance check if implementing bribe-ordering
        # if not can_order and game.configuration.finances:
        #     can_order = Expense.objects.filter(player=player, type__in=(6, 9), unit=unit, confirmed=True).exists() # Example check

        if not can_order:
             if logging: logging.warning(f"User {request.user} cannot order unit {unit_id}")
             return JsonResponse(response_data)

        # --- Process Order Type ---
        destinations_list = [] # Use a temporary list

        if order_type == '-': # Advance
            # 1. Check Preconditions
            if unit.siege_stage > 0:
                if logging: logging.info(f"Unit {unit_id} cannot advance, siege_stage > 0")
                return JsonResponse(response_data) # Cannot advance if besieging

            # 2. Find Directly Adjacent Valid Destinations
            valid_direct_moves = []
            bordering_areas = unit.area.board_area.borders.all() # Get Area objects
            bordering_game_areas = GameArea.objects.filter(
                game=game,
                board_area__in=bordering_areas
            ).select_related('board_area') # Get relevant GameAreas efficiently

            for dest_ga in bordering_game_areas:
                # Check adjacency using the unit's current coast
                if unit.area.board_area.is_adjacent(
                    dest_ga.board_area,
                    fleet=(unit.type == 'F'),
                    source_unit_coast=unit.coast # Pass current coast
                ) and dest_ga.board_area.accepts_type(unit.type):
                    valid_direct_moves.append(dest_ga)
                    destinations_list.append({
                        'id': dest_ga.id,
                        'name': dest_ga.board_area.name,
                        'code': dest_ga.board_area.code,
                        'coasts': dest_ga.board_area.get_coast_list(), # Add coasts info
                        'convoy_only': False
                    })

            # 3. Find Potential Convoy Destinations (Army on Coast only)
            if unit.type == 'A' and unit.area.board_area.is_coast:
                # Get IDs of areas already found as direct moves
                direct_move_ids = [ga.id for ga in valid_direct_moves]
                # Find all coastal areas in the game, excluding current area and direct moves
                potential_convoy_gareas = GameArea.objects.filter(
                    game=game,
                    board_area__is_coast=True
                ).exclude(
                    id__in=direct_move_ids + [unit.area.id] # Exclude current and direct
                ).select_related('board_area')

                for dest_ga in potential_convoy_gareas:
                    # No complex path check here, just offer all other coastal as options
                    destinations_list.append({
                        'id': dest_ga.id,
                        'name': dest_ga.board_area.name,
                        'code': dest_ga.board_area.code,
                        'coasts': dest_ga.board_area.get_coast_list(), # Add coasts info
                        'convoy_only': True
                    })

            response_data['destinations'] = destinations_list # Assign the final list

        elif order_type == '=': # Conversion
            valid_types = []
            # 1. Check Preconditions
            # Use siege_stage and exclude self
            if unit.type == 'G' and Unit.objects.filter(area=unit.area, siege_stage__gt=0).exclude(id=unit.id).exists():
                 if logging: logging.info(f"Unit {unit_id} cannot convert, garrison besieged")
                 return JsonResponse(response_data) # Besieged garrison cannot convert

            # 2. Determine Valid Conversion Types
            if unit.area.board_area.is_fortified:
                if unit.type == 'G':
                    valid_types.append('A')
                    if unit.area.board_area.has_port: valid_types.append('F')
                else: # A or F converting to G
                    # Check if city is empty of *other* Garrisons
                    if not Unit.objects.filter(area=unit.area, type='G').exclude(id=unit.id).exists():
                         # Fleet needs port to convert to G? Assume yes.
                         if unit.type == 'A' or (unit.type == 'F' and unit.area.board_area.has_port):
                              valid_types.append('G')

            # 3. Build Response
            if valid_types:
                 # Response for conversion is slightly different: includes valid_types
                 destinations_list = [{
                     'id': unit.area.id,
                     'name': unit.area.board_area.name,
                     'code': unit.area.board_area.code,
                     'valid_types': valid_types,
                     'coasts': [] # Coasts not relevant for conversion target itself
                 }]
            response_data['destinations'] = destinations_list # Assign the final list

        # --- Handle other order types (L, 0, B, S, C) ---
        # These generally don't need a primary destination list from this view.
        # Support ('S') and Convoy ('C') destinations are handled by get_valid_support_destinations.
        # Lift Siege ('L'), Disband ('0'), Besiege ('B') don't target another area.
        else:
            if logging: logging.info(f"Order type '{order_type}' does not require destinations from this view.")
            # response_data remains {'destinations': []}

    except (Unit.DoesNotExist, Player.DoesNotExist, GameArea.DoesNotExist) as e:
        if logging: logging.error(f"Error in get_valid_destinations: {e}")
        pass # Return default empty list on error

    return JsonResponse(response_data)
	
		def get_valid_support_destinations(self, unit, supported_unit):
			"""Returns valid destinations for support orders"""
			if not unit or not supported_unit:
				return GameArea.objects.none()

			# For garrisons, only allow supporting into their own province
			if unit.type == 'G':
				return GameArea.objects.filter(id=unit.area.id)
			
			# For non-garrison units, use normal support rules
			is_fleet = (unit.type == 'F')
			supported_area = supported_unit.area
			
			# Get areas adjacent to the supporting unit
			adjacent = GameArea.objects.filter(
				game=unit.player.game,
				board_area__borders=unit.area.board_area
			)

			# Filter based on supporting unit type
			if is_fleet:
				adjacent = adjacent.filter(
					Q(board_area__is_sea=True) | Q(board_area__is_coast=True)
				)
				adjacent = [a for a in adjacent if unit.area.board_area.is_adjacent(a.board_area, fleet=True)]
			else:
				adjacent = adjacent.exclude(board_area__is_sea=True)

			# Must include the supported unit's area and its valid destinations
			supported_destinations = self.get_valid_destinations(supported_unit)
			return adjacent.filter(
				Q(id__in=[a.id for a in supported_destinations]) |
				Q(id=supported_area.id)
			)
		# Minor adjustments might be needed in AJAX views calling these if rules changed significantly

        class Meta:
            model = Order
            # Add new coast fields
            fields = ('unit', 'code', 'destination', 'destination_coast', 'type',
                      'subunit', 'subcode', 'subdestination', 'subdestination_coast', 'subtype')

        class Media:
            # JS file needs updates to handle showing/hiding/populating coast fields
            js = ("/site_media/static/machiavelli/js/order_form.js", # Needs update!
                  "/site_media/static/machiavelli/js/jquery.form.js")

        def clean(self):
            cleaned_data = super(OrderForm, self).clean()
            unit = cleaned_data.get('unit')
            code = cleaned_data.get('code')
            destination = cleaned_data.get('destination')
            destination_coast = cleaned_data.get('destination_coast')
            type_ = cleaned_data.get('type')
            subunit = cleaned_data.get('subunit')
            subcode = cleaned_data.get('subcode')
            subdestination = cleaned_data.get('subdestination')
            subdestination_coast = cleaned_data.get('subdestination_coast')
            subtype = cleaned_data.get('subtype')

            if not unit: return cleaned_data

            # --- Coast Validation ---
            dest_requires_coast = False
            subdest_requires_coast = False

            if code == '-' and destination and unit.type == 'F' and destination.board_area.has_multiple_coasts():
                dest_requires_coast = True
            elif code == 'C' and subdestination and subdestination.board_area.has_multiple_coasts():
                 # Convoy destination always needs coast if multi-coast
                 subdest_requires_coast = True
            elif code == 'S' and subcode == '-' and subdestination and subdestination.board_area.has_multiple_coasts():
                 # Support move needs coast if target area is multi-coast
                 # (Technically depends on supported unit type, but require for simplicity, JS can refine)
                 subdest_requires_coast = True

            if dest_requires_coast and not destination_coast:
                self.add_error('destination_coast', _("Must specify coast for this destination."))
            elif not dest_requires_coast:
                 cleaned_data['destination_coast'] = None # Clear if not needed

            if subdest_requires_coast and not subdestination_coast:
                 self.add_error('subdestination_coast', _("Must specify coast for this support/convoy destination."))
            elif not subdest_requires_coast:
                 cleaned_data['subdestination_coast'] = None # Clear if not needed

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

            # Use Order.is_possible for final rule check (now includes coast checks)
            temp_order_data = cleaned_data.copy()
            temp_order_data['player'] = player
            # Ensure only valid fields are passed to Order constructor
            valid_order_fields = {f.name for f in Order._meta.get_fields()}
            temp_order = Order(**{k: v for k, v in temp_order_data.items() if k in valid_order_fields})
            if not temp_order.is_possible():
                 # Provide a more generic error, as specific reason is hard to pinpoint here
                 raise forms.ValidationError(_("This order (including coast selection) is not possible according to the rules."))


            # Clear fields based on primary code
            if code in ['H', 'B', 'L', '0']:
                cleaned_data.update({'destination': None, 'destination_coast': None, 'type': None, 'subunit': None,
                                     'subcode': None, 'subdestination': None, 'subdestination_coast': None, 'subtype': None})
            elif code == '-':
                cleaned_data.update({'type': None, 'subunit': None, 'subcode': None,
                                     'subdestination': None, 'subdestination_coast': None, 'subtype': None})
                # Keep destination, destination_coast
            elif code == '=':
                cleaned_data.update({'destination': None, 'destination_coast': None, 'subunit': None, 'subcode': None,
                                     'subdestination': None, 'subdestination_coast': None, 'subtype': None})
                # Keep type
            elif code == 'C':
                cleaned_data.update({'destination': None, 'destination_coast': None, 'type': None, 'subcode': '-', 'subtype': None})
                # Keep subunit, subdestination, subdestination_coast (force subcode='-')
            elif code == 'S':
                cleaned_data.update({'destination': None, 'destination_coast': None, 'type': None})
                # Keep subunit, subcode
                if subcode in ['H', 'B']:
                    cleaned_data.update({'subdestination': None, 'subdestination_coast': None, 'subtype': None})
                elif subcode == '-':
                    cleaned_data.update({'subtype': None})
                    # Keep subdestination, subdestination_coast
                # elif subcode == '=': # Support Conversion (Currently disallowed)
                #     cleaned_data.update({'subdestination': None, 'subdestination_coast': None})
                #     # Keep subtype

            return cleaned_data

		def as_td(self):
			"Returns this form rendered as HTML <td>s -- excluding the <tr></tr>."
			# Use standard form rendering methods if possible, or keep custom one
			# return self._html_output(u'<td>%(errors)s %(field)s%(help_text)s</td>', u'<td style="width:10%%">%s</td>', u'</td>', u' %s', False)
			return super(OrderForm, self).as_table() # Or as_p, as_ul

	return OrderForm

def make_retreat_form(u):
    # Get possible retreat areas using updated model method (includes current area for conversion)
    possible_retreats = u.get_possible_retreats().select_related('board_area') # Optimize

    class RetreatForm(forms.Form):
        unitid = forms.IntegerField(widget=forms.HiddenInput, initial=u.id)
        area = forms.ModelChoiceField(required=False, # Allow disbanding
                            queryset=possible_retreats,
                            empty_label=_('Disband unit'), # Use empty_label for disband option
                            label=unicode(u)) # Label with unit description
        # New Coast Field for Retreat
        coast = forms.ChoiceField(choices=BLANK_COAST_CHOICE + COAST_CHOICES, required=False, label=_("Retreat Coast"))

        def clean(self):
            cleaned_data = super(RetreatForm, self).clean()
            area = cleaned_data.get('area')
            coast = cleaned_data.get('coast')
            unit = Unit.objects.select_related('area__board_area').get(pk=cleaned_data.get('unitid')) # Get the unit

            if area: # If retreating to an area (not disbanding)
                 # Check if chosen area is valid
                 if area not in possible_retreats:
                      self.add_error('area', _("Invalid retreat destination selected."))
                      return cleaned_data # Stop validation

                 # Check coast if retreating to multi-coast area
                 if area.board_area.has_multiple_coasts():
                     # Fleet retreating to multi-coast MUST specify coast
                     if unit.type == 'F':
                         if not coast:
                             self.add_error('coast', _("Must specify coast when retreating a fleet to this area."))
                         elif coast not in area.board_area.get_coast_list():
                              self.add_error('coast', _("Invalid coast selected for this area."))
                     # Army retreating to multi-coast (only possible via conversion?) - coast not applicable
                     elif coast:
                          cleaned_data['coast'] = None # Clear invalid coast for army
                 elif coast:
                     # Clear coast if specified but area is not multi-coastal
                     cleaned_data['coast'] = None

                 # Check if retreating to current area (conversion)
                 if area == unit.area:
                      # Ensure conversion is actually possible (redundant with get_possible_retreats check?)
                      if not unit.area.board_area.is_fortified or \
                         Unit.objects.filter(area=unit.area, type='G').exclude(id=unit.id).exists() or \
                         (unit.type == 'F' and not unit.area.board_area.has_port):
                           self.add_error('area', _("Cannot retreat by converting to Garrison here."))
                      cleaned_data['coast'] = None # Coast not relevant for conversion

            elif coast: # Disbanding, but coast specified? Clear it.
                 cleaned_data['coast'] = None

            return cleaned_data

    return RetreatForm

def make_reinforce_form(player, finances=False, special_units=False):
    if finances:
        unit_types = (('', '---'),) + UNIT_TYPES # Allow blank choice if maybe not building
        noarea_label = '---'
    else: # Basic game
        unit_types = UNIT_TYPES # Must choose a type
        noarea_label = None

    # Get areas using updated model method
    area_qs = player.get_areas_for_new_units(finances=finances).select_related('board_area') # Optimize

    class ReinforceForm(forms.Form):
        type = forms.ChoiceField(required=not finances, choices=unit_types) # Required only in Basic
        area = forms.ModelChoiceField(required=not finances, # Required only in Basic
                              queryset=area_qs,
                              empty_label=noarea_label)
        # New Coast Field for Build
        coast = forms.ChoiceField(choices=BLANK_COAST_CHOICE + COAST_CHOICES, required=False, label=_("Build Coast"))

        # Special unit selection (Optional Rule IV)
        if finances and special_units and not player.has_special_unit(): # Only if finances, option on, player doesn't have one
            unit_class = forms.ModelChoiceField(required=False,
                                            queryset=SpecialUnit.objects.all(), # Allow choosing any defined special unit
                                            empty_label=_("Regular (Cost: 3)"), # Default is regular
                                            label=_("Unit Class"))

        def clean(self):
            cleaned_data = super(ReinforceForm, self).clean()
            type_ = cleaned_data.get('type')
            area = cleaned_data.get('area')
            coast = cleaned_data.get('coast')
            unit_class = cleaned_data.get('unit_class') # Get special unit choice

            # In finance mode, fields aren't required, skip validation if blank
            if finances and not type_ and not area:
                 # Check if unit_class was selected without type/area
                 if unit_class:
                      self.add_error('type', _("Must select type and area if choosing a special unit."))
                 return cleaned_data # Allow empty form submission

            if not type_: self.add_error('type', _("This field is required.")); return cleaned_data
            if not area: self.add_error('area', _("This field is required.")); return cleaned_data

            # --- Basic Placement Rule Checks ---
            board_area = area.board_area
            error = None
            if type_ == 'G':
                 if not board_area.is_fortified: error = _('Garrisons can only be placed in fortified cities/fortresses.')
                 # Check if city already occupied (Rule V.B.1.b / V.B.3.c)
                 elif area.unit_set.filter(type='G').exists(): error = _('A Garrison already exists in this city.')
            elif type_ == 'F':
                 if not board_area.has_port: error = _('Fleets can only be placed in port cities.')
                 # Check if province already occupied (Rule V.B.1.b / V.B.3.c)
                 elif area.unit_set.exclude(type='G').exists(): error = _('An Army or Fleet already exists in this province.')
            elif type_ == 'A':
                 if board_area.is_sea or board_area.code == 'VEN': error = _('Armies cannot be placed in seas or Venice.')
                 # Check if province already occupied (Rule V.B.1.b / V.B.3.c)
                 elif area.unit_set.exclude(type='G').exists(): error = _('An Army or Fleet already exists in this province.')

            if error: self.add_error(None, error); return cleaned_data

            # --- Coast Validation for Build ---
            if type_ == 'F' and board_area.has_multiple_coasts():
                if not coast:
                    self.add_error('coast', _("Must specify coast when building a fleet in this area."))
                elif coast not in board_area.get_coast_list():
                    self.add_error('coast', _("Invalid coast selected for this area."))
            elif coast:
                # Clear coast if not building a fleet or area is not multi-coastal
                cleaned_data['coast'] = None

            # --- Finance Checks (Cost) ---
            if finances:
                 cost = unit_class.cost if unit_class else 3
                 # Check available ducats (done in view/formset to sum costs)
                 # Store cost for formset validation
                 cleaned_data['cost'] = cost

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
    # Use general list for ducats, validation happens in clean()
    general_expense_choices = make_ducats_list(player.ducats, 3) # Rule VI.C.4.g.2: Multiples of 3 for bribes > min

    # Querysets for dropdowns
    # Target units: Any unit not owned by the player (for bribes) or any unit (for counter-bribe)
    # Filter further based on expense type in clean()
    unit_qs = Unit.objects.filter(player__game=player.game) \
                    .exclude(player=player) \
                    .select_related('area__board_area', 'player__country') \
                    .order_by('player__country__name', 'area__board_area__code')
    counter_bribe_unit_qs = Unit.objects.filter(player__game=player.game) \
                    .select_related('area__board_area', 'player__country') \
                    .order_by('player__country__name', 'area__board_area__code')

    # Target areas: Any non-sea area controlled by another player (for rebellions) or any area (for famine relief)
    area_qs = GameArea.objects.filter(game=player.game) \
                    .exclude(board_area__is_sea=True) \
                    .select_related('board_area', 'player__country') \
                    .order_by('board_area__code')
    famine_area_qs = GameArea.objects.filter(game=player.game, famine=True) \
                    .select_related('board_area') \
                    .order_by('board_area__code')


    class ExpenseForm(forms.ModelForm):
        # Use dynamic choices based on type later? For now, use general list.
        ducats = forms.ChoiceField(required=True, choices=general_expense_choices, label=_("Ducats to Spend"))
        # Querysets are broad initially, refined by JS or validated in clean()
        area = forms.ModelChoiceField(required=False, queryset=area_qs, label=_("Target Area"))
        unit = forms.ModelChoiceField(required=False, queryset=counter_bribe_unit_qs, label=_("Target Unit")) # Start with broader unit QS

        def __init__(self, player, **kwargs):
            super(ExpenseForm, self).__init__(**kwargs)
            self.instance.player = player
            # JS could potentially update querysets based on type selection
            # self.fields['area'].queryset = ...
            # self.fields['unit'].queryset = ...

        class Meta:
            model = Expense
            fields = ('type', 'ducats', 'area', 'unit') # Order fields logically

        def clean(self):
            cleaned_data = super(ExpenseForm, self).clean()
            type_ = cleaned_data.get('type')
            ducats_str = cleaned_data.get('ducats')
            area = cleaned_data.get('area')
            unit = cleaned_data.get('unit')

            if type_ is None or ducats_str is None: # Check basic fields exist
                return cleaned_data

            try:
                ducats = int(ducats_str)
                if ducats <= 0: raise forms.ValidationError(_("Must spend a positive amount."))
            except (ValueError, TypeError):
                raise forms.ValidationError(_("Invalid ducat amount selected."))

            # --- Validate required fields based on type ---
            if type_ == 0: # Famine relief
                if not area: self.add_error('area', _("Famine relief requires a target area.")); return cleaned_data
                if not area.famine: self.add_error('area', _("Selected area does not have famine."))
                cleaned_data['unit'] = None
            elif type_ == 1: # Pacify rebellion
                if not area: self.add_error('area', _("Pacify rebellion requires a target area.")); return cleaned_data
                if not Rebellion.objects.filter(area=area).exists(): self.add_error('area', _("There is no rebellion in the selected area."))
                cleaned_data['unit'] = None
            elif type_ in (2, 3): # Start rebellion
                if not area: self.add_error('area', _("Starting a rebellion requires a target area.")); return cleaned_data
                if not area.player: self.add_error('area', _("Selected area is not controlled by anyone."))
                elif area.player == player: self.add_error('area', _("Cannot start rebellion in your own area."))
                else: # Check home vs conquered (Rule VI.C.5.a/b)
                    is_home = area in area.player.home_country(original=True) # Check original home country
                    if type_ == 2 and is_home: self.add_error('type', _("This is a home province; use 'Home province to rebel'."))
                    elif type_ == 3 and not is_home: self.add_error('type', _("This is a conquered province; use 'Conquered province to rebel'."))
                # Check Venice occupation (Rule VI.C.5.c.11)
                if area.board_area.code == 'VEN' and area.unit_set.exists():
                    self.add_error('area', _("Cannot start rebellion in occupied Venice."))
                cleaned_data['unit'] = None
            elif type_ == 4: # Counter-bribe
                 if not unit: self.add_error('unit', _("Counter-bribe requires a target unit.")); return cleaned_data
                 cleaned_data['area'] = None
            elif type_ in (5, 6, 7, 8, 9, 10): # Bribes
                if not unit: self.add_error('unit', _("Bribe requires a target unit.")); return cleaned_data
                cleaned_data['area'] = None
                # Validate target unit type based on bribe type
                if type_ in (5, 6): # Disband/Buy Auto G
                     if unit.player and unit.player.user is not None: self.add_error('unit', _("Target must be an autonomous garrison."))
                     elif unit.type != 'G': self.add_error('unit', _("Target must be an autonomous garrison."))
                elif type_ == 7: # Commit G -> Auto
                     if not unit.player or unit.player.user is None: self.add_error('unit', _("Target must be a committed (non-autonomous) garrison."))
                     elif unit.type != 'G': self.add_error('unit', _("Target must be a committed garrison."))
                elif type_ == 8: # Disband Commit G
                     if not unit.player or unit.player.user is None: self.add_error('unit', _("Target must be a committed (non-autonomous) garrison."))
                     elif unit.type != 'G': self.add_error('unit', _("Target must be a committed garrison."))
                elif type_ == 9: # Disband A/F
                     if not unit.player or unit.player.user is None: self.add_error('unit', _("Target must be a committed (non-autonomous) unit."))
                     elif unit.type not in ['A', 'F']: self.add_error('unit', _("Target must be an Army or Fleet."))
                elif type_ == 10: # Buy A/F
                     if not unit.player or unit.player.user is None: self.add_error('unit', _("Target must be a committed (non-autonomous) unit."))
                     elif unit.type not in ['A', 'F']: self.add_error('unit', _("Target must be an Army or Fleet."))
            else:
                self.add_error('type', _("Unknown expense type selected."))
                return cleaned_data

            # --- Check minimum cost and ducat amount ---
            try:
                min_cost = get_expense_cost(type_, unit)
                if ducats < min_cost:
                    self.add_error('ducats', _("Must spend at least %(cost)s ducats for this expense.") % {'cost': min_cost})
                # Check amount is multiple of 3 if required (Rule VI.C.4.g.2)
                # Applies to bribes > min cost and counter-bribes
                if type_ >= 4 and ducats % 3 != 0:
                     self.add_error('ducats', _("Amount must be a multiple of 3."))

            except ValueError as e: # Handle errors from get_expense_cost
                self.add_error(None, unicode(e)) # Non-field error

            # --- Check bribe adjacency (Rule VI.C.4.g.4) ---
            if type_ in (5, 6, 7, 8, 9, 10) and unit: # Check if it's a bribe and unit is set
                # Check if player has unit adjacent to target unit's area OR controls area adjacent to target
                adjacent_areas = unit.area.get_adjacent_areas(include_self=False) # Areas adjacent to target
                q_player_unit_adjacent = Q(player=player, area__in=adjacent_areas)
                # Control check needs careful thought - controlling the province itself? Or just bordering?
                # Rule says "adjacent to one of that player's military units". Let's stick to that.
                # q_player_control_adjacent = Q(player=player, board_area__in=unit.area.board_area.borders.all())

                is_adjacent = Unit.objects.filter(q_player_unit_adjacent).exists()
                              # or GameArea.objects.filter(q_player_control_adjacent).exists()

                # Optional Rule V.A: Check adjacency via ally (requires complex check)
                # if not is_adjacent and player.game.configuration.bribes_via_ally:
                #    # Check if any ally unit is adjacent
                #    pass

                if not is_adjacent:
                    # Optional Rule V.B: Allow bribe anywhere
                    if not player.game.configuration.bribes_anywhere: # Assuming a config flag
                        self.add_error('unit', _("You cannot bribe this unit because it's not adjacent to any of your units."))

            return cleaned_data

    return ExpenseForm

class LendForm(forms.Form):
	ducats = forms.IntegerField(required=True, min_value=1) # Cannot lend 0

TERMS = (
    (1, _("1 year, 20% interest")), # Rule X.A.3
    (2, _("2 years, 50% interest")), # Rule X.A.3
)

class BorrowForm(forms.Form):
    ducats = forms.IntegerField(required=True, min_value=1, label=_("Ducats to borrow"))
    term = forms.ChoiceField(required=True, choices=TERMS, label=_("Term and interest"))

    def __init__(self, player=None, *args, **kwargs):
        self.player = player
        super(BorrowForm, self).__init__(*args, **kwargs)
        # Disable form if player cannot borrow
        if not self.player or self.player.defaulted or self.player.get_credit() <= 0:
             for field in self.fields:
                  self.fields[field].widget.attrs['disabled'] = True

    def clean_ducats(self):
        ducats = self.cleaned_data.get('ducats')
        if ducats is None: return None # Handled by required=True

        if not self.player: # Should not happen if form initialized correctly
            raise forms.ValidationError("Player context missing.")
        if self.player.defaulted: # Rule X.B
             raise forms.ValidationError(_("You cannot borrow after defaulting on a previous loan."))

        # Check max loan limit (Rule X.A.1)
        # Rule: "total number of ducats owed... may never exceed twenty-five"
        # This implies the *new principal* + *existing principal* cannot exceed 25.
        current_principal = 0
        try:
            # Assumes Loan model stores principal correctly
            current_principal = self.player.loan.principal
        except Loan.DoesNotExist:
            pass
        except AttributeError: # If Loan model doesn't have principal yet
             pass

        if (current_principal + ducats) > 25:
             max_borrow = 25 - current_principal
             if max_borrow < 0: max_borrow = 0
             raise forms.ValidationError(_("Cannot borrow: Total debt principal would exceed 25 ducats. You can borrow at most %(max)s more.") % {'max': max_borrow})

        # Check against player's credit limit (Optional Rule X.A - based on areas/units unless unbalanced)
        # get_credit() likely needs implementation based on Rule X.A if not using unbalanced.
        # Assuming get_credit() exists and returns the limit for *this specific loan*.
        # credit_limit = self.player.get_credit()
        # if ducats > credit_limit:
        #      raise forms.ValidationError(_("Your current credit limit is %(limit)s ducats.") % {'limit': credit_limit})
        # Credit limit check might be redundant if max total principal is 25.

        return ducats

    def clean(self):
        # Ensure form is disabled if needed
        if not self.player or self.player.defaulted or self.player.get_credit() <= 0:
             # If form submitted despite being disabled, raise error
             if self.has_changed():
                  raise forms.ValidationError(_("Cannot borrow money at this time."))
        return super(BorrowForm, self).clean()


class RepayForm(forms.Form):
	# No fields needed, just a confirmation button
	pass

def make_assassination_form(player):
    # Cost is minimum 12, max 36 (multiples of 12) - Rule VI.C.6.a
    assassination_choices = []
    # Check affordability based on player's ducats
    if player.ducats >= 12: assassination_choices.append((12, _("12 Ducats (1 die roll)")))
    if player.ducats >= 24: assassination_choices.append((24, _("24 Ducats (2 die rolls)")))
    if player.ducats >= 36: assassination_choices.append((36, _("36 Ducats (3 die rolls)")))

    if not assassination_choices: # Cannot afford even minimum
        assassination_choices = (('', _("Cannot afford")),) # Placeholder, disable form

    # Get countries the player has an assassin token for (Rule VI.C.6)
    assassin_targets_qs = Country.objects.filter(
        assassin__owner=player # Check Assassin model for tokens owned by player
    ).exclude(
        player__game=player.game, player__eliminated=True # Exclude eliminated players in this game
    ).exclude(
        id=player.country_id # Cannot target self
    ).distinct().order_by('name')

    class AssassinationForm(forms.Form):
        # Use dynamic choices based on affordability
        ducats = forms.ChoiceField(required=True, choices=assassination_choices, label=_("Cost (Selects Dice)"))
        # Use dynamic queryset based on available tokens
        target = forms.ModelChoiceField(required=True, queryset=assassin_targets_qs, label=_("Target Country"))

        def __init__(self, *args, **kwargs):
             super(AssassinationForm, self).__init__(*args, **kwargs)
             # Disable form if no choices available
             if not assassin_targets_qs.exists() or assassination_choices[0][0] == '':
                  for field in self.fields:
                       self.fields[field].widget.attrs['disabled'] = True

        def clean_ducats(self):
            ducats_str = self.cleaned_data.get('ducats')
            try:
                ducats_int = int(ducats_str)
                if ducats_int not in [12, 24, 36]:
                     raise forms.ValidationError(_("Invalid amount selected for assassination."))
                # Check affordability again (belt-and-suspenders)
                if ducats_int > player.ducats:
                     raise forms.ValidationError(_("Insufficient ducats for selected amount."))
            except (ValueError, TypeError):
                raise forms.ValidationError(_("Invalid amount selected."))
            return ducats_int # Return as integer

        def clean_target(self):
             target_country = self.cleaned_data.get('target')
             # Check if player actually has the token (redundant with queryset?)
             if target_country and not Assassin.objects.filter(owner=player, target=target_country).exists():
                  raise forms.ValidationError(_("You do not have an assassin token for this country."))
             return target_country

        def clean(self):
             # Ensure form is disabled if needed
             if not assassin_targets_qs.exists() or assassination_choices[0][0] == '':
                  if self.has_changed():
                       raise forms.ValidationError(_("Cannot attempt assassination at this time."))
             return super(AssassinationForm, self).clean()


    return AssassinationForm