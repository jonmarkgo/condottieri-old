# machiavelli/models.py
## Copyright (c) 2010 by Jose Antonio Martin <jantonio.martin AT gmail DOT com>
## This program is free software: you can redistribute it and/or modify it
## under the terms of the GNU Affero General Public License as published by the
## Free Software Foundation, either version 3 of the License, or (at your option
## any later version.
##
## This program is distributed in the hope that it will be useful, but WITHOUT
## ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
## FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License
## for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program. If not, see <http://www.gnu.org/licenses/agpl.txt>.
##
## This license is also included in the file COPYING
##
## AUTHOR: Jose Antonio Martin <jantonio.martin AT gmail DOT com>

""" Class definitions for machiavelli django application

Defines the core classes of the machiavelli game.
"""

## stdlib
import random
import thread
from datetime import datetime, timedelta

## django
from django.db import models
from django.db.models import permalink, Q, F, Count, Sum, Avg
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.cache import cache
from django.contrib.auth.models import User
import django.forms as forms
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.template.defaultfilters import capfirst, truncatewords, timesince, force_escape

if "notification" in settings.INSTALLED_APPS:
	from notification import models as notification
else:
	notification = None

if "jogging" in settings.INSTALLED_APPS:
	from jogging import logging
else:
	logging = None

if "condottieri_messages" in settings.INSTALLED_APPS:
	import condottieri_messages as condottieri_messages
else:
	condottieri_messages = None

## machiavelli
from machiavelli.fields import AutoTranslateField
from machiavelli.graphics import make_map
from machiavelli.logging import save_snapshot
import machiavelli.dice as dice
import machiavelli.disasters as disasters
import machiavelli.finances as finances
import machiavelli.exceptions as exceptions

## condottieri_profiles
from condottieri_profiles.models import CondottieriProfile

## condottieri_events
if "condottieri_events" in settings.INSTALLED_APPS:
	import machiavelli.signals as signals
else:
	signals = None

try:
	settings.TWITTER_USER
except:
	twitter_api = None
else:
	import twitter
	twitter_api = twitter.Api(username=settings.TWITTER_USER,
							  password=settings.TWITTER_PASSWORD)

UNIT_TYPES = (('A', _('Army')),
              ('F', _('Fleet')),
              ('G', _('Garrison'))
			  )

SEASONS = ((1, _('Spring')),
           (2, _('Summer')),
           (3, _('Fall')),
           )

# --- Phase Definitions ---
# Basic Game Phases
PHINACTIVE = 0
PHREINFORCE = 1 # Basic: Military Unit Adjustment / Advanced: + Income
PHORDERS = 2    # Basic: Order Writing / Advanced: + Ducat Expenditure Writing
PHRETREATS = 3  # Basic: Retreats (part of Order Execution)

# Advanced/Optional Phases (can be integrated or distinct)
PHINCOME = 10          # Advanced: Income Calculation (part of Spring Reinforce)
PHNEGOTIATION = 11     # All: Negotiation Phase (conceptual, not a hard state?)
PHEXPENSES = 12        # Advanced: Ducat Expenditure Phase
PHASSASSINATION = 13   # Advanced: Assassination Phase
PHFAMINE = 14          # Optional: Famine Phase (Spring)
PHPLAGUE = 15          # Optional: Plague Phase (Spring) - Rule III.A implies it happens *after* Famine
PHSTORMS = 16          # Optional: Storm Phase (Summer) - Rule III.C implies it happens *after* Negotiation
PHLENDERS = 17         # Optional: Money Lenders Phase (Ducat Borrowing) - Rule X implies before Expenses

# Combined Sequence (Example - adjust based on desired implementation)
GAME_PHASES = (
    (PHINACTIVE, _('Inactive game')),
    # Spring
    (PHFAMINE, _('Optional: Famine Check')), # Optional III.A
    (PHPLAGUE, _('Optional: Plague Check')), # Optional III.A
    (PHREINFORCE, _('Spring: Adjust Units & Income')), # Basic V / Advanced V.A/B
    (PHNEGOTIATION, _('Negotiation')), # Basic VI
    (PHLENDERS, _('Optional: Borrow Ducats')), # Optional X.A
    (PHORDERS, _('Write Orders & Expenses')), # Basic VII / Advanced VI.A
    (PHEXPENSES, _('Execute Expenses')), # Advanced VI.B
    (PHASSASSINATION, _('Resolve Assassinations')), # Advanced VI.B / IV.E
    (PHRETREATS, _('Execute Orders & Retreats')), # Basic VIII / Advanced IV.F
    # Summer
    (PHNEGOTIATION, _('Negotiation')),
    (PHSTORMS, _('Optional: Storm Check')), # Optional III.C
    (PHLENDERS, _('Optional: Borrow Ducats')),
    (PHORDERS, _('Write Orders & Expenses')),
    (PHEXPENSES, _('Execute Expenses')),
    (PHASSASSINATION, _('Resolve Assassinations')),
    (PHRETREATS, _('Execute Orders & Retreats')),
    # Fall
    (PHNEGOTIATION, _('Negotiation')),
    (PHLENDERS, _('Optional: Borrow Ducats')),
    (PHORDERS, _('Write Orders & Expenses')),
    (PHEXPENSES, _('Execute Expenses')),
    (PHASSASSINATION, _('Resolve Assassinations')),
    (PHRETREATS, _('Execute Orders & Retreats')),
)

# Original simple phases (kept for reference or basic game mode)
# GAME_PHASES = ((PHINACTIVE, _('Inactive game')),
# 	  (PHREINFORCE, _('Military adjustments')),
# 	  (PHORDERS, _('Order writing')),
# 	  (PHRETREATS, _('Retreats')),
# 	  )

ORDER_CODES = (('H', _('Hold')),
			   ('B', _('Besiege')),
			   ('-', _('Advance')),
			   ('=', _('Conversion')),
			   ('C', _('Convoy/Transport')), # Renamed slightly for clarity
			   ('S', _('Support')),
               ('L', _('Lift Siege')), # Added L
               ('0', _('Disband')),     # Added 0
				)
ORDER_SUBCODES = (
				('H', _('Hold')),
				('-', _('Advance')),
				('=', _('Conversion'))
)

## time limit in seconds for a game phase
FAST_LIMITS = (15*60, )

TIME_LIMITS = (
			#(5*24*60*60, _('5 days')),
			#(4*24*60*60, _('4 days')),
			(3*24*60*60, _('3 days')),
			(2*24*60*60, _('2 days')),
			(24*60*60, _('1 day')),
			(12*60*60, _('1/2 day')),
			(15*60, _('15 min')),
)

## SCORES
## points assigned to the first, second and third players
SCORES=[20, 10, 5]

# Default KARMA settings in case they're not in settings
KARMA_MINIMUM = getattr(settings, 'KARMA_MINIMUM', 10)
KARMA_DEFAULT = getattr(settings, 'KARMA_DEFAULT', 100)
KARMA_MAXIMUM = getattr(settings, 'KARMA_MAXIMUM', 200)
BONUS_TIME = getattr(settings, 'BONUS_TIME', 0.2)

class Invasion(object):
	""" This class is used in conflicts resolution for conditioned invasions.
	Invasion objects are not persistent (i.e. not stored in the database).
	"""

	def __init__(self, unit, area, conv=''):
		assert isinstance(unit, Unit), u"%s is not a Unit" % unit
		assert isinstance(area, GameArea), u"%s is not a GameArea" % area
		assert conv in ['', 'A', 'F', 'G'], u"%s is not a valid conversion" % conv # Added G
		self.unit = unit
		self.area = area
		self.conversion = conv

class Scenario(models.Model):
	""" This class defines a Machiavelli scenario basic data. """

	name = models.CharField(max_length=16, unique=True)
	title = AutoTranslateField(max_length=128)
	start_year = models.PositiveIntegerField()
	## this field is added to improve the performance of some queries
	number_of_players = models.PositiveIntegerField(default=0)
	# cities_to_win is now handled in Game model, scenario provides default if needed
	# cities_to_win = models.PositiveIntegerField(default=15)
	enabled = models.BooleanField(default=False) # this allows me to create the new setups in the admin

	def get_slots(self):
		# Exclude the autonomous player if present
		return self.setup_set.exclude(country__isnull=True).values('country').distinct().count()

	def __unicode__(self):
		return self.title

	def get_absolute_url(self):
		return "scenario/%s" % self.id

	def get_countries(self):
		return Country.objects.filter(home__scenario=self).distinct()

if twitter_api and settings.TWEET_NEW_SCENARIO:
	def tweet_new_scenario(sender, instance, created, **kw):
		if twitter_api and isinstance(instance, Scenario):
			if created == True:
				message = "A new scenario has been created: %s" % instance.title
				twitter_api.PostUpdate(message)

	models.signals.post_save.connect(tweet_new_scenario, sender=Scenario)

class SpecialUnit(models.Model):
	""" A SpecialUnit describes the attributes of a unit that costs more ducats than usual
	and can be more powerful or more loyal """
	static_title = models.CharField(max_length=50)
	title = AutoTranslateField(max_length=50)
	cost = models.PositiveIntegerField()
	power = models.PositiveIntegerField()
	loyalty = models.PositiveIntegerField()

	def __unicode__(self):
		return _("%(title)s (%(cost)sd)") % {'title': self.title,
											'cost': self.cost}

	def describe(self):
		return _("Costs %(cost)s; Strength %(power)s; Loyalty %(loyalty)s") % {'cost': self.cost,
																	'power': self.power,
																	'loyalty': self.loyalty}

class Country(models.Model):
	""" This class defines a Machiavelly country. """

	name = AutoTranslateField(max_length=20, unique=True)
	css_class = models.CharField(max_length=20, unique=True)
	can_excommunicate = models.BooleanField(default=False)
	static_name = models.CharField(max_length=20, default="")
	special_units = models.ManyToManyField(SpecialUnit)

	def __unicode__(self):
		return self.name

class Area(models.Model):
	""" This class describes **only** the area features in the board. The game is
actually played in GameArea objects.
	"""

	name = AutoTranslateField(max_length=25, unique=True)
	code = models.CharField(max_length=5 ,unique=True)
	is_sea = models.BooleanField(default=False)
	is_coast = models.BooleanField(default=False)
	has_city = models.BooleanField(default=False)
	is_fortified = models.BooleanField(default=False) # True for fortified cities AND standalone fortresses
	has_port = models.BooleanField(default=False)
	borders = models.ManyToManyField("self", editable=False)
	## control_income is the number of ducats that the area gives to the player
	## that controls it, including the city (seas give 0)
	control_income = models.PositiveIntegerField(null=False, default=0)
	## garrison_income is the number of ducats given by an unbesieged
	## garrison in the area's city, if any (no fortified city, 0)
	garrison_income = models.PositiveIntegerField(null=False, default=0)
	# Add field for major city income value (Advanced Rule V.B.1.c.2)
	major_city_income = models.PositiveIntegerField(null=True, blank=True, default=None, help_text="Income value if this is a major city")

	def is_adjacent(self, area, fleet=False):
		""" Two areas can be adjacent through land, but not through a coast.

		The list ``only_armies`` shows the areas that are adjacent but their
		coasts are not, so a Fleet can move between them.

        Handles special adjacency rules from VII.D.
		"""
		# Basic adjacency check
		if area not in self.borders.all():
			return False

		# Fleet specific checks
		if fleet:
			# Rule VII.D.4: Provence - separate coastlines
			if self.code == 'PRO' and area.code == 'MAR': return False # Cannot cross Marseille land bridge
			if area.code == 'PRO' and self.code == 'MAR': return False
			if self.code == 'PRO' and area.code == 'AVI': return False # Cannot move inland from coast
			if area.code == 'PRO' and self.code == 'AVI': return False
			# Rule VII.D.3: Dalmatia/Croatia - Croatia south coast access via Dalmatia/Istria
			if self.code == 'CRO' and area.code == 'UA': # Check if moving from North coast of Croatia
			    # This is complex, might need more map data (e.g., segment borders)
			    # Simple check: if adjacent to Istria/Dalmatia, assume South coast access
			    if not (self.borders.filter(code='IST').exists() or self.borders.filter(code='DAL').exists()):
			        return True # Assume North coast access
			    else: # If adjacent to IST/DAL, assume moving via South coast - needs DAL/IST first
			        return False # Cannot directly access UA from South Croatia coast
			if area.code == 'CRO' and self.code == 'UA': # Symmetric check
			    if not (area.borders.filter(code='IST').exists() or area.borders.filter(code='DAL').exists()):
			        return True
			    else:
			        return False
			# Rule VII.D.9: ETS <-> Capua (No), GON <-> Tivoli (Yes)
			if (self.code == 'ETS' and area.code == 'CAP') or (area.code == 'ETS' and self.code == 'CAP'):
			    return False
			# Rule VII.D.1/2: Piombino/Messina straits are handled by control logic, not adjacency.

			# General Fleet Adjacency: Cannot move between two non-coastal land provinces
			if not self.is_sea and not self.is_coast and not area.is_sea and not area.is_coast:
				return False
			# Fleet cannot move inland from a sea unless it's a coastal province
			if self.is_sea and not area.is_sea and not area.is_coast:
				return False
			if area.is_sea and not self.is_sea and not self.is_coast:
				return False
            # Fleet cannot move between two land provinces unless both are coastal and adjacent via coast
            # (This is tricky, basic border check might suffice if map data is accurate)
			if not self.is_sea and not area.is_sea: # Both are land
			    if not self.is_coast or not area.is_coast: # At least one is not coastal
			        return False # Cannot move fleet between non-coastal land or from coastal to non-coastal land

		# Army specific checks
		else: # Army movement
		    # Rule VII.B.1.d: Armies cannot enter seas
		    if area.is_sea: return False
		    # Rule VII.D.6: Armies cannot enter Venice (province/city combo)
		    if area.code == 'VEN': return False

		# If no specific rule prevents it, and they border, they are adjacent
		return True


	def accepts_type(self, type):
		""" Returns True if an given type of Unit can be in the Area. """

		assert type in ('A', 'F', 'G'), 'Wrong unit type'
		if type=='A':
			# Rule VII.B.1.d, VII.D.6: Armies cannot be in seas or Venice
			if self.is_sea or self.code=='VEN':
				return False
		elif type=='F':
			# Rule VII.B.1.e: Fleets can be in seas or coastal provinces
			if not self.is_sea and not self.is_coast:
				return False
		else: # Garrison
			# Rule VII.B.1.c: Garrisons only in fortified cities/fortresses
			if not self.is_fortified:
				return False
		return True

	def __unicode__(self):
		return "%(code)s - %(name)s" % {'name': self.name, 'code': self.code}

	class Meta:
		ordering = ('code',)

class DisabledArea(models.Model):
	""" A DisabledArea is an Area that is not used in a given Scenario. """
	scenario = models.ForeignKey(Scenario)
	area = models.ForeignKey(Area)

	def __unicode__(self):
		return "%(area)s disabled in %(scenario)s" % {'area': self.area,
													'scenario': self.scenario}

	class Meta:
		unique_together = (('scenario', 'area'),)

class Home(models.Model):
	""" This class defines which Country controls each Area in a given Scenario,
	at the beginning of a game.

	Note that, in some special cases, a province controlled by a country does
	not belong to the **home country** of this country. The ``is_home``
	attribute controls that.
	"""

	scenario = models.ForeignKey(Scenario)
	country = models.ForeignKey(Country)
	area = models.ForeignKey(Area)
	is_home = models.BooleanField(default=True) # Rule V.D.3

	def __unicode__(self):
		return "%s" % self.area.name

	class Meta:
		unique_together = (("scenario", "country", "area"),)

class Setup(models.Model):
	""" This class defines the initial setup of a unit in a given Scenario. """

	scenario = models.ForeignKey(Scenario)
	country = models.ForeignKey(Country, blank=True, null=True) # Null for Autonomous
	area = models.ForeignKey(Area)
	unit_type = models.CharField(max_length=1, choices=UNIT_TYPES)

	def __unicode__(self):
		return _("%(unit)s in %(area)s") % { 'unit': self.get_unit_type_display(),
											'area': self.area.name }

	class Meta:
		unique_together = (("scenario", "area", "unit_type"),) # Should allow multiple units if area allows? No, rule VII.B.1.b

class Treasury(models.Model):
	""" This class represents the initial amount of ducats that a Country starts
	each Scenario with """

	scenario = models.ForeignKey(Scenario)
	country = models.ForeignKey(Country)
	ducats = models.PositiveIntegerField(default=0)
	double = models.BooleanField(default=False) # Relates to variable income rolls? Rule V.B.1.d

	def __unicode__(self):
		return "%s starts %s with %s ducats" % (self.country, self.scenario, self.ducats)

	class Meta:
		unique_together = (("scenario", "country"),)


class CityIncome(models.Model):
	""" This class represents a City that generates an income in a given
	Scenario"""
	# This seems redundant if Area.major_city_income is used.
	# Keeping for now, but consider consolidating.
	city = models.ForeignKey(Area)
	scenario = models.ForeignKey(Scenario)

	def __unicode__(self):
		return "%s" % self.city.name

	class Meta:
		unique_together = (("city", "scenario"),)


class Game(models.Model):
	""" This is the main class of the machiavelli application. It includes all the
	logic to control the flow of the game, and to resolve conflicts.

	The attributes year, season and field are null when the game is first created
	and will be populated when the game is started, from the scenario data.
	"""

	slug = models.SlugField(max_length=20, unique=True,
				help_text=_("4-20 characters, only letters, numbers, hyphens and underscores"))
	year = models.PositiveIntegerField(blank=True, null=True)
	season = models.PositiveIntegerField(blank=True, null=True,
					     choices=SEASONS)
	phase = models.PositiveIntegerField(blank=True, null=True,
					    choices=GAME_PHASES, default=PHINACTIVE) # Default to inactive
	slots = models.SmallIntegerField(null=False, default=0)
	scenario = models.ForeignKey(Scenario)
	created_by = models.ForeignKey(User, editable=False)
	## whether the player of each country is visible
	visible = models.BooleanField(default=0,
				help_text=_("if checked, it will be known who controls each country"))
	map_outdated = models.BooleanField(default=0)
	time_limit = models.PositiveIntegerField(choices=TIME_LIMITS,
				help_text=_("time available to play a turn"))
	## the time and date of the last phase change
	last_phase_change = models.DateTimeField(blank=True, null=True)
	created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
	started = models.DateTimeField(blank=True, null=True)
	finished = models.DateTimeField(blank=True, null=True)
	# Store the *type* of victory condition chosen (e.g., 'basic', 'advanced', 'ultimate')
	victory_condition_type = models.CharField(max_length=10, default='basic')
	# Store the actual number required for the chosen type
	cities_to_win = models.PositiveIntegerField(default=12, # Default to Basic Game
				help_text=_("cities that must be controlled to win a game"))
	fast = models.BooleanField(default=0)
	private = models.BooleanField(default=0,
				help_text=_("only invited users can join the game"))
	comment = models.TextField(max_length=255, blank=True, null=True,
				help_text=_("optional comment for joining users"))

	def save(self, *args, **kwargs):
		if not self.pk:
			self.fast = self.time_limit in FAST_LIMITS
			# Set cities_to_win based on type if creating
			if self.victory_condition_type == 'basic':
			    self.cities_to_win = 12
			elif self.victory_condition_type == 'advanced':
			    # Need number of players to determine 15 or 18
			    # This might need adjustment post-creation or during game start
			    num_players = self.scenario.get_slots() + 1 # Estimate
			    self.cities_to_win = 15 if num_players >= 5 else 18
			elif self.victory_condition_type == 'ultimate':
			    self.cities_to_win = 23
			# else: keep the value provided, allowing custom games
		super(Game, self).save(*args, **kwargs)

	##------------------------
	## representation methods
	##------------------------
	def __unicode__(self):
		return "%d" % (self.pk)

	def get_map_url(self):
		if self.slots > 0:  # If game is pending
			return "scenario-%s.png" % self.scenario.pk
		return "map-%s.png?t=%s" % (self.id, self.last_phase_change.strftime('%s') if self.last_phase_change else '0')
	
	def get_absolute_url(self):
		return ('show-game', None, {'slug': self.slug})
	get_absolute_url = models.permalink(get_absolute_url)

	def reset_players_cache(self):
		""" Deletes the player list from the cache """
		key = "game-%s_player-list" % self.pk
		cache.delete(key)
	
	def player_list_ordered_by_cities(self):
		key = "game-%s_player-list" % self.pk
		result_list = cache.get(key)
		if result_list is None:
			from django.db import connection
			cursor = connection.cursor()
			cursor.execute("SELECT machiavelli_player.*, COUNT(machiavelli_gamearea.id) \
			AS cities \
			FROM machiavelli_player \
			LEFT JOIN (machiavelli_gamearea \
			INNER JOIN machiavelli_area \
			ON machiavelli_gamearea.board_area_id=machiavelli_area.id) \
			ON machiavelli_gamearea.player_id=machiavelli_player.id \
			WHERE (machiavelli_player.game_id=%s AND machiavelli_player.country_id \
			AND (machiavelli_area.has_city=1 OR machiavelli_gamearea.id IS NULL)) \
			GROUP BY machiavelli_player.id \
			ORDER BY cities DESC, machiavelli_player.id;" % self.id)
			result_list = []
			for row in cursor.fetchall():
				result_list.append(Player.objects.get(id=row[0]))
			cache.set(key, result_list)
		return result_list

	def highest_score(self):
		""" Returns the Score with the highest points value. """

		if self.slots > 0 or self.phase != PHINACTIVE:
			return Score.objects.none()
		scores = self.score_set.all().order_by('-points')
		return scores[0]
	
	def get_average_score(self):
		""" Returns the average score of the current list of players """
		
		result = CondottieriProfile.objects.filter(user__player__game=self).aggregate(average_score=Avg('total_score'))
		return result['average_score']

	def get_average_karma(self):
		""" Returns the average karma of the current list of players """
		
		result = CondottieriProfile.objects.filter(user__player__game=self).aggregate(average_karma=Avg('karma'))
		return result['average_karma']

	def get_all_units(self):
		""" Returns a queryset with all the units in the board. """
		key = "game-%s_all-units" % self.pk
		all_units = cache.get(key)
		if all_units is None:
			all_units = Unit.objects.select_related().filter(player__game=self).order_by('area__board_area__name')
			cache.set(key, all_units)
		return all_units

	def get_all_gameareas(self):
		""" Returns a queryset with all the game areas in the board. """
		key = "game-%s_all-areas" % self.pk
		all_areas = cache.get(key)
		if all_areas is None:
			all_areas = self.gamearea_set.select_related().order_by('board_area__code')
			cache.set(key, all_areas)
		return all_areas

	##------------------------
	## map methods
	##------------------------
	
	def make_map(self):
		make_map(self)
		#thread.start_new_thread(make_map, (self,))
		return True

	def map_changed(self):
		if self.map_outdated == False:
			self.map_outdated = True
			self.save()
	
	def map_saved(self):
		if self.map_outdated == True:
			self.map_outdated = False
			self.save()

	##------------------------
	## game starting methods
	##------------------------

	def player_joined(self):
		self.slots -= 1
		#self.map_outdated = True
		if self.slots == 0:
			#the game has all its players and should start
			if logging:
				logging.info("Starting game %s" % self.id)
			if self.private:
				self.invitation_set.all().delete()
			self.year = self.scenario.start_year
			self.season = 1
			self.phase = PHORDERS
			self.create_game_board()
			self.shuffle_countries()
			self.copy_country_data()
			self.home_control_markers()
			self.place_initial_units()
			if self.configuration.finances:
				self.assign_initial_income()
			if self.configuration.assassinations:
				self.create_assassins()
			#self.map_outdated = True
			self.make_map()
			self.started = datetime.now()
			self.last_phase_change = datetime.now()
			self.notify_players("game_started", {"game": self})
		self.save()
		#if self.map_outdated == True:
		#	self.make_map()
	
	def shuffle_countries(self):
		""" Assign a Country of the Scenario to each Player, randomly. """

		countries_dict = self.scenario.setup_set.values('country').distinct()
		countries = []
		for c in countries_dict:
			for v in c.values():
				if v:
					countries.append(v)
		## the number of players and countries should be the same
		assert len(countries) == len(self.player_set.filter(user__isnull=False)), "Number of players should be the same as number of countries"
		## a list of tuples will be returned
		assignment = []
		## shuffle the list of countries
		random.shuffle(countries)
		for player in self.player_set.filter(user__isnull=False):
			assignment.append((player, countries.pop()))
		for t in assignment:
			t[0].country = Country.objects.get(id=t[1])
			t[0].save()

	def copy_country_data(self):
		""" Copies to the player objects some properties that will never change during the game.
		This way, I hope to save some hits to the database """
		excom = self.configuration.excommunication
		finances = self.configuration.finances

		for p in self.player_set.filter(user__isnull=False):
			p.static_name = p.country.static_name
			if excom:
				p.may_excommunicate = p.country.can_excommunicate
			if finances:
				t = Treasury.objects.get(scenario=self.scenario, country=p.country)
				p.double_income = t.double
			p.save()

	def get_disabled_areas(self):
		""" Returns the disabled Areas in the game scenario """
		return Area.objects.filter(disabledarea__scenario=self.scenario)

	def create_game_board(self):
		""" Creates the GameAreas for the Game.	"""
		disabled_ids = Area.objects.filter(disabledarea__scenario=self.scenario).values_list('id', flat=True)
		for a in Area.objects.all():
			if not a.id in disabled_ids:
				ga = GameArea(game=self, board_area=a)
				ga.save()

	def get_autonomous_setups(self):
		return Setup.objects.filter(scenario=self.scenario,
				country__isnull=True).select_related()
	
	def place_initial_garrisons(self):
		""" Creates the Autonomous Player, and places the autonomous garrisons at the
		start of the game.
		"""

		## create the autonomous player
		autonomous = Player(game=self, done=True)
		autonomous.save()
		for s in self.get_autonomous_setups():
			try:
				a = GameArea.objects.get(game=self, board_area=s.area)
			except:
				print "Error 1: Area not found!"
			else:	
				if s.unit_type:
					new_unit = Unit(type='G', area=a, player=autonomous)
					new_unit.save()

	def home_control_markers(self):
		for p in self.player_set.filter(user__isnull=False):
			p.home_control_markers()

	def place_initial_units(self):
		for p in self.player_set.filter(user__isnull=False):
			p.place_initial_units()
		self.place_initial_garrisons()

	def assign_initial_income(self):
		for p in self.player_set.filter(user__isnull=False):
			t = Treasury.objects.get(scenario=self.scenario, country=p.country)
			p.ducats = t.ducats
			p.save()

	def create_assassins(self):
		""" Assign each player an assassination counter for each of the other players """
		for p in self.player_set.filter(user__isnull=False):
			for q in self.player_set.filter(user__isnull=False):
				if q == p:
					continue
				assassin = Assassin()
				assassin.owner = p
				assassin.target = q.country
				assassin.save()

	##--------------------------
	## time controlling methods
	##--------------------------

	def clear_phase_cache(self):
		cache_keys = [
			"game-%s_player_list" % self.pk,
			"game-%s_all-units" % self.pk,
			"game-%s_all-areas" % self.pk,
		]
		for k in cache_keys:
			cache.delete(k)

	def get_highest_karma(self):
		""" Returns the karma of the non-finished player with the highest value.
			
			Returns 0 if all the players have finished.
		"""

		players = CondottieriProfile.objects.filter(user__player__game=self,
								user__player__done=False).order_by('-karma')
		if len(players) > 0:
			return float(players[0].karma)
		return 0


	def next_phase_change(self):
		""" Returns the Time of the next compulsory phase change. """
		if self.phase == PHINACTIVE :
			return False	
		if self.fast:
			## do not use karma
			time_limit = self.time_limit
		else:
			## get the player with the highest karma, and not done
			highest = self.get_highest_karma()
			if highest > 100:
				if self.phase == PHORDERS:
					k = 1 + (highest - 100) / 200
				else:
					k = 1
			else:
				k = highest / 100
			time_limit = self.time_limit * k
		
		duration = timedelta(0, time_limit)

		return self.last_phase_change + duration
	

	def force_phase_change(self):
		""" When the time limit is reached and one or more of the players are not
		done, a phase change is forced.
		"""

		for p in self.player_set.all():
			if p.done:
				continue
			else:
				if self.phase == PHREINFORCE:
					if self.configuration.finances:
						units = Unit.objects.filter(player=p).order_by('id')
						ducats = p.ducats
						payable = ducats / 3
						cost = 0
						if payable > 0:
							for u in units[:payable]:
								u.paid = True
								u.save()
								cost += 3
						p.ducats = ducats - cost
						p.save()
					else:
						units = Unit.objects.filter(player=p).order_by('-id')
						reinforce = p.units_to_place()
						if reinforce < 0:
							## delete the newest units
							for u in units[:-reinforce]:
								u.delete()
				elif self.phase == PHORDERS:
					pass
				elif self.phase == PHRETREATS:
					## disband the units that should retreat
					Unit.objects.filter(player=p).exclude(must_retreat__exact='').delete()
				p.end_phase(forced=True)
		
	def time_to_limit(self):
		""" Calculates the time to the next phase change and returns it as a
		timedelta.
		"""
		if not self.phase == PHINACTIVE:
			limit = self.next_phase_change()
			return limit - datetime.now()
	
	def time_is_exceeded(self):
		"""
		Checks if the time limit has been reached. If yes, return True
		"""
		return self.time_to_limit() <= timedelta(0, 0)

	def check_finished_phase(self):
		""" Checks if all players are done or time limit exceeded, then processes the phase. """
		# Check if game is already finished
		if self.phase == PHINACTIVE:
			return False # Nothing to check

		players_not_done = self.player_set.filter(user__isnull=False, eliminated=False, done=False)
		all_done = not players_not_done.exists()
		time_exceeded = self.time_is_exceeded()

		msg = f"Checking phase change in game {self.pk} (Phase: {self.get_phase_display()}, All Done: {all_done}, Time Exceeded: {time_exceeded})\n"

		if time_exceeded and not all_done:
			msg += "Time exceeded. Forcing phase change.\n"
			self.force_phase_change() # Force remaining players
			all_done = True # Now consider all done for processing

		if all_done:
			msg += "All players done or forced. Processing phase.\n"
			if logging: logging.info(msg)

			self.process_current_phase() # Execute actions for the completed phase

			# Check for winner *after* processing the phase's actions
			if self.phase != PHINACTIVE and self.check_winner(): # Avoid check if game_over already triggered
				msg += "Winner found after processing phase.\n"
				if logging: logging.info(msg)
				self.make_map()
				self.assign_scores()
				self.game_over()
				return True # Game ended

			# If game didn't end, advance to the next phase
			if self.phase != PHINACTIVE:
			    self.advance_to_next_phase()
			    self.clear_phase_cache()
			    # Reset player 'done' status for the new phase
			    self.player_set.filter(user__isnull=False, eliminated=False).update(done=False)
			    # Call new_phase logic for each player (check if they need to act)
			    for p in self.player_set.filter(user__isnull=False, eliminated=False):
			        p.new_phase() # Let player model determine if 'done' should be true for new phase
			    self.notify_players("new_phase", {"game": self})
			    self.make_map() # Update map for new phase
			return True # Phase advanced
		else:
			msg += "At least one player is not done and time remains.\n"
			if logging: logging.debug(msg) # Use debug for routine checks
			return False # Phase not finished yet

	def process_current_phase(self):
	    """ Executes the logic associated with the *current* game phase. """
	    phase = self.phase
	    if logging: logging.info(f"Game {self.id}: Processing phase {phase} ({self.get_phase_display()})")

	    if phase == PHFAMINE:
	        self.mark_famine_areas()
	    elif phase == PHPLAGUE:
	        self.kill_plague_units()
	    elif phase == PHREINFORCE: # Handles both Basic Adjust and Advanced Income/Adjust
	        if self.configuration.finances:
	            self.assign_incomes() # Calculate income first in Spring
	        self.adjust_units() # Place/remove units
	    elif phase == PHNEGOTIATION:
	        pass # Conceptual phase, no mechanical action
	    elif phase == PHLENDERS:
	        self.check_loans() # Check for defaults (Optional X.B)
	        # Borrowing happens via user interaction in views during this phase
	    elif phase == PHORDERS:
	        # Order writing happened before this phase was marked done.
	        # This phase might be combined or just a step in sequence.
	        pass
	    elif phase == PHEXPENSES:
	        self.process_expenses() # Advanced VI.B
	    elif phase == PHASSASSINATION:
	        self.process_assassinations() # Advanced VI.B / IV.E
	        # Apply assassination effects (garrison surrender, rebellions)
	        for p in self.player_set.filter(assassinated=True):
	            # Remove besieged garrisons (Rule VI.C.6.e)
	            besieged_garrisons = Unit.objects.filter(
	                player=p, type='G', area__unit__besieging=True, area__unit__siege_stage__gt=0
	            ).distinct() # Check siege_stage > 0
	            for garrison in besieged_garrisons:
	                besieger = Unit.objects.filter(area=garrison.area, siege_stage__gt=0).first()
	                if signals: signals.unit_surrendered.send(sender=garrison, context="assassination")
	                garrison.delete()
	                if besieger:
	                    besieger.siege_stage = 0 # Reset siege
	                    besieger.besieging = False
	                    besieger.save()

	            # Trigger province rebellions (Rule VI.C.6.f)
	            for area in p.gamearea_set.exclude(board_area__is_sea=True):
	                 area.check_assassination_rebellion()
	    elif phase == PHRETREATS: # Handles Order Execution AND Retreats
	        # Apply assassination paralysis (Rule VI.C.6.d) - change orders to Hold
	        for p in self.player_set.filter(assassinated=True):
	            p.cancel_orders(hold=True)

	        self.process_orders() # Resolve movements, conflicts, sieges

	        # If retreats were generated, process user input for them
	        if Unit.objects.filter(player__game=self).exclude(must_retreat__exact='').exists():
	            self.process_retreats() # Process RetreatOrder objects created by view
	    elif phase == PHSTORMS:
	        self.mark_storm_areas()
	    # Add other phase processing logic here

	def advance_to_next_phase(self):
	    """ Determines and sets the next phase based on season and configuration. """
	    current_phase = self.phase
	    current_season = self.season
	    current_year = self.year
	    config = self.configuration

	    # --- Determine the sequence for the current/next season ---
	    sequence = []
	    is_spring = (current_season == 1)
	    is_summer = (current_season == 2)
	    is_fall = (current_season == 3)

	    # Build sequence based on rules
	    if is_spring:
	        if config.famine: sequence.append(PHFAMINE)
	        if config.plague: sequence.append(PHPLAGUE)
	        sequence.append(PHREINFORCE) # Basic V / Advanced V.A/B
	    # Common phases for all seasons
	    sequence.append(PHNEGOTIATION) # Basic VI
	    if is_summer and config.storms: sequence.append(PHSTORMS) # Optional III.C (Summer only)
	    if config.lenders: sequence.append(PHLENDERS) # Optional X.A
	    sequence.append(PHORDERS) # Basic VII / Advanced VI.A
	    if config.finances: # Expenses/Assassination only if finances enabled
	        sequence.append(PHEXPENSES) # Advanced VI.B / IV.D
	        if config.assassinations:
	            sequence.append(PHASSASSINATION) # Advanced VI.B / IV.E
	    sequence.append(PHRETREATS) # Basic VIII / Advanced IV.F (Order Exec + Retreats)

	    # --- Find the next phase in the sequence ---
	    try:
	        current_index = sequence.index(current_phase)
	        next_phase = sequence[current_index + 1]
	        next_season = current_season
	        next_year = current_year
	    except (ValueError, IndexError):
	        # Current phase not found or was the last in sequence -> Advance Season/Year
	        if is_fall:
	            # --- End of Fall Season Checks ---
	            self.end_of_season_checks(season_ended=3)
	            if self.phase == PHINACTIVE: return # Game ended during checks

	            next_season = 1
	            next_year = current_year + 1
	            # Determine first phase of Spring
	            next_phase = PHREINFORCE
	            if config.plague: next_phase = PHPLAGUE
	            if config.famine: next_phase = PHFAMINE
	        else:
	            # --- End of Spring/Summer Season Checks ---
	            self.end_of_season_checks(season_ended=current_season)
	            if self.phase == PHINACTIVE: return # Game ended during checks

	            next_season = current_season + 1
	            next_year = current_year
	            # Determine first phase of Summer/Fall (Negotiation)
	            next_phase = PHNEGOTIATION
	            if next_season == 2 and config.storms: # Add Storms if applicable
	                 sequence = [PHNEGOTIATION, PHSTORMS] # Start of summer sequence
	                 if current_phase == PHNEGOTIATION: next_phase = PHSTORMS
	                 else: next_phase = PHNEGOTIATION # Should not happen if sequence is correct
	            # else: first phase is Negotiation

	    # --- Update Game State ---
	    self.phase = next_phase
	    self.season = next_season
	    self.year = next_year
	    self.last_phase_change = datetime.now()
	    # Reset assassination status for the new turn (happens before phase actions)
	    self.player_set.filter(assassinated=True).update(assassinated=False)
	    # Reset Pope's sentencing status
	    self.player_set.filter(has_sentenced=True).update(has_sentenced=False)

	    self.save()
	    if logging: logging.info(f"Game {self.id}: Advanced to {self.year} {self.get_season_display()} - {self.get_phase_display()}")


	
	def check_bonus_time(self):
		""" Returns true if, when the function is called, the first BONUS_TIME% of the
		duration has not been reached.
		"""

		duration = timedelta(0, self.time_limit * BONUS_TIME)
		limit = self.last_phase_change + duration
		to_limit = limit - datetime.now()
		if to_limit >= timedelta(0, 0):
			return True
		else:
			return False

	def get_bonus_deadline(self):
		""" Returns the latest time when karma is bonified """
		duration = timedelta(0, self.time_limit * BONUS_TIME)
		return self.last_phase_change + duration
	
	def _next_season(self):
	    # This method is now largely replaced by advance_to_next_phase
	    # Kept for reference or potential specific season logic if needed outside phase advancement
	    save_snapshot(self)
	    if self.season == 3:
	        self.season = 1
	        self.year += 1
	    else:
	        self.season += 1
	    # Cleanup that happens *every* turn transition (if any)
	    Unit.objects.filter(player__game=self).update(must_retreat='')
	    GameArea.objects.filter(game=self).update(standoff=False)
	    # Resetting assassinated/has_sentenced moved to advance_to_next_phase
	    # self.player_set.all().update(assassinated=False, has_sentenced=False)
	    self.save()


	def all_players_done(self):
	    # This method is now deprecated. Logic moved to check_finished_phase.
	    pass



	def end_of_season_checks(self, season_ended):
	    """ Performs checks that happen at the end of a specific season. """
	    if logging: logging.info(f"Game {self.id}: Performing end-of-season checks for season {season_ended}")
	    config = self.configuration

	    if season_ended == 1: # End of Spring
	        # Famine units removed (Rule III.B)
	        if config.famine:
	            famine_units = Unit.objects.filter(player__game=self, area__famine=True)
	            if famine_units.exists():
	                if logging: logging.info(f"Game {self.id}: Removing {famine_units.count()} units due to famine.")
	                famine_units.delete()
	            self.gamearea_set.filter(famine=True).update(famine=False) # Reset famine markers
	        # Plague units already killed in PHPLAGUE phase

	    elif season_ended == 2: # End of Summer
	        # Storms resolved at end of Fall
	        pass

	    elif season_ended == 3: # End of Fall
	        # Storm units removed (Rule III.C)
	        if config.storms:
	            storm_units = Unit.objects.filter(player__game=self, area__storm=True)
	            if storm_units.exists():
	                 if logging: logging.info(f"Game {self.id}: Removing {storm_units.count()} units due to storms.")
	                 storm_units.delete()
	            self.gamearea_set.filter(storm=True).update(storm=False) # Reset storm markers

	        # Check eliminations (Rule V.D)
	        for p in self.player_set.filter(eliminated=False, user__isnull=False):
	            if p.check_eliminated():
	                p.eliminate() # Handles unit removal etc.

	        self.update_controls() # Update area control based on unit presence

	        # Check conquerings (Rule V.D.2)
	        if config.conquering:
	            self.check_conquerings()

	        # Check for winner AFTER all end-of-fall actions
	        if self.check_winner():
	            # Game ends here, set phase to inactive to stop further advancement
	            self.phase = PHINACTIVE
	            self.save()
	            # Winner processing happens in the calling function (check_finished_phase)

	def adjust_units(self):
		""" Places new units and disbands the ones that are not paid (Finance rules).
		    Or adjusts units based on city count (Basic rules). """
		if self.configuration.finances:
		    # Disband unpaid units
		    to_disband = Unit.objects.filter(player__game=self, placed=True, paid=False).exclude(player__user__isnull=True) # Exclude autonomous
		    if to_disband.exists():
		        if logging: logging.info(f"Game {self.id}: Disbanding {to_disband.count()} unpaid units.")
		        to_disband.delete()
		    # Place newly built units
		    to_place = Unit.objects.filter(player__game=self, placed=False)
		    if to_place.exists():
		         if logging: logging.info(f"Game {self.id}: Placing {to_place.count()} new units.")
		         for u in to_place: u.place() # Calls signal etc.
		    # Mark all remaining non-autonomous units as unpaid for the *next* Spring
		    Unit.objects.filter(player__game=self).exclude(player__user__isnull=True).update(paid=False)
		else: # Basic Game Logic
		    # Units marked paid=False by view logic need disbanding
		    to_disband = Unit.objects.filter(player__game=self, placed=True, paid=False).exclude(player__user__isnull=True)
		    if to_disband.exists():
		        if logging: logging.info(f"Game {self.id}: Disbanding {to_disband.count()} excess units (Basic).")
		        to_disband.delete()
		    # Units marked placed=False by view logic need placing
		    to_place = Unit.objects.filter(player__game=self, placed=False)
		    if to_place.exists():
		        if logging: logging.info(f"Game {self.id}: Placing {to_place.count()} new units (Basic).")
		        for u in to_place: u.place()
		    # No concept of payment in basic, reset flags? Or rely on view logic setting them correctly each Spring.
		    # Let's assume view logic handles it.


	## deprecated because of check_finished_phase
	#def check_next_phase(self):
	#	""" When a player ends its phase, send a signal to the game. This function
	#	checks if all the players have finished.
	#	"""
	#
	#	for p in self.player_set.all():
	#		if not p.done:
	#			return False
	#	self.all_players_done()
	#	for p in self.player_set.all():
	#		p.new_phase()

	##------------------------
	## optional rules methods
	##------------------------
	def check_conquerings(self):
		if not self.configuration.conquering:
			return
		## a player can only be conquered if he is eliminated
		for p in self.player_set.filter(eliminated=True):
			## try fo find a home province that is not controlled by any player
			neutral = GameArea.objects.filter(game=self,
									board_area__home__country=p.country,
									board_area__home__scenario=self.scenario,
									board_area__home__is_home=True,
									player__isnull=True).count()
			if neutral > 0:
				continue
			## get the players that control part of this player's home country
			controllers = self.player_set.filter(gamearea__board_area__home__country=p.country,
									gamearea__board_area__home__scenario=self.scenario,
									gamearea__board_area__home__is_home=True).distinct()
			if len(controllers) == 1:
				## all the areas in home country belong to the same player
				if p != controllers[0] and p.conqueror != controllers[0]:
					## controllers[0] conquers p
					p.set_conqueror(controllers[0])

	def mark_famine_areas(self):
		if not self.configuration.famine:
			return
		codes = disasters.get_famine()
		famine_areas = GameArea.objects.filter(game=self, board_area__code__in=codes)
		for f in famine_areas:
			f.famine=True
			f.save()
			signals.famine_marker_placed.send(sender=f)
	
	def mark_storm_areas(self):
		if not self.configuration.storms:
			return
		codes = disasters.get_storms()
		storm_areas = GameArea.objects.filter(game=self, board_area__code__in=codes)
		for f in storm_areas:
			f.storm=True
			f.save()
			signals.storm_marker_placed.send(sender=f)
	
	def kill_plague_units(self):
		if not self.configuration.plague:
			return
		codes = disasters.get_plague()
		plague_areas = GameArea.objects.filter(game=self, board_area__code__in=codes)
		for p in plague_areas:
			# Check if a plague event already exists for this area
			from condottieri_events.models import DisasterEvent
			existing_plague = DisasterEvent.objects.filter(
				game=self,
				area=p.board_area,
				message=1  # 1 is the message type for plague
			).exists()
			
			if not existing_plague:
				signals.plague_placed.send(sender=p)
			for u in p.unit_set.all():
				u.delete()

	def assign_incomes(self):
		""" Gets each player's income and add it to the player's treasury (Advanced V.B). """
		if not self.configuration.finances or self.season != 1: # Only in Spring with Finances
		    return

		die = dice.roll_1d6() # Rule V.B.1.d
		if logging: logging.info(f"Game {self.id}: Variable income roll (Spring {self.year}): {die}")

		# Get IDs of major cities for this scenario (Rule V.B.1.c.2)
		# Use Area.major_city_income if populated, otherwise CityIncome model
		major_city_ids_area = Area.objects.filter(major_city_income__isnull=False).values_list('id', flat=True)
		major_city_ids_model = CityIncome.objects.filter(scenario=self.scenario).values_list('city_id', flat=True)
		all_major_city_ids = set(list(major_city_ids_area) + list(major_city_ids_model))


		players = self.player_set.filter(user__isnull=False, eliminated=False)
		for p in players:
			income = p.get_income(die, all_major_city_ids) # Pass die roll and major city IDs
			if income > 0:
				p.add_ducats(income) # Handles F() expression and logging

	def check_loans(self):
		""" Check if any loans have exceeded their terms. If so, apply the
		penalties. """
		loans = Loan.objects.filter(player__game=self)
		for loan in loans:
			if self.year >= loan.year and self.season >= loan.season:
				## the loan has exceeded its term
				if logging:
					msg = "%s defaulted" % loan.player
					logging.info(msg)
				loan.player.defaulted = True
				loan.player.save()
				loan.player.assassinate()
				loan.delete()
	
	def process_expenses(self):
		## undo unconfirmed expenses
		invalid_expenses = Expense.objects.filter(player__game=self, confirmed=False)
		for e in invalid_expenses:
			e.undo()
		## log expenses
		if signals:
			for e in Expense.objects.filter(player__game=self, confirmed=True):
				signals.expense_paid.send(sender=e)
		## then, process famine reliefs
		for e in Expense.objects.filter(player__game=self, type=0):
			e.area.famine = False
			e.area.save()
		## then, delete the rebellions
		for e in Expense.objects.filter(player__game=self, type=1):
			Rebellion.objects.filter(area=e.area).delete()
		## then, place new rebellions
		for e in Expense.objects.filter(player__game=self, type__in=(2,3)):
			try:
				rebellion = Rebellion(area=e.area)
				rebellion.save()
			except:
				continue
		## then, delete bribes that are countered
		expenses = Expense.objects.filter(player__game=self)
		for e in expenses:
			if e.is_bribe():
				## get the sum of counter-bribes
				cb = Expense.objects.filter(player__game=self, type=4, unit=e.unit).aggregate(Sum('ducats'))
				if not cb['ducats__sum']:
					cb['ducats__sum'] = 0
				total_cost = get_expense_cost(e.type, e.unit) + cb['ducats__sum']
				if total_cost > e.ducats:
					e.delete()
		## then, resolve the bribes for each bribed unit
		bribed_ids = Expense.objects.filter(unit__player__game=self, type__in=(5,6,7,8,9)).values_list('unit', flat=True).distinct()
		chosen = []
		## TODO: if two bribes have the same value, decide randomly between them
		for i in bribed_ids:
			bribes = Expense.objects.filter(type__in=(5,6,7,8,9), unit__id=i).order_by('-ducats')
			chosen.append(bribes[0])
		## all bribes in 'chosen' are successful, and executed
		for c in chosen:
			if c.type in (5, 8): #disband unit
				c.unit.delete()
			elif c.type in (6, 9): #buy unit
				c.unit.change_player(c.player)
			elif c.type == 7: #to autonomous
				c.unit.to_autonomous()
		## finally, delete all the expenses
		Expense.objects.filter(player__game=self).delete()

	def get_rebellions(self):
		""" Returns a queryset with all the rebellions in this game """
		return Rebellion.objects.filter(area__game=self)

	def process_assassinations(self):
		""" Resolves all the assassination attempts """
		attempts = Assassination.objects.filter(killer__game=self)
		victims = []
		msg = u"Processing assassinations in game %s:\n" % self
		for a in attempts:
			msg += u"\n%s spends %s ducats to kill %s\n" % (a.killer, a.ducats, a.target)
			if a.target in victims:
				msg += u"%s already killed\n" % a.target
				continue
			dice_rolled = int(a.ducats / 12)
			if dice_rolled < 1:
				msg += u"%s are not enough" % a.ducats
				continue
			msg += u"%s dice will be rolled\n" % dice_rolled
			if dice.check_one_six(dice_rolled):
				msg += u"Attempt is successful\n"
				## attempt is successful
				a.target.assassinate()
				victims.append(a.target)
			else:
				msg += u"Attempt fails\n"
		attempts.delete()
		if logging:
			logging.info(msg)


	##------------------------
	## turn processing methods
	##------------------------

	def get_conflict_areas(self):
		""" Returns the orders that could result in a possible conflict these are the
		advancing units and the units that try to convert into A or F.
		"""

		conflict_orders = Order.objects.filter(unit__player__game=self, code__in=['-', '=']).exclude(type__exact='G')
		conflict_areas = []
		for o in conflict_orders:
			if o.code == '-':
				if o.unit.area.board_area.is_adjacent(o.destination.board_area, fleet=(o.unit.type=='F')) or \
					o.find_convoy_line():
						area = o.destination
				else:
					continue
			else:
				## unit trying to convert into A or F
				area = o.unit.area
			conflict_areas.append(area)
		return conflict_areas

	def 
	def filter_supports(self):
		""" Checks which Units with support orders are being attacked and delete their
		orders if the attack is not from the supported direction (Rule VIII.B.3.d).
		"""
		info = u"Step 2: Cancel supports from units under attack.\n"
		support_orders = Order.objects.filter(unit__player__game=self, code='S', confirmed=True) # Process confirmed orders
		# Get all potential attacking orders targeting areas with supporting units
		supporter_areas = support_orders.values_list('unit__area', flat=True).distinct()
		attacking_orders = Order.objects.filter(
		    Q(unit__player__game=self, confirmed=True) &
		    ( # Advance into supporter's area
		      (Q(code='-') & Q(destination__in=supporter_areas)) |
		      # Convert G->A/F in supporter's area
		      (Q(code='=') & ~Q(type='G') & Q(unit__area__in=supporter_areas))
		    )
		)

		orders_to_delete = []
		for s_order in support_orders:
			supporter = s_order.unit
			info += f"Checking support order {s_order.id} from {supporter}.\n"
			# Find attacks specifically targeting this supporter's area
			attacks_on_supporter = attacking_orders.filter(
			    ~Q(unit__player=supporter.player) & # Must be enemy attack
			    (Q(destination=supporter.area) | Q(unit__area=supporter.area)) # Target area matches
			)

			if attacks_on_supporter.exists():
				info += f"Supporting unit {supporter} is being attacked.\n"
				support_cut = False
				# Determine the area the support is directed *into*
				support_target_area = None
				if s_order.subcode == 'H': support_target_area = s_order.subunit.area
				elif s_order.subcode == '-': support_target_area = s_order.subdestination
				# elif s_order.subcode == '=': support_target_area = s_order.subunit.area # Support conversion

				if not support_target_area:
				    info += "Invalid support target area, support likely invalid.\n"
				    # This case should ideally be caught by form validation
				    continue

				for attack_order in attacks_on_supporter:
					# Rule VIII.B.3.d: Support is NOT cut if attack comes FROM the area support was directed TO.
					if attack_order.unit.area == support_target_area:
						info += f"Attack from {attack_order.unit} is from the supported area ({support_target_area.board_area.code}). Support NOT cut.\n"
						continue # This attack doesn't cut support
					else:
						info += f"Attack from {attack_order.unit} (in {attack_order.unit.area.board_area.code}) cuts support into {support_target_area.board_area.code}.\n"
						support_cut = True
						break # One cutting attack is enough

				if support_cut:
					if signals: signals.support_broken.send(sender=supporter)
					orders_to_delete.append(s_order.id)

		if orders_to_delete:
		     Order.objects.filter(id__in=orders_to_delete).delete()
		     info += f"Deleted {len(orders_to_delete)} cut support orders.\n"

		return info

	def filter_convoys(self):
		""" Checks which convoying Fleets are dislodged and cancels their convoy. (Rule VIII.B.6.f implies convoy fails if fleet retreats) """
		# This is complex because dislodging depends on the full conflict resolution.
		# A simpler approach (as likely intended by original code) is to check if the fleet *loses* a direct conflict.
		info = u"Step 3: Cancel convoys by fleets likely to be dislodged.\n"
		convoy_orders = Order.objects.filter(unit__player__game=self, code='C', confirmed=True)
		orders_to_delete = []

		for c_order in convoy_orders:
		    fleet = c_order.unit
		    info += f"Checking convoy order {c_order.id} by {fleet}.\n"
		    # Check attacks targeting the fleet's area
		    attacks_on_fleet = Order.objects.filter(
		        ~Q(unit__player=fleet.player) & Q(unit__player__game=self, confirmed=True) &
		        (Q(code='-', destination=fleet.area) | Q(code='=', unit__area=fleet.area, type__in=['A','F']))
		    )
		    if not attacks_on_fleet.exists():
		        continue # Fleet not attacked

		    info += f"Convoying fleet {fleet} is under attack.\n"
		    fleet_strength_obj = Unit.objects.get_with_strength(self.game, id=fleet.id)
		    fleet_strength = fleet_strength_obj.strength

		    dislodged = False
		    for attack_order in attacks_on_fleet:
		        attacker_strength_obj = Unit.objects.get_with_strength(self.game, id=attack_order.unit.id)
		        attacker_strength = attacker_strength_obj.strength
		        info += f"Attacked by {attack_order.unit} (Strength: {attacker_strength}). Fleet strength: {fleet_strength}.\n"
		        # If any single attacker has > strength, fleet is dislodged
		        # If attacker has == strength, it's a standoff, fleet holds, convoy proceeds.
		        if attacker_strength > fleet_strength:
		            info += f"Fleet {fleet} will be dislodged by {attack_order.unit}. Cancelling convoy.\n"
		            dislodged = True
		            break # One successful dislodge is enough

		    if dislodged:
		        orders_to_delete.append(c_order.id)
		        # Also cancel the corresponding army's advance order if it relied solely on this convoy
		        army_order = Order.objects.filter(unit=c_order.subunit, code='-', destination=c_order.subdestination, confirmed=True).first()
		        if army_order:
		            # Check if other convoys exist for this army move (complex)
		            # Simplification: Assume if the main convoy fails, the move fails.
		            info += f"Cancelling advance order for convoyed army {c_order.subunit}.\n"
		            orders_to_delete.append(army_order.id)


		if orders_to_delete:
		     Order.objects.filter(id__in=orders_to_delete).delete()
		     info += f"Deleted {len(orders_to_delete)} orders due to disrupted convoys.\n"

		return info

	def filter_unreachable_attacks(self):
		""" Delete advance orders to non-adjacent areas without a valid convoy line. """
		info = u"Step 4: Cancel attacks to unreachable areas.\n"
		advance_orders = Order.objects.filter(unit__player__game=self, code='-', confirmed=True)
		orders_to_delete = []

		for order in advance_orders:
		    unit = order.unit
		    destination = order.destination
		    is_fleet = (unit.type == 'F')
		    is_directly_adjacent = unit.area.board_area.is_adjacent(destination.board_area, fleet=is_fleet)

		    if not is_directly_adjacent:
		        # If not adjacent, check for convoy possibility
		        is_convoy_possible = False
		        if unit.type == 'A' and unit.area.board_area.is_coast and destination.board_area.is_coast:
		            # Check if ANY fleet is ordered to convoy this unit to this destination
		            if Order.objects.filter(
		                unit__player__game=self, code='C', confirmed=True,
		                subunit=unit, subdestination=destination
		            ).exists():
		                 # Basic check: At least one fleet is trying. Full path check is complex.
		                 # Assume possible if at least one convoy order exists.
		                 is_convoy_possible = True
		                 # TODO: Implement full find_convoy_line check here if needed for stricter validation.

		        if not is_convoy_possible:
		            info += f"Impossible attack: {order}. Area not adjacent and no valid convoy.\n"
		            orders_to_delete.append(order.id)

		if orders_to_delete:
		    Order.objects.filter(id__in=orders_to_delete).delete()
		    info += f"Deleted {len(orders_to_delete)} unreachable attack orders.\n"
		return info


	def resolve_auto_garrisons(self):
		""" Units with '= G' orders in areas without a garrison, convert into garrison. """
		info = u"Step 1: Process unopposed conversions to Garrison.\n"
		garrisoning_orders = Order.objects.filter(unit__player__game=self, code='=', type='G', confirmed=True)
		orders_to_delete = []
		units_converted = []

		for g_order in garrisoning_orders:
		    unit = g_order.unit
		    info += f"{unit} tries to convert into garrison in {unit.area}.\n"
		    # Check if city already has a garrison
		    if Unit.objects.filter(area=unit.area, type='G').exists():
		        info += f"Fail: Garrison already exists in {unit.area}.\n"
		        orders_to_delete.append(g_order.id) # Order fails
		    else:
		        # Check if another unit is trying to convert to G in the same area
		        competing_conversions = garrisoning_orders.filter(unit__area=unit.area).exclude(id=g_order.id)
		        if competing_conversions.exists():
		             info += f"Fail: Competing conversion to Garrison in {unit.area}.\n"
		             # Both fail? Or highest strength wins? Rules don't specify. Assume both fail.
		             orders_to_delete.append(g_order.id)
		             for comp_order in competing_conversions:
		                 if comp_order.id not in orders_to_delete: orders_to_delete.append(comp_order.id)
		        else:
		            # Conversion successful
		            info += f"Success! {unit} converts to Garrison.\n"
		            unit.convert('G') # Update unit type
		            units_converted.append(unit.id)
		            orders_to_delete.append(g_order.id) # Order completed

		if orders_to_delete:
		    Order.objects.filter(id__in=orders_to_delete).delete()
		    info += f"Processed {len(garrisoning_orders)} Garrison conversion orders.\n"

		return info


	def resolve_conflicts(self):
		""" Resolves conflicts based on strength and orders. (Rule VIII.B) """
		info = u"Step 5: Process conflicts.\n"
		# Get all potentially conflicting orders (Advance, Convert A/F)
		conflicting_orders = Order.objects.filter(
		    unit__player__game=self, confirmed=True
		).exclude(code__in=['H', 'S', 'B', 'C', 'L', '0', '=G']) # Exclude non-moving/non-province-entering orders

		# Identify unique target areas for these orders
		target_areas = set()
		for order in conflicting_orders:
		    target_area = order.get_attacked_area()
		    if target_area: target_areas.add(target_area)

		processed_units = set() # Track units whose orders have been resolved (succeeded, failed, or retreated)
		retreating_units = {} # unit_id: source_area_code

		for area in target_areas:
		    info += f"\nResolving conflicts for area: {area.board_area.code}\n"
		    area.standoff = False # Reset standoff status for this turn's resolution

		    # Units trying to ENTER this area (Advance or Convert G->A/F from elsewhere)
		    invading_orders = conflicting_orders.filter(
		        Q(code='-', destination=area) |
		        Q(code='=', unit__area=area, type__in=['A', 'F']) # Convert G->A/F happens *in* the area
		    )

		    # Unit(s) currently OCCUPYING this area (A/F unit)
		    occupying_units = Unit.objects.filter(area=area, type__in=['A', 'F'])
		    occupying_order = None
		    occupier = None
		    if occupying_units.count() > 1:
		         # Should not happen based on rules, log error
		         if logging: logging.error(f"Game {self.id}: Multiple A/F units found in {area.board_area.code}")
		         continue # Skip resolution for this broken state area
		    elif occupying_units.count() == 1:
		         occupier = occupying_units.first()
		         occupying_order = Order.objects.filter(unit=occupier, confirmed=True).first()
		         # If occupier is already retreating, ignore them for defense calc
		         if occupier.id in retreating_units:
		             occupier = None
		             occupying_order = None


		    # --- Calculate Strengths ---
		    invader_strengths = {} # {order_id: strength}
		    for order in invading_orders:
		        if order.unit.id in processed_units: continue # Skip already processed units
		        strength_obj = Unit.objects.get_with_strength(self.game, id=order.unit.id)
		        invader_strengths[order.id] = strength_obj.strength
		        info += f"Invader: {order.unit} (Strength: {strength_obj.strength})\n"

		    occupier_strength = 0
		    if occupier and occupier.id not in processed_units:
		        # Occupier strength includes support for HOLDING
		        hold_support_query = Q(unit__player__game=self, code='S', confirmed=True, subunit=occupier, subcode='H')
		        hold_support_sum = Order.objects.filter(hold_support_query).aggregate(support_power=Sum('unit__power'))
		        hold_support_strength = hold_support_sum['support_power'] or 0
		        occupier_strength = occupier.power + hold_support_strength
		        info += f"Occupier: {occupier} (Strength: {occupier_strength})\n"


		    # --- Resolve Standoffs among Invaders ---
		    max_invader_strength = 0
		    winners = []
		    if invader_strengths:
		        max_invader_strength = max(invader_strengths.values())
		        winners = [oid for oid, s in invader_strengths.items() if s == max_invader_strength]

		    if len(winners) > 1: # Standoff among invaders (Rule VIII.B.3.a)
		        info += f"Standoff among invaders for {area.board_area.code} (Strength: {max_invader_strength}).\n"
		        area.standoff = True
		        area.save()
		        # All involved invaders fail and hold
		        for order_id in invader_strengths.keys():
		            order = Order.objects.get(id=order_id)
		            processed_units.add(order.unit.id)
		            order.delete() # Failed order
		        # Occupier (if any) holds successfully
		        if occupier: processed_units.add(occupier.id)
		        continue # Move to next area

		    # --- Resolve Single Winner vs Occupier ---
		    winning_order = None
		    if len(winners) == 1:
		        winning_order = Order.objects.get(id=winners[0])
		        winning_strength = max_invader_strength
		        info += f"Winning invader: {winning_order.unit} (Strength: {winning_strength})\n"

		        # Compare winner vs occupier
		        if occupier:
		            if winning_strength > occupier_strength: # Invader wins, occupier retreats (Rule VIII.B.4.b/c)
		                info += f"{winning_order.unit} dislodges {occupier}.\n"
		                retreating_units[occupier.id] = winning_order.unit.area.board_area.code # Retreat FROM attacker's origin
		                processed_units.add(occupier.id)
		                if occupying_order: occupying_order.delete() # Occupier's order fails
		                # Winning order succeeds
		                if winning_order.code == '-': winning_order.unit.invade_area(area)
		                elif winning_order.code == '=': winning_order.unit.convert(winning_order.type)
		                processed_units.add(winning_order.unit.id)
		                winning_order.delete() # Order completed
		            elif winning_strength == occupier_strength: # Bounce / Standoff (Rule VIII.B.3.c/d)
		                info += f"Bounce between {winning_order.unit} and {occupier}.\n"
		                area.standoff = True # Mark area as standoff for retreat purposes
		                area.save()
		                # Both units hold
		                processed_units.add(winning_order.unit.id)
		                winning_order.delete() # Failed order
		                processed_units.add(occupier.id)
		                # Occupier's support might be cut if attacker wasn't from supported area (handled in filter_supports)
		            else: # Occupier wins, invader holds (Rule VIII.B.4.e)
		                info += f"{occupier} holds against {winning_order.unit}.\n"
		                processed_units.add(winning_order.unit.id)
		                winning_order.delete() # Failed order
		                processed_units.add(occupier.id)
		        else: # No occupier, invader succeeds
		            info += f"{winning_order.unit} successfully enters empty {area.board_area.code}.\n"
		            if winning_order.code == '-': winning_order.unit.invade_area(area)
		            elif winning_order.code == '=': winning_order.unit.convert(winning_order.type)
		            processed_units.add(winning_order.unit.id)
		            winning_order.delete() # Order completed

		    elif not winners and occupier: # No invaders, occupier holds
		         info += f"Occupier {occupier} holds uncontested.\n"
		         processed_units.add(occupier.id)
		         # Occupier executes its original order if it wasn't just holding
		         if occupying_order and occupying_order.code != 'H':
		             # This logic needs care - if occupier was moving OUT, it should have happened already.
		             # Assume occupier holds if no invaders.
		             pass


		# --- Update retreating units ---
		for unit_id, source_code in retreating_units.items():
		    try:
		        unit = Unit.objects.get(id=unit_id)
		        unit.must_retreat = source_code
		        unit.save()
		    except Unit.DoesNotExist:
		        pass # Unit might have been disbanded by other means

		# --- Cleanup remaining confirmed orders (should be only Holds, Supports, etc.) ---
		remaining_orders = Order.objects.filter(unit__player__game=self, confirmed=True).exclude(unit_id__in=processed_units)
		# Process Holds, Supports, Convoys, Lifts, Disbands that weren't involved in conflicts
		for order in remaining_orders:
		     if order.code == 'L': # Lift Siege
		         if order.unit.siege_stage > 0:
		             order.unit.siege_stage = 0
		             order.unit.besieging = False
		             order.unit.save()
		             info += f"{order.unit} lifts siege.\n"
		         order.delete()
		     elif order.code == '0': # Disband
		         info += f"{order.unit} disbands.\n"
		         order.unit.delete() # Delete the unit
		         # Order deleted implicitly with unit
		     elif order.code == 'C': # Convoy (if not cancelled earlier)
		         # Convoy itself doesn't move the fleet, just enables army move
		         info += f"{order.unit} provides convoy.\n"
		         order.delete()
		     elif order.code in ['H', 'S', 'B']:
		         # These orders mean the unit holds its position.
		         # Sieges ('B') are handled separately in resolve_sieges.
		         # Supports ('S') enable other moves but don't move unit.
		         # Holds ('H') do nothing.
		         # Delete the order as it's conceptually completed for the turn.
		         if order.code != 'B': # Keep Besiege orders for resolve_sieges
		              order.delete()

		info += u"End of conflicts processing.\n"
		return info


	def resolve_sieges(self):
		""" Handles starting, continuing, and resolving sieges based on siege_stage. (Rule VIII.C.2) """
		info = u"Step 6: Process sieges.\n"

		# Process units ordered to Besiege ('B')
		besieging_orders = Order.objects.filter(unit__player__game=self, code='B', confirmed=True)
		for b_order in besieging_orders:
			b = b_order.unit
			info += f"{b} ordered to besiege in {b.area}. "
			target_unit = None
			target_rebellion = None

			# Check if player is assassinated (cannot progress siege - Rule VI.C.6.d)
			if b.player.assassinated:
				info += "Player assassinated. Siege does not progress.\n"
				b_order.delete() # Consume the order
				continue

			# Find target (Garrison or Rebellion)
			try:
				target_unit = Unit.objects.get(area=b.area, type='G')
				if target_unit.player == b.player: target_unit = None # Cannot besiege self
				else: info += f"Target: Garrison {target_unit}. "
			except Unit.DoesNotExist:
				target_rebellion = b.area.has_rebellion(b.player, same=False) # Target enemy rebellion
				if target_rebellion and target_rebellion.garrisoned:
				    info += "Target: Garrisoned Rebellion. "
				else: target_rebellion = None # Not a valid target

			if not target_unit and not target_rebellion:
			    info += "No valid target found. Invalid siege order.\n"
			    b_order.delete()
			    continue

			# --- Process Siege Stages ---
			if b.siege_stage == 0: # Start siege (Stage 1)
				b.siege_stage = 1
				b.besieging = True
				b.save()
				info += "Siege started (Stage 1).\n"
				if signals: signals.siege_started.send(sender=b)
				# Check immediate surrender if target assassinated (Rule VI.C.6.e)
				if target_unit and target_unit.player.assassinated:
				    info += "Target player assassinated! Garrison surrenders.\n"
				    if signals: signals.unit_surrendered.send(sender=target_unit, context="assassination")
				    target_unit.delete()
				    b.siege_stage = 0; b.besieging = False; b.save() # Reset siege

			elif b.siege_stage == 1: # Continue siege (Stage 2)
				b.siege_stage = 2
				b.save()
				info += "Siege continues (Stage 2).\n"
				# Check immediate surrender if target assassinated
				if target_unit and target_unit.player.assassinated:
				    info += "Target player assassinated! Garrison surrenders.\n"
				    if signals: signals.unit_surrendered.send(sender=target_unit, context="assassination")
				    target_unit.delete()
				    b.siege_stage = 0; b.besieging = False; b.save() # Reset siege

			elif b.siege_stage == 2: # Siege successful (End of Stage 2)
				info += "Siege successful! "
				if target_unit:
					info += f"Garrison {target_unit} removed.\n"
					if signals: signals.unit_surrendered.send(sender=target_unit, context="siege")
					target_unit.delete()
				elif target_rebellion:
					info += "Rebellion removed.\n"
					target_rebellion.delete()
				b.siege_stage = 0 # Reset siege state
				b.besieging = False
				b.save()

			b_order.delete() # Consume the Besiege order

		# Process units ordered to Lift Siege ('L') - Handled in resolve_conflicts cleanup now

		# Reset siege stage for units that *were* besieging but didn't get a 'B' order this turn
		broken_sieges = Unit.objects.filter(
		    player__game=self, siege_stage__gt=0
		).exclude(id__in=besieging_orders.values_list('unit_id', flat=True)) # Exclude units that got 'B' order

		for b in broken_sieges:
			info += f"Siege by {b} broken (no Besiege order given).\n"
			b.siege_stage = 0
			b.besieging = False
			b.save()

		return info


	def announce_retreats(self):
		""" Logs units that must retreat. """
		info = u"Step 7: Announce Retreats\n"
		retreating = Unit.objects.filter(player__game=self).exclude(must_retreat__exact='')
		if retreating.exists():
		    for u in retreating:
		        info += f"{u} must retreat from {u.area} (attack from {u.must_retreat}).\n"
		        if signals: signals.forced_to_retreat.send(sender=u)
		else:
		    info += "No retreats required this turn.\n"
		return info


	def preprocess_orders(self):
		"""
		Deletes unconfirmed orders and logs confirmed ones.
		"""
		## delete all orders that were not confirmed
		Order.objects.filter(unit__player__game=self, confirmed=False).delete()
		## delete all orders sent by players that don't control the unit
		if self.configuration.finances:
			Order.objects.filter(player__game=self).exclude(player=F('unit__player')).delete()
		## cancel interrupted sieges
		besieging = Unit.objects.filter(player__game=self, besieging=True)
		for u in besieging:
			try:
				Order.objects.get(unit=u, code='B')
			except ObjectDoesNotExist:
				u.besieging = False
				u.save()
		## log the rest of the orders
		for o in Order.objects.filter(player__game=self, confirmed=True):
			if o.code != 'H':
				if signals:
					signals.order_placed.send(sender=o)
	
	def process_orders(self):
		""" Run a batch of methods in the correct order to process all the orders.
		"""
		self.preprocess_orders()
		info = u"Processing orders in game %s\n" % self.slug
		info += u"------------------------------\n\n"
		info += self.resolve_auto_garrisons()
		info += u"\n"
		info += self.filter_supports()
		info += u"\n"
		info += self.filter_convoys()
		info += u"\n"
		info += self.filter_unreachable_attacks()
		info += u"\n"
		info += self.resolve_conflicts() # This needs careful review for all rules
		info += u"\n"
		info += self.resolve_sieges() # This needs update for siege duration
		info += u"\n"
		info += self.announce_retreats()
		info += u"--- END ---\n"
		if logging:
			logging.info(info)
		turn_log = TurnLog(game=self, year=self.year,
							season=self.season,
							phase=self.phase, # Log the phase where orders were executed
							log=info)
		turn_log.save()

	def process_retreats(self):
		""" Processes RetreatOrder objects created by the view. (Rule VIII.B.6) """
		info = u"Processing Retreats:\n"
		retreat_orders = RetreatOrder.objects.filter(unit__player__game=self)

		# Units ordered to disband
		disband_units = retreat_orders.filter(area__isnull=True).values_list('unit', flat=True)
		if disband_units:
		    units_to_delete = Unit.objects.filter(id__in=disband_units)
		    info += f"Disbanding units: {', '.join(map(str, units_to_delete))}\n"
		    units_to_delete.delete()

		# Units ordered to retreat to a specific area
		move_orders = retreat_orders.exclude(area__isnull=True)
		area_counts = move_orders.values('area').annotate(count=Count('id'))

		orders_to_process = list(move_orders) # Process individually

		for order in orders_to_process:
		    unit = order.unit
		    destination = order.area
		    area_conflict = False
		    for area_count in area_counts:
		        if area_count['area'] == destination.id and area_count['count'] > 1:
		            area_conflict = True
		            break

		    if area_conflict:
		        # Multiple units trying to retreat to the same spot -> all disband (Rule VIII.B.6.e implies this?)
		        # Rule doesn't explicitly state multiple retreats cause disband, only if *no* place is available.
		        # Let's follow common Diplomacy interpretation: retreat conflict = disband.
		        info += f"Retreat conflict for {unit} targeting {destination}. Unit disbands.\n"
		        try: unit.delete()
		        except Unit.DoesNotExist: pass # Might already be deleted if involved in multiple conflicts
		    else:
		        # Check if destination is still valid (not standoff, not occupied by A/F)
		        try:
		            dest_area = GameArea.objects.get(id=destination.id)
		            can_retreat_here = True
		            if dest_area.standoff: # Rule VIII.B.6.c.1
		                info += f"Cannot retreat {unit} to {destination}: Area is standoff.\n"
		                can_retreat_here = False
		            if Unit.objects.filter(area=dest_area, type__in=['A','F']).exists():
		                info += f"Cannot retreat {unit} to {destination}: Area occupied.\n"
		                can_retreat_here = False
		            # Cannot retreat where attacker came from (already filtered in get_possible_retreats)

		            if can_retreat_here:
		                info += f"{unit} retreats to {destination}.\n"
		                unit.retreat(destination) # Handles conversion if retreating to own city
		            else:
		                 info += f"No valid retreat for {unit}. Unit disbands.\n"
		                 unit.delete()

		        except GameArea.DoesNotExist:
		             info += f"Retreat destination {destination.id} not found for {unit}. Unit disbands.\n"
		             try: unit.delete()
		             except Unit.DoesNotExist: pass
		        except Unit.DoesNotExist:
		             pass # Unit already deleted

		# Clean up processed RetreatOrder objects
		retreat_orders.delete()
		info += "Retreat processing complete.\n"
		if logging: logging.info(info)


	def update_controls(self):
		""" Updates area control based on unit presence at end of Fall. (Rule V.C) """
		if self.season != 3: return # Only happens end of Fall

		info = u"Updating Controls (End of Fall):\n"
		# Areas are controlled by the player with a unit (A/F/G) unless contested.
		# Control persists even if unit leaves, until another player's unit enters.

		for area in GameArea.objects.filter(game=self).exclude(board_area__is_sea=True):
		    units_in_area = area.unit_set.all()
		    players_present = set(u.player for u in units_in_area if u.player.user is not None) # Get unique players (excluding autonomous)

		    if len(players_present) == 1:
		        new_controller = players_present.pop()
		        if area.player != new_controller:
		            old_controller_name = area.player.country.name if area.player else "Neutral"
		            info += f"Area {area.board_area.code}: Control changed from {old_controller_name} to {new_controller.country.name}.\n"
		            area.player = new_controller
		            area.save()
		            if signals: signals.area_controlled.send(sender=area)
		    elif len(players_present) > 1:
		        # Contested area, no one controls (Rule V.C.1.a)
		        if area.player is not None:
		            info += f"Area {area.board_area.code}: Control lost by {area.player.country.name} (contested).\n"
		            area.player = None
		            area.save()
		    # If len(players_present) == 0, control remains with the last controller (area.player)
		if logging: logging.info(info)

	##---------------------
	## logging methods
	##---------------------

	def log_event(self, e, **kwargs):
		## TODO: CATCH ERRORS
		#event = e(game=self, year=self.year, season=self.season, phase=self.phase, **kwargs)
		#event.save()
		pass


	##------------------------
	## game ending methods
	##------------------------

	def check_winner(self):
		""" Returns True if at least one player has met the victory conditions. """
		for p in self.player_set.filter(user__isnull=False, eliminated=False):
			num_cities = p.number_of_cities()
			if num_cities >= self.cities_to_win:
				# Basic condition: Just number of cities
				if self.victory_condition_type == 'basic':
				    # Rule III.B: Must include all home cities and >= 6 conquered
				    home_cities_controlled = p.controlled_home_cities().count()
				    total_home_cities = p.home_country().filter(board_area__has_city=True).count()
				    conquered_cities = num_cities - home_cities_controlled
				    if home_cities_controlled == total_home_cities and conquered_cities >= 6:
				        return True
				# Advanced/Ultimate conditions: Number + Control of other home countries
				elif self.victory_condition_type in ['advanced', 'ultimate']:
				    required_conquered_homes = 1 if self.victory_condition_type == 'advanced' else 2
				    conquered_homes_count = 0
				    other_players = self.player_set.filter(user__isnull=False).exclude(id=p.id)
				    for other_p in other_players:
				        if other_p.is_fully_conquered_by(p):
				            conquered_homes_count += 1
				    if conquered_homes_count >= required_conquered_homes:
				        return True
				# Could add a 'custom' type check here if needed
		return False

	def assign_scores(self):
		qual = []
		for p in self.player_set.filter(user__isnull=False):
			qual.append((p, p.number_of_cities()))
		## sort the players by their number of cities, less cities go first
		qual.sort(cmp=lambda x,y: cmp(x[1], y[1]), reverse=False)
		zeros = len(qual) - len(SCORES)
		assignation = SCORES + [0] * zeros
		for s in assignation:
			try:
				q = qual.pop()
			except:
				exit
			else:
				# add the number of cities to the score
				score = Score(user=q[0].user, game=q[0].game,
							country=q[0].country,
							points = s + q[1],
							cities = q[1])
				score.save()
				## add the points to the profile total_score
				score.user.get_profile().total_score += score.points
				score.user.get_profile().save()
				## highest score = last score
				while qual != [] and qual[-1][1] == q[1]:
					tied = qual.pop()
					score = Score(user=tied[0].user, game=tied[0].game,
								country=tied[0].country,
								points = s + tied[1],
								cities = tied[1])
					score.save()
					## add the points to the profile total_score
					score.user.get_profile().total_score += score.points
					score.user.get_profile().save()

	def game_over(self):
		self.phase = PHINACTIVE
		self.finished = datetime.now()
		self.save()
		if signals:
			signals.game_finished.send(sender=self)
		self.notify_players("game_over", {"game": self})
		self.tweet_message("The game %(game)s is over" % {'game': self.slug})
		self.tweet_results()
		self.clean_useless_data()

	def clean_useless_data(self):
		""" In a finished game, delete all the data that is not going to be used
		anymore. """

		self.player_set.all().delete()
		self.gamearea_set.all().delete()
		self.invitation_set.all().delete()
		self.whisper_set.all().delete()
	
	##------------------------
	## notification methods
	##------------------------

	def notify_players(self, label, extra_context={}, on_site=True):
		if notification:
			users = User.objects.filter(player__game=self,
										player__eliminated=False)
			extra_context.update({'STATIC_URL': settings.STATIC_URL, })
			if self.fast:
				notification.send_now(users, label, extra_context, on_site)
			else:
				notification.send(users, label, extra_context, on_site)

	def tweet_message(self, message):
		if twitter_api:
			#thread.start_new_thread(twitter_api.PostUpdate, (message,))
			twitter_api.PostUpdate(message)

	def tweet_results(self):
		if twitter_api:
			#winners = self.player_set.order_by('-score')
			winners = self.score_set.order_by('-points')
			message = "'%s' - Winner: %s; 2nd: %s; 3rd: %s" % (self.slug,
							winners[0].user,
							winners[1].user,
							winners[2].user)
			self.tweet_message(message)

if twitter_api and settings.TWEET_NEW_GAME:
	def tweet_new_game(sender, instance, created, **kw):
		if twitter_api and isinstance(instance, Game):
			if created == True:
				message = "New game: http://www.condottierigame.com%s" % instance.get_absolute_url()
				twitter_api.PostUpdate(message)

	models.signals.post_save.connect(tweet_new_game, sender=Game)

class GameArea(models.Model):
	""" This class defines the actual game areas where each game is played. """

	game = models.ForeignKey(Game)
	board_area = models.ForeignKey(Area)
	## player is who controls the area, if any
	player = models.ForeignKey('Player', blank=True, null=True)
	standoff = models.BooleanField(default=False)
	famine = models.BooleanField(default=False) # Optional Rule III.B
	storm = models.BooleanField(default=False)  # Optional Rule III.C

	def abbr(self):
		return "%s (%s)" % (self.board_area.code, self.board_area.name)

	def __unicode__(self):
		#return self.board_area.name
		#return "(%(code)s) %(name)s" % {'name': self.board_area.name, 'code': self.board_area.code}
		return unicode(self.board_area)

	def accepts_type(self, type):
		return self.board_area.accepts_type(type)
	
	def possible_reinforcements(self):
		""" Returns a list of possible unit types for an area. """

		existing_types = []
		result = []
		units = self.unit_set.all()
		for unit in units:
	        	existing_types.append(unit.type)
		if self.accepts_type('G') and not "G" in existing_types:
			result.append('G')
		if self.accepts_type('F') and not ("A" in existing_types or "F" in existing_types):
			result.append('F')
		if self.accepts_type('A') and not ("A" in existing_types or "F" in existing_types):
			result.append('A')
		return result

	def mark_as_standoff(self):
		if signals:
			signals.standoff_happened.send(sender=self)
		else:
			self.game.log_event(StandoffEvent, area=self.board_area)
		self.standoff = True
		self.save()

	def province_is_empty(self):
		return self.unit_set.exclude(type__exact='G').count() == 0

	def get_adjacent_areas(self, include_self=False):
		""" Returns a queryset with all the adjacent GameAreas """
		if include_self:
			cond = Q(board_area__borders=self.board_area, game=self.game) | Q(id=self.id)
		else:
			cond = Q(board_area__borders=self.board_area, game=self.game)
		adj = GameArea.objects.filter(cond).distinct()
		return adj
	
	def has_rebellion(self, player, same=True):
		""" If there is a rebellion in the area, either against the player or
		against any other player, returns the rebellion. """
		try:
			if same:
				reb = Rebellion.objects.get(area=self, player=player)
			else:
				reb = Rebellion.objects.exclude(player=player).get(area=self)
		except ObjectDoesNotExist:
			return False
		return reb

	def check_assassination_rebellion(self):
		""" When a player is assassinated this function checks if a new
		rebellion appears in the game area, according to Rule VI.C.6.f. """
		if not self.player or not self.player.assassinated: # Only if controlled by assassinated player
		    return False
		if self.board_area.is_sea:
			return False
		# Rule implies rebellion happens unless *another* player's unit is present.
		if Unit.objects.filter(area=self).exclude(player=self.player).exists():
			return False
		if self.has_rebellion(self.player): # Already rebelling
		    return False

		result = False
		die = dice.roll_1d6()
		is_occupied_by_owner = Unit.objects.filter(area=self, player=self.player).exists()
		is_home_province = self in self.player.home_country() # Assumes home_country() is correct

		if is_home_province:
			if is_occupied_by_owner and die == 1: result = True
			elif not is_occupied_by_owner and die in (1, 2): result = True
		else: # Conquered province
			if is_occupied_by_owner and die in (1, 2, 3): result = True
			elif not is_occupied_by_owner and die != 6: result = True

		if result:
			rebellion = Rebellion(area=self)
			# Rebellion model needs to correctly determine player and garrisoned status on save
			rebellion.save()
			if logging: logging.info("Assassination rebellion in %s" % self)
		return result


def check_min_karma(sender, instance=None, **kwargs):
	if isinstance(instance, CondottieriProfile):
		if instance.karma < settings.KARMA_TO_JOIN:		
			players = Player.objects.filter(user=instance.user,
											game__slots__gt=0)
			for p in players:
				game = p.game
				if not game.private:
					p.delete()
					game.slots += 1
					game.save()
	
models.signals.post_save.connect(check_min_karma, sender=CondottieriProfile)


class Score(models.Model):
	""" This class defines the scores that a user got in a finished game. """

	user = models.ForeignKey(User)
	game = models.ForeignKey(Game)
	country = models.ForeignKey(Country)
	points = models.PositiveIntegerField(default=0)
	cities = models.PositiveIntegerField(default=0)
	position = models.PositiveIntegerField(default=0)
	""" Default value is added for compatibility with south, to be deleted after migration """
	created_at = models.DateTimeField(auto_now_add=True)

	def __unicode__(self):
		return "%s (%s)" % (self.user, self.game)

class Player(models.Model):
	""" This class defines the relationship between a User and a Game. """

	user = models.ForeignKey(User, blank=True, null=True) # Null for autonomous units
	game = models.ForeignKey(Game)
	country = models.ForeignKey(Country, blank=True, null=True)
	done = models.BooleanField(default=False)
	eliminated = models.BooleanField(default=False)
	conqueror = models.ForeignKey('self', related_name='conquered', blank=True, null=True)
	excommunicated = models.PositiveIntegerField(blank=True, null=True) # Seems unused?
	assassinated = models.BooleanField(default=False) # Advanced VI.C.6
	defaulted = models.BooleanField(default=False) # Optional X.B
	ducats = models.PositiveIntegerField(default=0) # Advanced V
	double_income = models.BooleanField(default=False) # Advanced V.B.1.d
	may_excommunicate = models.BooleanField(default=False) # Implied Papacy ability
	static_name = models.CharField(max_length=20, default="")
	step = models.PositiveIntegerField(default=0)
	has_sentenced = models.BooleanField(default=False) # Related to excommunication
	is_excommunicated = models.BooleanField(default=False) # Related to excommunication
	pope_excommunicated = models.BooleanField(default=False) # Related to excommunication


	def __unicode__(self):
		if self.user:
			return "%s (%s)" % (self.user, self.game)
		else:
			return "Autonomous in %s" % self.game

	def get_language(self):
		if self.user:
			return self.user.account_set.all()[0].get_language_display()
		else:
			return ''
	
	def get_setups(self):
		return Setup.objects.filter(scenario=self.game.scenario,
				country=self.country).select_related()
	
	def home_control_markers(self):
		""" Assigns each GameArea the player as owner. """
		GameArea.objects.filter(game=self.game,
								board_area__home__scenario=self.game.scenario,
								board_area__home__country=self.country).update(player=self)
	
	def place_initial_units(self):
		for s in self.get_setups():
			try:
				a = GameArea.objects.get(game=self.game, board_area=s.area)
			except:
				print "Error 2: Area not found!"
			else:
				#a.player = self
				#a.save()
				if s.unit_type:
					new_unit = Unit(type=s.unit_type, area=a, player=self, paid=False)
					new_unit.save()
	
	def number_of_cities(self):
		""" Returns the number of cities controlled by the player. """

		cities = GameArea.objects.filter(player=self, board_area__has_city=True)
		return len(cities)

	def number_of_units(self):
		## this funcion is deprecated
		return self.unit_set.all().count()

	def placed_units_count(self):
		return self.unit_set.filter(placed=True).count()
	
	def units_to_place(self):
		""" Return the number of units that the player must place. Negative if
		the player has to remove units.
		"""

		if not self.user:
			return 0
		cities = self.number_of_cities()
		if self.game.configuration.famine:
			famines = self.gamearea_set.filter(famine=True, board_area__has_city=True).exclude(unit__type__exact='G').count()
			cities -= famines
		units = len(self.unit_set.all())
		place = cities - units
		slots = len(self.get_areas_for_new_units())
		if place > slots:
			place = slots
		return place
	
	def home_country(self, original=True):
		""" Returns a queryset with Game Areas in home country.
		    If original=True, returns only the starting home country.
		    If original=False, includes conquered home countries. (Rule V.D.2)
		"""
		q = Q(game=self.game) & Q(board_area__home__scenario=self.game.scenario) & Q(board_area__home__is_home=True)
		if original:
		    q &= Q(board_area__home__country=self.country)
		else:
		    conquered_countries = [c.country for c in self.conquered.all()]
		    q &= (Q(board_area__home__country=self.country) | Q(board_area__home__country__in=conquered_countries))
		return GameArea.objects.filter(q)

	def controlled_home_country(self):
		""" Returns a queryset with GameAreas in home country controlled by player.
		"""

		return self.home_country().filter(player=self)

	def controlled_home_cities(self, original=True):
		""" Returns a queryset with GameAreas in home country, with city,
		controlled by the player """
		return self.home_country(original=original).filter(player=self, board_area__has_city=True)

	def get_areas_for_new_units(self, finances=False):
		""" Returns a queryset with the GameAreas that accept new units.
		    Rule V.B.1.b/c (Basic) / V.B.3.b/c (Advanced)
		"""
		# Placement only in controlled home city provinces (original or conquered)
		q = Q(player=self) & Q(board_area__has_city=True) & Q(famine=False) # Must control, have city, not famine
		q &= Q(board_area__home__scenario=self.game.scenario) & Q(board_area__home__is_home=True)

		# Determine which home countries are valid for placement
		valid_home_countries = [self.country]
		if self.game.configuration.conquering:
		    # Check if any conquered countries are fully controlled for placement (Rule V.D.2.b)
		    for conquered_player in self.conquered.all():
		        if conquered_player.is_fully_conquered_by(self): # Need this helper method
		             valid_home_countries.append(conquered_player.country)

		q &= Q(board_area__home__country__in=valid_home_countries)

		areas = GameArea.objects.filter(q)

		# Exclude areas where placement is blocked (Rule V.B.1.b/c)
		excludes = []
		for a in areas:
			units_in_area = a.unit_set.count()
			units_in_city = a.unit_set.filter(type='G').count()
			units_in_province = units_in_area - units_in_city

			# Cannot place if both city and province are occupied
			if units_in_city > 0 and units_in_province > 0:
				excludes.append(a.id)
			# Cannot place if target spot (city/province) is occupied
			# This needs form input to know if placing in city or province
			# Simplification: Assume we can place if *either* city or province is free.
			# A stricter interpretation might require the form to specify city/province placement.

		if finances:
			# Exclude areas where an existing unit hasn't been paid (prevents replacing unpaid)
			for u in self.unit_set.filter(placed=True, paid=False):
				if u.area_id not in excludes:
				    excludes.append(u.area_id)

		areas = areas.exclude(id__in=excludes)
		return areas


	def is_fully_conquered_by(self, potential_conqueror):
	    """ Checks if this player's original home country is fully controlled
	        by the potential_conqueror. (Helper for Rule V.D.2.a/b) """
	    if not self.country: return False # Autonomous players cannot be conquered this way
	    home_provinces = GameArea.objects.filter(
	        game=self.game,
	        board_area__home__scenario=self.game.scenario,
	        board_area__home__country=self.country,
	        board_area__home__is_home=True
	    )
	    if not home_provinces.exists(): return False # No home provinces defined?

	    # Check if all home provinces are controlled by the potential conqueror
	    return not home_provinces.exclude(player=potential_conqueror).exists()


	def cancel_orders(self, hold=False):
		""" Deletes all the player's orders, optionally changing them to Hold first (for assassination). """
		if hold:
		    # Change all non-hold orders to Hold
		    # Note: This might conflict if a unit cannot legally Hold (e.g., mid-conversion?)
		    # Rule VI.C.6.d just says "paralyzed" and orders become "hold".
		    self.order_set.exclude(code='H').update(
		        code='H',
		        destination=None, type=None, subunit=None, subcode=None,
		        subdestination=None, subtype=None, confirmed=True # Ensure they are processed as holds
		    )
		    # If assassination paralysis prevents putting down rebellions (Rule VI.C.6.d),
		    # this needs handling in the rebellion resolution logic, not just changing order code.
		else:
		    self.order_set.all().delete()

	
    def check_eliminated(self):
        """ Checks if the player is eliminated based on Rule V.D.1 and V.D.2.c. """
        if not self.user: return False

        # Rule V.D.1: Check control of *any* original home city
        if self.controlled_home_cities(original=True).exists():
            return False # Still controls at least one original home city

        # Rule V.D.2.c: If no original home cities, check if *all* home provinces (original + conquered) are lost
        all_home_provinces = self.home_country(original=False)
        if not all_home_provinces.exists():
             # This case implies the player had no home country defined, shouldn't happen in normal scenarios
             if logging: logging.warning(f"Player {self} has no defined home provinces for elimination check.")
             # If they have no home provinces at all, are they eliminated? Assume yes if they also control no cities anywhere.
             return self.number_of_cities() == 0

        # Check if they control *any* province within their original OR conquered home countries
        if all_home_provinces.filter(player=self).exists():
            return False # Still controls at least one province in the combined home territories

        # If no original home cities controlled AND no provinces controlled in *any* home territory (original+conquered) -> Eliminated
        if logging: logging.info(f"Player {self} eliminated (lost all original home cities AND all provinces in combined home territories)")
        return True


	def eliminate(self):
		""" Eliminates the player and removes units, controls, etc. """
		if self.user and not self.eliminated: # Prevent double elimination
			self.eliminated = True
			self.ducats = 0
			self.is_excommunicated = False
			self.pope_excommunicated = False
			# Keep conqueror status if already conquered
			self.save()
			signals.country_eliminated.send(sender=self, country=self.country)
			if logging:
				msg = "Game %s: player %s (%s) has been eliminated." % (self.game.pk, self.user.username, self.country)
				logging.info(msg)

			# Remove units and control
			self.unit_set.all().delete()
			self.gamearea_set.all().update(player=None) # Remove control from all areas they owned
			self.order_set.all().delete() # Remove pending orders
			self.expense_set.all().delete() # Remove pending expenses
			self.assassination_attempts.all().delete() # Remove pending assassinations
			# Assassins targeting this player are removed in process_assassinations? Or should be here?
			# Loans are just lost? Rule X doesn't specify. Assume lost.
			Loan.objects.filter(player=self).delete()

			# Clear excommunications if they were the Pope (Rule implies Papacy is unique)
			if self.game.configuration.excommunication and self.may_excommunicate:
				self.game.player_set.all().update(is_excommunicated=False, pope_excommunicated=False)

			# Remove pending revolution attempts against this player
			Revolution.objects.filter(government=self).delete()

	def set_conqueror(self, player):
		if player != self:
			signals.country_conquered.send(sender=self, country=self.country)
			if logging:
				msg = "Player %s conquered by player %s" % (self.pk, player.pk)
				logging.info(msg)
			self.conqueror = player
			#if self.game.configuration.finances:
			#	if self.ducats > 0:
			#		player.ducats = F('ducats') + self.ducats
			#		player.save()
			#		self.ducats = 0
			self.save()

	def can_excommunicate(self):
		""" Returns true if player.may_excommunicate and the Player has not excommunicated or
		forgiven anyone this turn and there is no other player explicitly excommunicated """

		if self.eliminated:
			return False
		if self.game.configuration.excommunication:
			if self.may_excommunicate and not self.has_sentenced:
				try:
					Player.objects.get(game=self.game, pope_excommunicated=True)
				except ObjectDoesNotExist:
					return True
		return False

	def can_forgive(self):
		""" Returns true if player.may_excommunicate and the Player has not excommunicated or
		forgiven anyone this turn. """
		
		if self.eliminated:
			return False
		if self.game.configuration.excommunication:
			if self.may_excommunicate and not self.has_sentenced:
				return True
		return False

	def set_excommunication(self, by_pope=False):
		""" Excommunicates the player """
		self.is_excommunicated = True
		self.pope_excommunicated = by_pope
		self.save()
		self.game.reset_players_cache()
		signals.country_excommunicated.send(sender=self)
		if logging:
			msg = "Player %s excommunicated" % self.pk
			logging.info(msg)
	
	def unset_excommunication(self):
		self.is_excommunicated = False
		self.pope_excommunicated = False
		self.save()
		self.game.reset_players_cache()
		signals.country_forgiven.send(sender=self)
		if logging:
			msg = "Player %s is forgiven" % self.pk
			logging.info(msg)

	def assassinate(self):
		self.assassinated = True
		self.save()
		signals.player_assassinated.send(sender=self)

	def has_special_unit(self):
		try:
			Unit.objects.get(player=self, paid=True, cost__gt=3)
		except ObjectDoesNotExist:
			return False
		else:
			return True

	def end_phase(self, forced=False):
		self.done = True
		self.step = 0
		self.save()
		if not forced:
			if not self.game.fast and self.game.check_bonus_time():
				## get a karma bonus
				#self.user.stats.adjust_karma(1)
				self.user.get_profile().adjust_karma(1)
			## delete possible revolutions
			Revolution.objects.filter(government=self).delete()
			msg = "Player %s ended phase" % self.pk
		else:
			self.force_phase_change()
			msg = "Player %s forced to end phase" % self.pk
		#self.game.check_next_phase()
		if logging:
			logging.info(msg)

	def new_phase(self):
		## check that the player is not autonomous and is not eliminated
		if self.user and not self.eliminated:
			if self.game.phase == PHREINFORCE and not self.game.configuration.finances:
				if self.units_to_place() == 0:
					self.done = True
				else:
					self.done = False
			elif self.game.phase == PHORDERS:
				units = self.unit_set.all().count()
				if units <= 0:
					self.done = True
				else:
					self.done = False
			elif self.game.phase == PHRETREATS:
				retreats = self.unit_set.exclude(must_retreat__exact='').count()
				if retreats == 0:
					self.done = True
				else:
					self.done = False
			else:
				self.done = False
			self.save()

	def next_phase_change(self):
		""" Returns the time that the next forced phase change would happen,
		if this were the only player (i.e. only his own karma is considered)
		"""
		
		if self.game.fast:
			karma = 100.
		else:
			karma = float(self.user.get_profile().karma)
		if karma > 100:
			if self.game.phase == PHORDERS:
				k = 1 + (karma - 100) / 200
			else:
				k = 1
		else:
			k = karma / 100
		time_limit = self.game.time_limit * k
		
		duration = timedelta(0, time_limit)

		return self.game.last_phase_change + duration
	
	def time_to_limit(self):
		"""
		Calculates the time to the next phase change and returns it as a
		timedelta.
		"""
		return self.next_phase_change() - datetime.now()
	
	def in_last_seconds(self):
		"""
		Returns True if the next phase change would happen in a few minutes.
		"""
		return self.time_to_limit() <= timedelta(seconds=settings.LAST_SECONDS)
	
	def time_exceeded(self):
		""" Returns true if the player has exceeded his own time, and he is playing because
		other players have not yet finished. """

		return self.next_phase_change() < datetime.now()

	def get_time_status(self):
		""" Returns a string describing the status of the player depending on the time limits.
		This string is to be used as a css class to show the time """
		now = datetime.now()
		bonus = self.game.get_bonus_deadline()
		if now <= bonus:
			return 'bonus_time'
		safe = self.next_phase_change()
		if now <= safe:
			return 'safe_time'
		return 'unsafe_time'
	
	def force_phase_change(self):
		## the player didn't take his actions, so he loses karma
		if not self.game.fast:
			self.user.get_profile().adjust_karma(-10)
		## if there is a revolution with an overthrowing player, change users
		try:
			rev = Revolution.objects.get(government=self)
		except ObjectDoesNotExist:
			if not self.game.fast:
				## create a new possible revolution
				rev = Revolution(government=self)
				rev.save()
				logging.info("New revolution for player %s" % self)
		else:
			if rev.opposition:
				if notification:
					## notify the old player
					user = [self.user,]
					extra_context = {'game': self.game,}
					notification.send(user, "lost_player", extra_context, on_site=True)
					## notify the new player
					user = [rev.opposition]
					if self.game.fast:
						notification.send_now(user, "got_player", extra_context)	
					else:
						notification.send(user, "got_player", extra_context)
				logging.info("Government of %s is overthrown" % self.country)
				if signals:
					signals.government_overthrown.send(sender=self)
				else:
					self.game.log_event(CountryEvent,
								country=self.country,
								message=0)
				self.user = rev.opposition
				self.save()
				rev.delete()
				self.user.get_profile().adjust_karma(10)

	def unread_count(self):
		""" Gets the number of unread received letters """
		
		if condottieri_messages:
			return condottieri_messages.models.Letter.objects.filter(recipient_player=self, read_at__isnull=True, recipient_deleted_at__isnull=True).count()
		else:
			return 0
	
	
	##
	## Income calculation
	##
	def get_control_income(self, die, majors_ids, rebellion_ids):
		""" Gets the sum of the control income of all controlled AND empty
		provinces. Note that provinces affected by plague don't genearate
		any income"""
		gamearea_ids = self.gamearea_set.filter(famine=False).exclude(id__in=rebellion_ids).values_list('board_area', flat=True)
		income = Area.objects.filter(id__in = gamearea_ids).aggregate(Sum('control_income'))

		i =  income['control_income__sum']
		if i is None:
			return 0
		
		v = 0
		for a in majors_ids:
			if a in gamearea_ids:
				city = Area.objects.get(id=a)
				v += finances.get_ducats(city.code, die)

		return income['control_income__sum'] + v

	def get_occupation_income(self):
		""" Gets the sum of the income of all the armies and fleets in not controlled areas """
		units = self.unit_set.exclude(type="G").exclude(area__famine=True)
		units = units.filter(~Q(area__player=self) | Q(area__player__isnull=True))

		i = units.count()
		if i > 0:
			return i
		return 0

	def get_garrisons_income(self, die, majors_ids, rebellion_ids):
		""" Gets the sum of the income of all the non-besieged garrisons in non-controlled areas
		"""
		## get garrisons in non-controlled areas
		cond = ~Q(area__player=self)
		cond |= Q(area__player__isnull=True)
		cond |= (Q(area__player=self, area__famine=True))
		cond |= (Q(area__player=self, area__id__in=rebellion_ids))
		garrisons = self.unit_set.filter(type="G")
		garrisons = garrisons.filter(cond)
		garrisons = garrisons.values_list('area__board_area__id', flat=True)
		if len(garrisons) > 0:
			## get ids of gameareas where garrisons are under siege
			sieges = Unit.objects.filter(player__game=self.game, besieging=True)
			sieges = sieges.values_list('area__board_area__id', flat=True)
			## get the income
			income = Area.objects.filter(id__in=garrisons).exclude(id__in=sieges)
			if income.count() > 0:
				v = 0
				for a in income:
					if a.id in majors_ids:
						v += finances.get_ducats(a.code, die)
				income = income.aggregate(Sum('garrison_income'))
				return income['garrison_income__sum'] + v
		return 0

	def get_variable_income(self, die):
		""" Gets the variable income for the country """
		v = finances.get_ducats(self.static_name, die, self.double_income)
		## the player gets the variable income of conquered players
		if self.game.configuration.conquering:
			conquered = self.game.player_set.filter(conqueror=self)
			for c in conquered:
				v += finances.get_ducats(c.static_name, die, c.double_income)

		return v

	def get_income(self, die, majors_ids):
		""" Gets the total income in one turn """
		rebellion_ids = Rebellion.objects.filter(player=self).values_list('area', flat=True)
		income = self.get_control_income(die, majors_ids, rebellion_ids)
		income += self.get_occupation_income()
		income += self.get_garrisons_income(die, majors_ids, rebellion_ids)
		income += self.get_variable_income(die)
		return income

	def add_ducats(self, d):
		""" Adds d to the ducats field of the player."""
		self.ducats = F('ducats') + d
		self.save()
		signals.income_raised.send(sender=self, ducats=d)
		if logging:
			msg = "Player %s raised %s ducats." % (self.pk, d)
			logging.info(msg)

	def get_credit(self):
		""" Returns the number of ducats that the player can borrow from the bank. """
		if self.defaulted:
			return 0
		if self.game.configuration.unbalanced_loans:
			credit = 25
		else:
			credit = self.gamearea_set.count() + self.unit_set.count()
			if credit > 25:
				credit = 25
		return credit

	def check_no_units(self):
		""" Returns True if no players have any units left. """
		return not Unit.objects.filter(player__game=self, player__user__isnull=False).exists()

class Revolution(models.Model):
	""" A Revolution instance means that ``government`` is not playing, and
	``opposition`` is trying to replace it.
	"""

	government = models.ForeignKey(Player)
	opposition = models.ForeignKey(User, blank=True, null=True)

	def __unicode__(self):
		return "%s" % self.government

def notify_overthrow_attempt(sender, instance, created, **kw):
	if notification and isinstance(instance, Revolution) and not created:
		user = [instance.government.user,]
		extra_context = {'game': instance.government.game,}
		notification.send(user, "overthrow_attempt", extra_context , on_site=True)

models.signals.post_save.connect(notify_overthrow_attempt, sender=Revolution)

class UnitManager(models.Manager):
	def get_with_strength(self, game, **kwargs):
		u = self.get_query_set().get(**kwargs)
		# Basic strength is unit's power (usually 1, modified by special units)
		strength = u.power
		u_order = u.get_order()

		# Calculate support strength
		support_query = Q(unit__player__game=game, code='S', subunit=u)
		if not u_order or u_order.code in ('H', 'S', 'C', 'B', 'L', '0'): # Holding or non-moving order
			support_query &= Q(subcode='H') # Support Hold
		elif u_order.code == '=': # Conversion
			support_query &= Q(subcode='=', subtype=u_order.type) # Support Conversion
		elif u_order.code == '-': # Advance
			support_query &= Q(subcode='-', subdestination=u_order.destination) # Support Advance

		# Sum the 'power' of supporting units (Rule VIII.B.2, Optional IV)
		support_sum = Order.objects.filter(support_query).aggregate(support_power=Sum('unit__power'))
		support_strength = support_sum['support_power'] or 0

		strength += support_strength

		# Check for support from Rebellion (Advanced Rule VI.C.5.c.9)
		if game.configuration.finances and u_order and u_order.code == '-':
		    target_area = u_order.destination
		    rebellion = target_area.has_rebellion(u.player, same=False) # Rebellion against someone else
		    if rebellion:
		        # Check if multiple players are trying to use the same rebellion support
		        other_attackers = Order.objects.filter(
		            player__game=game, code='-', destination=target_area
		        ).exclude(unit=u).count()
		        if other_attackers == 0:
		            strength += 1 # Rebellion adds 1 strength

		# Check if support is cut (Rule VIII.B.3.d) - This needs to happen *during* conflict resolution, not here.
		# Strength calculation should be pure based on orders written.

		u.strength = strength
		return u

	def list_with_strength(self, game):
		from django.db import connection
		cursor = connection.cursor()
		cursor.execute("SELECT u.id, \
							u.type, \
							u.area_id, \
							u.player_id, \
							u.besieging, \
							u.must_retreat, \
							u.placed, \
							u.paid, \
							u.cost, \
							u.power, \
							u.loyalty, \
							o.code, \
							o.destination_id, \
							o.type \
		FROM (machiavelli_player p INNER JOIN machiavelli_unit u on p.id=u.player_id) \
		LEFT JOIN machiavelli_order o ON u.id=o.unit_id \
		WHERE p.game_id=%s" % game.id)
		result_list = []
		for row in cursor.fetchall():
			holding = False
			support_query = Q(unit__player__game=game,
							  code__exact='S',
							  subunit__pk=row[0])
			if row[11] in (None, '', 'H', 'S', 'C', 'B'): #unit is holding
				support_query &= Q(subcode__exact='H')
				holding = True
			elif row[11] == '=':
				support_query &= Q(subcode__exact='=',
						   		subtype__exact=row[13])
			elif row[11] == '-':
				support_query &= Q(subcode__exact='-',
								subdestination__pk__exact=row[12])
			#support = Order.objects.filter(support_query).count()
			support_sum = Order.objects.filter(support_query).aggregate(Sum('unit__power'))
			if support_sum['unit__power__sum'] is None:
				support = 0
			else:
				support = int(support_sum['unit__power__sum'])
			unit = self.model(id=row[0], type=row[1], area_id=row[2],
							player_id=row[3], besieging=row[4],
							must_retreat=row[5], placed=row[6], paid=row[7],
							cost=row[8], power=row[9], loyalty=row[10])
			if game.configuration.finances:
				if holding and unit.area.has_rebellion(unit.player, same=True):
					support -= 1
			unit.strength = unit.power + support
			result_list.append(unit)
		result_list.sort(cmp=lambda x,y: cmp(x.strength, y.strength), reverse=True)
		return result_list

class Unit(models.Model):
	""" This class defines a unit in a game, its location and status. """

	type = models.CharField(max_length=1, choices=UNIT_TYPES)
	area = models.ForeignKey(GameArea)
	player = models.ForeignKey(Player)
	besieging = models.BooleanField(default=False) # UI flag, logic uses siege_stage
	siege_stage = models.PositiveSmallIntegerField(default=0, help_text="0:Not besieging, 1:Besieging(1st turn), 2:Besieging(2nd turn)") # Added
	must_retreat = models.CharField(max_length=5, blank=True, default='')
	placed = models.BooleanField(default=True)
	paid = models.BooleanField(default=True) # Advanced V.B.3
	cost = models.PositiveIntegerField(default=3) # Advanced V.B.3 / Optional IV
	power = models.PositiveIntegerField(default=1) # Optional IV
	loyalty = models.PositiveIntegerField(default=1) # Optional IV / Advanced VI.C.4.g

	objects = UnitManager()

	def get_order(self):
		""" If the unit has more than one order, raises an error. If not, return the order.
		When this method is called, each unit should have 0 or 1 order """
		try:
			order = Order.objects.get(unit=self)
		except MultipleObjectsReturned:
			raise MultipleObjectsReturned
		except:
			return None
		else:
			return order
	
	def get_attacked_area(self):
		""" If the unit has orders, get the attacked area, if any. This method is
		only a proxy of the Order method with the same name.
		"""
		order = self.get_order()
		if order:
			return order.get_attacked_area()
		else:
			return GameArea.objects.none()

	def supportable_order(self):
		"""Returns a description of the unit for the support order dropdown.
		Only shows the unit's type and location, not its orders."""
		return _("%(type)s in %(area)s") % {
			'type': self.get_type_display(),
			'area': self.area
		}

	def place(self):
		self.placed = True
		self.paid = False ## to be unpaid in the next reinforcement phase
		if signals:
			signals.unit_placed.send(sender=self)
		else:
			self.player.game.log_event(NewUnitEvent, country=self.player.country,
								type=self.type, area=self.area.board_area)
		self.save()

	def delete(self):
		if signals:
			signals.unit_disbanded.send(sender=self)
		else:
			self.player.game.log_event(DisbandEvent, country=self.player.country,
								type=self.type, area=self.area.board_area)
		super(Unit, self).delete()
	
	def __unicode__(self):
		return _("%(type)s in %(area)s") % {'type': self.get_type_display(), 'area': self.area}

	def describe_with_cost(self):
		return _("%(type)s in %(area)s (%(cost)s ducats)") % {'type': self.get_type_display(),
														'area': self.area,
														'cost': self.cost,}
    
	def get_possible_retreats(self):
		""" Returns a queryset of GameAreas the unit can retreat to. (Rule VIII.B.6) """
		if not self.must_retreat: # Should not be called if not retreating
		    return GameArea.objects.none()

		# Potential destinations: adjacent areas
		q = Q(game=self.player.game) & Q(board_area__borders=self.area.board_area)

		# a. Adjacency and unit type restrictions
		if self.type == 'A':
			q &= ~Q(board_area__is_sea=True) & ~Q(board_area__code='VEN') # No seas, no Venice
		elif self.type == 'F':
			# Must be sea or coast, and fleet-adjacent
			q &= (Q(board_area__is_sea=True) | Q(board_area__is_coast=True))
			# Filter for fleet adjacency later, as it depends on specific pairs

		# Must be unoccupied by another A/F unit (Garrisons don't block retreat)
		q &= ~Q(unit__type__in=['A', 'F'])

		# c.1: Cannot retreat into a standoff area
		q &= Q(standoff=False)

		# c.2: Cannot retreat into the area the attack came from
		q &= ~Q(board_area__code=self.must_retreat)

		possible_areas = GameArea.objects.filter(q).distinct()

		# Filter fleet retreats for true adjacency
		if self.type == 'F':
		    fleet_retreats = []
		    for area in possible_areas:
		        if self.area.board_area.is_adjacent(area.board_area, fleet=True):
		            fleet_retreats.append(area.id)
		    possible_areas = GameArea.objects.filter(id__in=fleet_retreats)

		# d. Option to convert to Garrison if possible and no other retreat exists
		can_convert_to_garrison = False
		if self.area.board_area.is_fortified and self.area.accepts_type('G'):
		    # Check if city is empty (no garrison)
		    if not Unit.objects.filter(area=self.area, type='G').exists():
		        # Check if rebellion blocks it
		        rebellion = self.area.has_rebellion(self.player, same=True) # Check for any rebellion
		        if not rebellion or not rebellion.garrisoned:
		            can_convert_to_garrison = True

		# If no other retreats available, add current area (for conversion)
		if not possible_areas.exists() and can_convert_to_garrison:
		    possible_areas = GameArea.objects.filter(id=self.area.id)
		# If other retreats exist, still offer conversion as an option
		elif can_convert_to_garrison:
		    possible_areas = possible_areas | GameArea.objects.filter(id=self.area.id)


		return possible_areas

	def invade_area(self, ga):
		if signals:
			signals.unit_moved.send(sender=self, destination=ga)
		else:
			self.player.game.log_event(MovementEvent, type=self.type,
										origin=self.area.board_area,
										destination=ga.board_area)
		self.area = ga
		self.must_retreat = ''
		self.save()
		self.check_rebellion()

	def retreat(self, destination):
		""" Executes the retreat, potentially converting to Garrison. """
		if self.area == destination: # Retreating into own city/fortress
			# Convert to Garrison (Rule VIII.B.6.d/f)
			if signals: signals.unit_converted.send(sender=self, before=self.type, after='G', context="retreat")
			self.type = 'G'
			self.siege_stage = 0 # Cannot be besieging if garrison
			self.besieging = False
			self.must_retreat = ''
			self.save()
		else: # Retreating to adjacent area
			if signals: signals.unit_retreated.send(sender=self, destination=destination)
			origin_code = self.area.board_area.code # Store before changing area
			self.area = destination
			self.must_retreat = ''
			self.save()
			self.check_rebellion() # Liberate rebellion if applicable

	def convert(self, new_type):
		""" Executes a conversion order. """
		# Rule VII.B.7.h: Besieged Garrison may not convert.
		if self.type == 'G' and Unit.objects.filter(area=self.area, besieging=True).exists():
		     # Conversion fails, unit holds (implicitly by not changing)
		     if logging: logging.info("Conversion failed: %s is besieged" % self)
		     return

		if signals: signals.unit_converted.send(sender=self, before=self.type, after=new_type)
		old_type = self.type
		self.type = new_type
		self.must_retreat = '' # Conversion prevents retreat? Rule VIII.B.6.f seems to imply conversion happens *then* retreat if needed. Let's assume conversion takes precedence.
		self.siege_stage = 0 # Reset siege status on conversion
		self.besieging = False
		self.save()
		# If converting *out* of Garrison, check for liberating rebellion
		if old_type == 'G' and new_type != 'G':
			self.check_rebellion()

	def check_rebellion(self):
		## if there is a rebellion against other player, put it down
		reb = self.area.has_rebellion(self.player, same=False)
		if reb:
			reb.delete()

	def delete_order(self):
		order = self.get_order()
		if order:
			order.delete()
		return True

	def change_player(self, player):
		assert isinstance(player, Player)
		self.player = player
		self.save()
		self.check_rebellion()
		if signals:
			signals.unit_changed_country.send(sender=self)

	def to_autonomous(self):
		assert self.type == 'G'
		## find the autonomous player
		try:
			aplayer = Player.objects.get(game=self.player.game, user__isnull=True)
		except ObjectDoesNotExist:
			return
		self.player = aplayer
		self.paid = True
		self.save()
		if signals:
			signals.unit_to_autonomous.send(sender=self)

class Order(models.Model):
	""" This class defines an order from a player to a unit. The order will not be
	effective unless it is confirmed.
	"""
	unit = models.ForeignKey(Unit)
	code = models.CharField(max_length=1, choices=ORDER_CODES)
	destination = models.ForeignKey(GameArea, blank=True, null=True) # For Advance, Support Advance
	type = models.CharField(max_length=1, blank=True, null=True, choices=UNIT_TYPES) # For Conversion, Support Conversion
	subunit = models.ForeignKey(Unit, related_name='affecting_orders', blank=True, null=True) # For Support, Convoy
	subcode = models.CharField(max_length=1, choices=ORDER_SUBCODES, blank=True, null=True) # For Support
	subdestination = models.ForeignKey(GameArea, related_name='affecting_orders', blank=True, null=True) # For Support Advance, Convoy
	subtype = models.CharField(max_length=1, blank=True, null=True, choices=UNIT_TYPES) # For Support Conversion
	confirmed = models.BooleanField(default=False)
	player = models.ForeignKey(Player, null=True) # Tracks who issued the order (can differ from unit.player if bought)

	class Meta:
		unique_together = (('unit', 'player'),) # Ensure one order per unit per player

	def as_dict(self):
		result = {
			'id': self.pk,
			'unit': unicode(self.unit),
			'code': self.get_code_display(),
			'destination': '',
			'type': '',
			'subunit': '',
			'subcode': '',
			'subdestination': '',
			'subtype': ''
		}
		if isinstance(self.destination, GameArea):
			result.update({'destination': unicode(self.destination)})
		if not self.type == None:
			result.update({'type': self.get_type_display()})
		if isinstance(self.subunit, Unit):
			result.update({'subunit': unicode(self.subunit)})
			if not self.subcode == None:
				result.update({'subcode': self.get_subcode_display()})
			if isinstance(self.subdestination, GameArea):
				result.update({'subdestination': unicode(self.subdestination)})
			if not self.subtype == None:
				result.update({'subtype': self.get_subtype_display()})

		return result
	
	def explain(self):
		""" Returns a human readable order.	"""

		if self.code == 'H':
			msg = _("%(unit)s holds its position.") % {'unit': self.unit,}
		elif self.code == '-':
			msg = _("%(unit)s tries to go to %(area)s.") % {
							'unit': self.unit,
							'area': self.destination
							}
		elif self.code == 'B':
			msg = _("%(unit)s besieges the city.") % {'unit': self.unit}
		elif self.code == '=':
			msg = _("%(unit)s tries to convert into %(type)s.") % {
							'unit': self.unit,
							'type': self.get_type_display()
							}
		elif self.code == 'C':
			msg = _("%(unit)s must convoy %(subunit)s to %(area)s.") % {
							'unit': self.unit,
							'subunit': self.subunit,
							'area': self.subdestination
							}
		elif self.code == 'S':
			if self.subcode == 'H':
				msg=_("%(unit)s supports %(subunit)s to hold its position.") % {
							'unit': self.unit,
							'subunit': self.subunit
							}
			elif self.subcode == '-':
				msg = _("%(unit)s supports %(subunit)s to go to %(area)s.") % {
							'unit': self.unit,
							'subunit': self.subunit,
							'area': self.subdestination
							}
			elif self.subcode == '=':
				msg = _("%(unit)s supports %(subunit)s to convert into %(type)s.") % {
							'unit': self.unit,
							'subunit': self.subunit,
							'type': self.get_subtype_display()
							}
		return msg
	
	def confirm(self):
		self.confirmed = True
		self.save()
	
	def format_suborder(self):
		""" Returns a string with the abbreviated code (as in Machiavelli) of
		the suborder.
		"""

		if not self.subunit:
			return ''
		f = "%s %s" % (self.subunit.type, self.subunit.area.board_area.code)
		f += " %s" % self.subcode
		if self.subcode == None and self.subdestination != None:
			f += "- %s" % self.subdestination.board_area.code
		elif self.subcode == '-':
			f += " %s" % self.subdestination.board_area.code
		elif self.subcode == '=':
			f += " %s" % self.subtype
		return f

	def format(self):
		""" Returns a string with the abreviated code (as in Machiavelli) of
		the order.
		"""

		f = "%s %s" % (self.unit.type, self.unit.area.board_area.code)
		f += " %s" % self.code
		if self.code == '-':
			f += " %s" % self.destination.board_area.code
		elif self.code == '=':
			f += " %s" % self.type
		elif self.code == 'S' or self.code == 'C':
			f += " %s" % self.format_suborder()
		return f

	def find_convoy_line(self):
		""" Returns True if there is a continuous line of convoy orders from 
		the origin to the destination of the order.
		"""

		origins = [self.unit.area,]
		destination = self.destination
		## get all areas convoying this order AND the destination
		convoy_areas = GameArea.objects.filter(
						## in this game
						(Q(game=self.unit.player.game) &
						## being sea areas
						Q(board_area__is_sea=True) &
						## with convoy orders
						Q(unit__order__code__exact='C') &
						## convoying this unit
						Q(unit__order__subunit=self.unit) &
						## convoying to this destination
						Q(unit__order__subdestination=self.destination)) |
						## OR being the destination
						Q(id=self.destination.id))
		if len(convoy_areas) <= 1:
			return False
		while 1:
			new_origins = []
			for o in origins:
				borders = GameArea.objects.filter(game=self.unit.player.game,
												board_area__borders=o.board_area)
				for b in borders:
					if b == destination:
						return True
					if b in convoy_areas:
						new_origins.append(b)
			if len(new_origins) == 0:
				return False
			origins = new_origins	
	
	def get_enemies(self):
		""" Returns a Queryset with all the units trying to oppose an advance or
		conversion order.
		"""

		if self.code == '-':
			enemies = Unit.objects.filter(Q(player__game=self.unit.player.game),
										## trying to go to the same area
										Q(order__destination=self.destination) |
										## trying to exchange areas
										(Q(area=self.destination) &
										Q(order__destination=self.unit.area)) |
										## trying to convert in the same area
										(Q(type__exact='G') &
										Q(area=self.destination) &
										Q(order__code__exact='=')) |
										## trying to stay in the area
										(Q(type__in=['A','F']) &
										Q(area=self.destination) &
										(Q(order__isnull=True) |
										Q(order__code__in=['B','H','S','C'])))
										).exclude(id=self.unit.id)
		elif self.code == '=':
			enemies = Unit.objects.filter(Q(player__game=self.unit.player.game),
										## trying to go to the same area
										Q(order__destination=self.unit.area) |
										## trying to stay in the area
										(Q(type__in=['A','F']) & 
										Q(area=self.unit.area) &
										(Q(order__isnull=True) |
										Q(order__code__in=['B','H','S','C','='])
										))).exclude(id=self.unit.id)
			
		else:
			enemies = Unit.objects.none()
		return enemies
	
	def get_rivals(self):
		""" Returns a Queryset with all the units trying to enter the same
		province as the unit that gave this order.
		"""

		if self.code == '-':
			rivals = Unit.objects.filter(Q(player__game=self.unit.player.game),
										## trying to go to the same area
										Q(order__destination=self.destination) |
										## trying to convert in the same area
										(Q(type__exact='G') &
										Q(area=self.destination) &
										Q(order__code__exact='='))
										).exclude(id=self.unit.id)
		elif self.code == '=':
			rivals = Unit.objects.filter(Q(player__game=self.unit.player.game),
										## trying to go to the same area
										Q(order__destination=self.unit.area)
										).exclude(id=self.unit.id)
			
		else:
			rivals = Unit.objects.none()
		return rivals
	
	def get_defender(self):
		""" Returns a Unit trying to stay in the destination area of this order, or
		None.
		"""

		try:
			if self.code == '-':
				defender = Unit.objects.get(Q(player__game=self.unit.player.game),
										## trying to exchange areas
										(Q(area=self.destination) &
										Q(order__destination=self.unit.area)) |
										## trying to stay in the area
										(Q(type__in=['A','F']) &
										Q(area=self.destination) &
										(Q(order__isnull=True) |
										Q(order__code__in=['B','H','S','C'])))
										)
			elif self.code == '=':
				defender = Unit.objects.get(Q(player__game=self.unit.player.game),
										## trying to stay in the area
										(Q(type__in=['A','F']) & 
										Q(area=self.unit.area) &
										(Q(order__isnull=True) |
										Q(order__code__in=['B','H','S','C','='])
										)))
			else:
				defender = Unit.objects.none()
		except ObjectDoesNotExist:
			defender = Unit.objects.none()
		return defender
	
	def get_attacked_area(self):
		""" Returns the game area being attacked by this order. """

		if self.code == '-':
			return self.destination
		elif self.code == '=':
			return self.unit.area
		else:
			return GameArea.objects.none()
	
	def is_possible(self):
		""" Checks if an Order is possible based on rules VII.B and VIII.C.2.a.3. """
		unit = self.unit
		area = unit.area
		board_area = area.board_area

		if self.code == 'H': # Hold
			return True
		elif self.code == '0': # Disband
		    return True
		elif self.code == '-': # Advance (Rule VII.B.1)
			if unit.type not in ['A', 'F']: return False
			if not self.destination: return False
			# Check adjacency based on type
			if not board_area.is_adjacent(self.destination.board_area, fleet=(unit.type == 'F')):
			    # If not adjacent, check for convoy possibility (Rule VII.B.6)
			    if unit.type == 'A' and board_area.is_coast and self.destination.board_area.is_coast:
			        # Convoy line check happens during resolution, assume possible here if coastal start/end
			        return True # Potential convoy
			    else:
			        return False # Not adjacent and not potential convoy
			# Check type restrictions for destination
			if not self.destination.board_area.accepts_type(unit.type):
			    return False
			# Rule VII.B.4: Cannot advance if currently besieging (must Lift Siege first)
			if unit.siege_stage > 0:
			    return False
			return True
		elif self.code == 'B': # Besiege (Rule VII.B.2)
			if unit.type not in ['A', 'F']: return False
			if not board_area.is_fortified: return False
			# Fleet can only besiege ports
			if unit.type == 'F' and not board_area.has_port: return False
			# Must target an enemy garrison or garrisoned rebellion
			target_garrison = Unit.objects.filter(area=area, type='G').exclude(player=unit.player).exists()
			target_rebellion = area.has_rebellion(unit.player, same=False) and area.has_rebellion(unit.player, same=False).garrisoned
			if not target_garrison and not target_rebellion: return False
			# Cannot start siege if already besieging max stage
			if unit.siege_stage == 2: return False # Already at final stage
			return True
		elif self.code == 'L': # Lift Siege (Rule VII.B.4)
		    if unit.type not in ['A', 'F']: return False
		    # Must actually be besieging to lift it
		    if unit.siege_stage == 0: return False
		    return True
		elif self.code == '=': # Conversion (Rule VII.B.7)
			if not self.type: return False
			if unit.type == self.type: return False # Cannot convert to same type
			if not board_area.is_fortified: return False # Must be in fortified city/fortress
			# Check type restrictions
			if unit.type == 'G': # Garrison converting out
				if self.type == 'F' and not board_area.has_port: return False # Need port for Fleet
				if self.type not in ['A', 'F']: return False # Can only become A or F
				# Rule VII.B.7.h: Besieged garrison cannot convert
				if Unit.objects.filter(area=area, besieging=True).exclude(id=unit.id).exists(): return False
			else: # Army/Fleet converting in
				if self.type != 'G': return False # Can only become Garrison
				if unit.type == 'F' and not board_area.has_port: return False # Fleet needs port
				# Cannot convert if city already occupied by a Garrison
				if Unit.objects.filter(area=area, type='G').exists(): return False
			return True
		elif self.code == 'C': # Convoy/Transport (Rule VII.B.6)
			if unit.type != 'F': return False # Only Fleets convoy
			if not self.subunit or self.subunit.type != 'A': return False # Must convoy an Army
			if not self.subdestination: return False
			# Fleet must be in sea (or Venice Lagoon)
			if not board_area.is_sea and board_area.code != 'VEN': return False
			# Army must be in coastal province adjacent to the fleet's sea
			army_area = self.subunit.area.board_area
			if not army_area.is_coast: return False
			if not army_area.is_adjacent(board_area, fleet=True): return False # Check if army area borders fleet sea
			# Destination must be a province the Fleet could move to (coastal)
			if not self.subdestination.board_area.is_coast: return False
			if not board_area.is_adjacent(self.subdestination.board_area, fleet=True): # Can fleet reach destination sea border?
			    # This doesn't check intermediate convoy steps, only direct reach
			    # Full check requires find_convoy_line logic
			    pass # Assume possible for now, resolution handles full path
			return True
		elif self.code == 'S': # Support (Rule VII.B.5)
			if not self.subunit: return False
			# Determine target area of support
			support_target_area = None
			if self.subcode == 'H': support_target_area = self.subunit.area
			elif self.subcode == '-': support_target_area = self.subdestination
			elif self.subcode == '=': support_target_area = self.subunit.area # Support conversion happens in unit's area
			else: return False # Invalid subcode

			if not support_target_area: return False

			# Check if supporting unit can reach the target area
			if unit.type == 'G': # Garrison support
				if support_target_area != area: return False # Can only support own province (Rule VII.B.5.c)
			else: # Army/Fleet support
				if not board_area.is_adjacent(support_target_area.board_area, fleet=(unit.type == 'F')): return False
				# Check unit type restrictions for target area
				if not support_target_area.board_area.accepts_type(unit.type): return False

			# Check validity of supported order (e.g., cannot support invalid move)
			# This might be too complex for is_possible, better handled in resolution?
			# Basic check: cannot support conversion from Garrison if besieged
			if self.subcode == '=' and self.subunit.type == 'G':
			    if Unit.objects.filter(area=self.subunit.area, besieging=True).exclude(id=self.subunit.id).exists(): return False

			return True

		return False # Default false for unknown codes

	def __unicode__(self):
		return self.format()

class RetreatOrder(models.Model):
	""" Defines the area where the unit must try to retreat. If ``area`` is
	blank, the unit will be disbanded.
	"""

	unit = models.ForeignKey(Unit)
	area = models.ForeignKey(GameArea, null=True, blank=True)

	def __unicode__(self):
		return "%s" % self.unit

class ControlToken(models.Model):
	""" Defines the coordinates of the control token for a board area. """

	area = models.OneToOneField(Area)
	x = models.PositiveIntegerField()
	y = models.PositiveIntegerField()

	def __unicode__(self):
		return "%s, %s" % (self.x, self.y)


class GToken(models.Model):
	""" Defines the coordinates of the Garrison token in a board area. """

	area = models.OneToOneField(Area)
	x = models.PositiveIntegerField()
	y = models.PositiveIntegerField()

	def __unicode__(self):
		return "%s, %s" % (self.x, self.y)


class AFToken(models.Model):
	""" Defines the coordinates of the Army and Fleet tokens in a board area."""

	area = models.OneToOneField(Area)
	x = models.PositiveIntegerField()
	y = models.PositiveIntegerField()

	def __unicode__(self):
		return "%s, %s" % (self.x, self.y)

class TurnLog(models.Model):
	""" A TurnLog is text describing the processing of the method
	``Game.process_orders()``.
	"""

	game = models.ForeignKey(Game)
	year = models.PositiveIntegerField()
	season = models.PositiveIntegerField(choices=SEASONS)
	phase = models.PositiveIntegerField(choices=GAME_PHASES)
	timestamp = models.DateTimeField(auto_now_add=True)
	log = models.TextField()

	class Meta:
		ordering = ['-timestamp',]

	def __unicode__(self):
		return self.log

class Configuration(models.Model):
	""" Defines the configuration options for each game. 
	
	At the moment, only some of them are actually implemented.
	"""

	game = models.OneToOneField(Game, verbose_name=_('game'), editable=False)
	finances = models.BooleanField(_('finances'), default=False)
	assassinations = models.BooleanField(_('assassinations'), default=False,
					help_text=_('will enable Finances'))
	bribes = models.BooleanField(_('bribes'), default=False,
					help_text=_('will enable Finances'))
	excommunication = models.BooleanField(_('excommunication'), default=False)
	#disasters = models.BooleanField(_('natural disasters'), default=False)
	special_units = models.BooleanField(_('special units'), default=False,
					help_text=_('will enable Finances'))
	strategic = models.BooleanField(_('strategic movement'), default=False)
	lenders = models.BooleanField(_('money lenders'), default=False,
					help_text=_('will enable Finances'))
	unbalanced_loans = models.BooleanField(_('unbalanced loans'), default=False,
		help_text=_('the credit for all players will be 25d'))
	conquering = models.BooleanField(_('conquering'), default=False)
	famine = models.BooleanField(_('famine'), default=False)
	plague = models.BooleanField(_('plague'), default=False)
	storms = models.BooleanField(_('storms'), default=False)
	gossip = models.BooleanField(_('gossip'), default=False)

	def __unicode__(self):
		return unicode(self.game)

	def get_enabled_rules(self):
		rules = []
		for f in self._meta.fields:
			if isinstance(f, models.BooleanField):
				if f.value_from_object(self):
					rules.append(unicode(f.verbose_name))
		return rules
	
def create_configuration(sender, instance, created, **kwargs):
    if isinstance(instance, Game) and created:
		config = Configuration(game=instance)
		config.save()

models.signals.post_save.connect(create_configuration, sender=Game)

###
### EXPENSES
###

EXPENSE_TYPES = (
	(0, _("Famine relief")),
	(1, _("Pacify rebellion")),
	(2, _("Conquered province to rebel")),
	(3, _("Home province to rebel")),
	(4, _("Counter bribe")),
	(5, _("Disband autonomous garrison")),
	(6, _("Buy autonomous garrison")),
	(7, _("Convert garrison unit")),
	(8, _("Disband enemy unit")),
	(9, _("Buy enemy unit")),
)

EXPENSE_COST = {
	0: 3,
	1: 12,
	2: 9,
	3: 15,
	4: 3,
	5: 6,
	6: 9,
	7: 9,
	8: 12,
	9: 18,
}

# Ensure Expense costs match rules, especially doubling for major cities
def get_expense_cost(type, unit=None):
	""" Calculates the minimum cost for an expense, considering unit loyalty and major cities. """
	if type not in EXPENSE_COST:
		raise ValueError("Invalid expense type")

	base_cost = EXPENSE_COST[type]
	multiplier = 1
	loyalty_factor = 1

	if type in (5, 6, 7, 8, 9): # Bribes targeting a unit
		if not isinstance(unit, Unit):
			raise ValueError("Unit required for bribe cost calculation")
		loyalty_factor = unit.loyalty # Optional Rule IV / Advanced VI.C.4.g

		# Rule VI.C.4.g.3: Double cost for Garrisons in major cities
		if unit.type == 'G':
		    area_board = unit.area.board_area
		    # Check if the area itself has major city income OR if it's linked via CityIncome model
		    is_major = (area_board.major_city_income is not None and area_board.major_city_income > 1) or \
		               CityIncome.objects.filter(city=area_board, scenario=unit.player.game.scenario).exists()
		    if is_major:
		        multiplier = 2

	# Counter-bribe cost is minimum 3, but can be increased in multiples of 3
	if type == 4:
	    # The form should handle setting the actual amount, this just gives base
	    return base_cost # Minimum is 3

	return base_cost * multiplier * loyalty_factor

class Expense(models.Model):
	""" A player may expend unit to affect some units or areas in the game. """
	player = models.ForeignKey(Player)
	ducats = models.PositiveIntegerField(default=0)
	type = models.PositiveIntegerField(choices=EXPENSE_TYPES)
	area = models.ForeignKey(GameArea, null=True, blank=True)
	unit = models.ForeignKey(Unit, null=True, blank=True)
	confirmed = models.BooleanField(default=False)

	def save(self, *args, **kwargs):
		## expenses that need an area
		if self.type in (0, 1, 2, 3):
			assert isinstance(self.area, GameArea), "Expense needs a GameArea"
		## expenses that need a unit
		elif self.type in (4, 5, 6, 7, 8, 9):
			assert isinstance(self.unit, Unit), "Expense needs a Unit"
		else:
			raise ValueError, "Wrong expense type %s" % self.type
		## if no errors raised, save the expense
		super(Expense, self).save(*args, **kwargs)
		if logging:
			msg = "New expense in game %s: %s" % (self.player.game.id,
													self)
			logging.info(msg)
	
	def __unicode__(self):
		data = {
			'country': self.player.country,
			'area': self.area,
			'unit': self.unit,
		}
		messages = {
			0: _("%(country)s reliefs famine in %(area)s"),
			1: _("%(country)s pacifies rebellion in %(area)s"),
			2: _("%(country)s promotes a rebellion in %(area)s"),
			3: _("%(country)s promotes a rebellion in %(area)s"),
			4: _("%(country)s tries to counter bribe on %(unit)s"),
			5: _("%(country)s tries to disband %(unit)s"),
			6: _("%(country)s tries to buy %(unit)s"),
			7: _("%(country)s tries to turn %(unit)s into an autonomous garrison"),
			8: _("%(country)s tries to disband %(unit)s"),
			9: _("%(country)s tries to buy %(unit)s"),
		}

		if self.type in messages.keys():
			return messages[self.type] % data
		else:
			return "Unknown expense"
	
	def is_bribe(self):
		return self.type in (5, 6, 7, 8, 9)

	def is_allowed(self):
		""" Return true if it's not a bribe or the unit is in a valid area as
		stated in the rules. """
		if self.type in (0, 1, 2, 3, 4):
			return True
		elif self.is_bribe():
			## self.unit must be adjacent to a unit or area of self.player
			## then, find the borders of self.unit
			adjacent = self.unit.area.get_adjacent_areas()

	def undo(self):
		""" Deletes the expense and returns the money to the player """
		if self.type in (6, 9):
			## trying to buy a unit
			try:
				order = Order.objects.get(player=self.player, unit=self.unit)
			except ObjectDoesNotExist:
				pass
			else:
				order.delete()
		self.player.ducats += self.ducats
		self.player.save()
		if logging:
			msg = "Deleting expense in game %s: %s." % (self.player.game.id,
													self)
			logging.info(msg)
		self.delete()

class Rebellion(models.Model):
	"""
	A Rebellion may be placed in a GameArea if finances rules are applied.
	Rebellion.player is the player who controlled the GameArea when the
	Rebellion was placed. Rebellion.garrisoned is True if the Rebellion is
	in a garrisoned city.
	"""
	area = models.ForeignKey(GameArea, unique=True)
	player = models.ForeignKey(Player)
	garrisoned = models.BooleanField(default=False)

	def __unicode__(self):
		return "Rebellion in %(area)s against %(player)s" % {'area': self.area,
														'player': self.player}
	
	def save(self, *args, **kwargs):
		## area must be controlled by a player, who is assigned to the rebellion
		try:
			self.player = self.area.player
		except:
			return False
		## a rebellion cannot be placed in a sea area
		if self.area.board_area.is_sea:
			return False
		## check if the rebellion is to be garrisoned
		if self.area.board_area.is_fortified:
			try:
				Unit.objects.get(area=self.area, type='G')
			except ObjectDoesNotExist:
				self.garrisoned = True
			else:
				## there is a garrison in the city
				if self.area.board_area.code == 'VEN':
					## there cannot be a rebellion in Venice sea area
					return False
		super(Rebellion, self).save(*args, **kwargs)
		if signals:
			signals.rebellion_started.send(sender=self.area)
	
class Loan(models.Model):
	""" A Loan describes a quantity of money that a player borrows from the bank, with a term """
	player = models.OneToOneField(Player)
	debt = models.PositiveIntegerField(default=0)
	season = models.PositiveIntegerField(choices=SEASONS)
	year = models.PositiveIntegerField(default=0)

	def __unicode__(self):
		return "%(player)s ows %(debt)s ducats" % {'player': self.player, 'debt': self.debt, }

class Assassin(models.Model):
	""" An Assassin represents a counter that a Player owns, to murder the leader of a country """
	owner = models.ForeignKey(Player)
	target = models.ForeignKey(Country)

	def __unicode__(self):
		return "%(owner)s may assassinate %(target)s" % {'owner': self.owner, 'target': self.target, }

class Assassination(models.Model):
	""" An Assassination describes an attempt made by a Player to murder the leader of another
	Country, spending some Ducats """
	killer = models.ForeignKey(Player, related_name="assassination_attempts")
	target = models.ForeignKey(Player, related_name="assassination_targets")
	ducats = models.PositiveIntegerField(default=0)

	def __unicode__(self):
		return "%(killer)s tries to kill %(target)s" % {'killer': self.killer, 'target': self.target, }

	def explain(self):
		return _("%(ducats)sd to kill the leader of %(country)s.") % {'ducats': self.ducats,
																	'country': self.target.country}

class Whisper(models.Model):
	""" A whisper is an _anonymous_ message that is shown in the game screen. """
	created_at = models.DateTimeField(auto_now_add=True)
	user = models.ForeignKey(User)
	as_admin = models.BooleanField(default=False)
	game = models.ForeignKey(Game)
	text = models.CharField(max_length=140,
		help_text=_("limit of 140 characters"))
	order = models.PositiveIntegerField(editable=False, default=0)

	class Meta:
		ordering = ["-created_at" ,]
		unique_together = (("game", "order"),)

	def __unicode__(self):
		return self.text

	def as_li(self):
		if self.as_admin:
			li = u"<li class=\"admin\">"
		else:
			li = u"<li>"
		html = u"%(li)s<strong>#%(order)s</strong>&nbsp;&nbsp;%(text)s<span class=\"date\">%(date)s</span> </li>" % {
								'order': self.order,
								'li': li,
								'date': timesince(self.created_at),
								'text': force_escape(self.text), }
		return html

def whisper_order(sender, instance, **kw):
	""" Checks if a whisper has already an 'order' value and, if not, calculate
	and assign one """
	if instance.order is None or instance.order == 0:
		whispers = Whisper.objects.filter(game=instance.game).order_by("-order")
		try:
			last = whispers[0].order
			instance.order = last + 1
		except IndexError:
			instance.order = 1

models.signals.pre_save.connect(whisper_order, sender=Whisper)

class Invitation(models.Model):
	""" A private game accepts only users that have been invited by the creator
	of the game. """
	game = models.ForeignKey(Game)
	user = models.ForeignKey(User)
	message = models.TextField(default="", blank=True)

	class Meta:
		unique_together = (('game', 'user'),)

	def __unicode__(self):
		return "%s" % self.user

def notify_new_invitation(sender, instance, created, **kw):
	if notification and isinstance(instance, Invitation) and created:
		user = [instance.user,]
		extra_context = {'game': instance.game,
						'invitation': instance,}
		notification.send(user, "new_invitation", extra_context , on_site=True)

models.signals.post_save.connect(notify_new_invitation, sender=Invitation)

