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
from collections import defaultdict # Add defaultdict
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
VICTORY_TYPES = (
    ('basic', _('Basic (12 Cities, 6 Conquered)')),
    ('advanced_18', _('Advanced (18 Cities, 1 Conquered Home - <=4 Players)')),
    ('advanced_15', _('Advanced (15 Cities, 1 Conquered Home - >=5 Players)')),
    ('ultimate', _('Ultimate (23 Cities, 2 Conquered Homes)')),
    # ('custom', _('Custom (Set Manually)')), # Optional: Add if you implement custom logic
)
# --- Phase Definitions ---

# --- Phase Definitions ---
# Basic Game Phases (Simplified - Use these numbers for core logic)
PHINACTIVE = 0
PHREINFORCE = 1 # Spring: Basic Adjust / Adv Income & Adjust
PHORDERS = 2    # Spring/Summer/Fall: Order Writing (+ Adv Expense Writing)
PHRETREATS = 3  # Spring/Summer/Fall: Order Execution & Retreats

# Advanced/Optional Phases (Can be conceptual or trigger specific logic within core phases)
# These numbers are illustrative and might not represent distinct states in the 'phase' field
# unless you implement a more complex state machine.
_PH_ADV_INCOME = 10          # Conceptual: Part of PHREINFORCE in Spring
_PH_NEGOTIATION = 11     # Conceptual: Happens before PHORDERS each season
_PH_ADV_EXPENSES = 12        # Conceptual: Happens after PHORDERS, before PHRETREATS if finances on
_PH_ADV_ASSASSINATION = 13   # Conceptual: Happens after _PH_ADV_EXPENSES, before PHRETREATS if finances on
_PH_OPT_FAMINE = 14          # Conceptual: Happens before PHREINFORCE in Spring if optional rule on
_PH_OPT_PLAGUE = 15          # Conceptual: Happens after _PH_OPT_FAMINE in Spring if optional rule on
_PH_OPT_STORMS = 16          # Conceptual: Happens after _PH_NEGOTIATION in Summer if optional rule on
_PH_OPT_LENDERS = 17         # Conceptual: Happens after _PH_NEGOTIATION if optional rule on

# Combined Sequence (Simplified for state machine, logic handled in processing)
# We'll use the core phases (1, 2, 3) and trigger specific logic based on season/config.
GAME_PHASES = (
    (PHINACTIVE, _('Inactive game')),
    # Spring
    (PHREINFORCE, _('Spring: Adjust Units & Income')), # Basic V / Advanced V.A/B / Optional III.A/B
    (PHORDERS, _('Spring: Write Orders & Expenses')), # Basic VII / Advanced VI.A / Optional X.A
    (PHRETREATS, _('Spring: Execute Orders & Retreats')), # Basic VIII / Advanced IV.D/E/F
    # Summer
    (PHORDERS, _('Summer: Write Orders & Expenses')), # Basic VII / Advanced VI.A / Optional III.C / Optional X.A
    (PHRETREATS, _('Summer: Execute Orders & Retreats')), # Basic VIII / Advanced IV.D/E/F
    # Fall
    (PHORDERS, _('Fall: Write Orders & Expenses')), # Basic VII / Advanced VI.A / Optional X.A
    (PHRETREATS, _('Fall: Execute Orders & Retreats')), # Basic VIII / Advanced IV.D/E/F
)

ORDER_CODES = (('H', _('Hold')),
               ('B', _('Besiege')),
               ('-', _('Advance')),
               ('=', _('Conversion')),
               ('C', _('Convoy/Transport')), # Renamed slightly for clarity
               ('S', _('Support')),
               ('L', _('Lift Siege')), # Added L (Rule VII.B.4)
               ('0', _('Disband')),     # Added 0 (Rule VII.B.7.f)
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


# Helper function (can be placed outside class or as a static method if preferred)
def is_strait_blocked(area1_code, area2_code, game, convoying_player):
    """Checks if movement between two areas is blocked by a strait rule."""
    # Rule VII.D.2: Messina Strait (GON <-> IS blocked by F MES)
    if {area1_code, area2_code} == {'GON', 'IS'}:
        try:
            messina_ga = GameArea.objects.get(game=game, board_area__code='MES')
            # Check if an *enemy* fleet is in Messina
            if messina_ga.unit_set.filter(type='F').exclude(player=convoying_player).exists():
                if logging: logging.debug("Convoy path blocked: Messina Strait (%s<->%s) blocked by enemy fleet." % (area1_code, area2_code))
                return True
        except GameArea.DoesNotExist:
            pass # Messina area doesn't exist in this game/scenario

    # Rule VII.D.1: Piombino Strait (ETS <-> PISA blocked by F PIO)
    # Note: Rule says ETS<->PISA blocked by F PIO. ETS doesn't border PISA directly.
    # The rule likely means movement *through* ETS that would normally connect to PISA (e.g. from GOL)
    # is blocked if PIO has a fleet. This is complex to model in simple adjacency.
    # Let's interpret the rule as blocking direct sea movement adjacent to Piombino if PIO has a fleet.
    # Example: GOL <-> ETS might be affected if PIO has a fleet? This needs map clarification.
    # For now, let's implement the *literal* (though likely incorrect map-wise) ETS<->PISA block check.
    # A better implementation requires specific border analysis around Piombino.
    # if {area1_code, area2_code} == {'ETS', 'PISA'}: # Direct border doesn't exist
    # Let's check if Piombino itself contains an enemy fleet, which might affect adjacent sea moves.
    try:
        piombino_ga = GameArea.objects.get(game=game, board_area__code='PIO')
        if piombino_ga.unit_set.filter(type='F').exclude(player=convoying_player).exists():
             # If Piombino has an enemy fleet, which sea connections does it block?
             # Rule VII.D.1 says it controls straits between mainland and Elba, part of ETS.
             # It blocks hostile fleets moving Pisa <-> ETS. Let's assume it blocks convoy path GOL<->ETS.
             if {area1_code, area2_code} == {'GOL', 'ETS'}:
                  if logging: logging.debug("Convoy path blocked: Piombino Strait (%s<->%s) blocked by enemy fleet in PIO." % (area1_code, area2_code))
                  return True
    except GameArea.DoesNotExist:
         pass # Piombino area doesn't exist

    return False # Not blocked by known straits


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
    name = AutoTranslateField(max_length=30)
    code = models.CharField(max_length=5, unique=True)
    is_sea = models.BooleanField(default=False)
    is_coast = models.BooleanField(default=False)
    has_city = models.BooleanField(default=False)
    is_fortified = models.BooleanField(default=False) # Rule VII.B.1.c
    has_port = models.BooleanField(default=False) # Rule II.A / VII.B.1.f
    borders = models.ManyToManyField("self", editable=False, symmetrical=True) # Keep symmetrical=True for standard adjacency
    # Removed control_income/garrison_income, use province/city income rules
    # control_income = models.PositiveIntegerField(null=False, default=0) # REMOVED
    # garrison_income = models.PositiveIntegerField(null=False, default=0) # REMOVED
    major_city_income = models.PositiveIntegerField(null=True, blank=True, default=None, help_text="Income value if this is a major city (Rule V.B.1.c.2)") # Kept for Advanced
    # New field to list valid coast identifiers, comma-separated (e.g., "nc,sc", "ec,sc")
    coast_names = models.CharField(max_length=10, blank=True, null=True, help_text="Valid coast identifiers (e.g., nc,sc,ec)") # Rule VII.D.3, VII.D.4

    def get_coast_list(self):
        """Returns a list of valid coast identifiers for this area."""
        if self.coast_names:
            # Ensure consistent case (lowercase)
            return [c.strip().lower() for c in self.coast_names.split(',')]
        return []

    def has_multiple_coasts(self):
        """Checks if the area has more than one defined coast."""
        return bool(self.coast_names and ',' in self.coast_names)
    
    def is_adjacent(self, target_area, fleet=False, source_unit_coast=None, target_order_coast=None):
        """
        Checks adjacency between self and target_area.
        Considers unit type (fleet=True for fleets), coasts, and special rules.
        """
        # 1. Basic physical border check (most efficient first check)
        # Assumes self.borders correctly defines ALL physical adjacencies.
        if not self.borders.filter(pk=target_area.pk).exists():
            return False

        # 2. Army Adjacency (Non-Fleet)
        if not fleet:
            # Rule VII.B.1.d (Machiavelli): Armies cannot enter seas
            if target_area.is_sea: return False
            # Rule VII.D.6 (Machiavelli): Armies cannot enter Venice (province/city combo)
            if target_area.code == 'VEN': return False
            # Diplomacy Rule (p.8): Armies cannot enter water provinces. (Covered by is_sea check)
            # Otherwise, if they border physically, they are adjacent for armies.
            return True

        # 3. Fleet Adjacency
        # Normalize provided coasts
        source_unit_coast = source_unit_coast.lower() if source_unit_coast else None
        target_order_coast = target_order_coast.lower() if target_order_coast else None

        # Use the specific coast-aware check if needed
        if self.has_multiple_coasts() and source_unit_coast:
            # Check adjacency FROM a specific coast of SELF
            # Also ensure target is valid for a fleet (Sea or Coastal)
            if not target_area.is_sea and not target_area.is_coast: return False
            return self.is_coast_adjacent(source_unit_coast, target_area)
        elif target_area.has_multiple_coasts() and target_order_coast:
            # Check adjacency TO a specific coast of TARGET
            # Also ensure self is valid for a fleet (Sea or Coastal)
            if not self.is_sea and not self.is_coast: return False
            # This is equivalent to checking from the target's perspective
            return target_area.is_coast_adjacent(target_order_coast, self)
        else:
            # --- Standard Fleet Adjacency (No specific multi-coast involved in the check) ---
            source_is_sea = self.is_sea
            target_is_sea = target_area.is_sea
            source_is_coast = self.is_coast
            target_is_coast = target_area.is_coast

            # Rule VII.B.1.e (Machiavelli) / Diplomacy (p.4): Fleet movement possibilities
            valid_combination = False
            if source_is_sea and target_is_sea: valid_combination = True
            elif source_is_sea and target_is_coast: valid_combination = True
            elif source_is_coast and target_is_sea: valid_combination = True
            elif source_is_coast and target_is_coast: valid_combination = True # Assumes border implies coastal path

            if not valid_combination:
                return False

            # --- Specific Non-Adjacency / Strait Rules (Handled here or in pathfinding) ---
            # Rule VII.D.9 (Machiavelli): No movement ETS <-> Capua
            if (self.code == 'ETS' and target_area.code == 'CAP') or \
               (target_area.code == 'ETS' and self.code == 'CAP'):
                return False

            # Diplomacy Rule (p.8): BAL <-> SKA is NOT direct. Requires move to DEN/SWE first.
            # This rule affects pathfinding more than direct adjacency. DEN/SWE *are* adjacent to BAL/SKA.
            # We don't block the adjacency here, but pathfinding (like find_convoy_line) should enforce it.
            # if {self.code, target_area.code} == {'BAL', 'SKA'}: return False # Incorrect - they border DEN/SWE

            # Kiel/Constantinople (p.8): Act as single coast. Standard adjacency works.
            # Denmark/Sweden (p.8): Act as single coast. Standard adjacency works.

            # If physical border exists and type combination is valid, assume adjacent
            return True


    def is_coast_adjacent(self, coast_code, target_area):
        """
        Helper: Checks if a specific coast ('nc', 'sc', 'ec') of this multi-coast area
        is considered adjacent to the target_area for fleet movement/support,
        based on Machiavelli rules (VII.D.3/4) and Diplomacy rules (p.8).

        Args:
            coast_code (str): The coast identifier (e.g., 'nc', 'sc', 'ec') of 'self'.
            target_area (Area): The Area object being checked for adjacency.

        Returns:
            bool: True if adjacent via the specified coast, False otherwise.
        """
        # Ensure self is actually multi-coast and a valid coast was provided
        if not self.has_multiple_coasts() or not coast_code or coast_code not in self.get_coast_list():
            # Fall back to standard physical border check if not multi-coast or invalid coast given
            # logger.debug("Falling back to standard border check for {self.code} coast '{coast_code}' -> {target_area.code}")
            return self.borders.filter(pk=target_area.pk).exists()

        target_code = target_area.code

        # --- Rule VII.D.4 (Machiavelli): Provence (PRO) ---
        if self.code == 'PRO':
            if coast_code == 'nc':
                # North Coast borders Spain (SPA) and Gulf of Lions (GOL)
                allowed_codes = ['SPA', 'GOL']
                return target_code in allowed_codes
            elif coast_code == 'sc':
                # South Coast borders Gulf of Lions (GOL), Marseille (MAR), Piedmont (PIE)
                # Fleet cannot move to landlocked PIE.
                allowed_codes = ['GOL', 'MAR']
                return target_code in allowed_codes
            else: return False # Invalid coast for PRO

        # --- Rule VII.D.3 (Machiavelli): Croatia (CRO) ---
        elif self.code == 'CRO':
            if coast_code == 'nc':
                # North Coast borders Upper Adriatic (UA) and Carinthia (CAR)
                # Fleet cannot move to landlocked CAR.
                allowed_codes = ['UA']
                return target_code in allowed_codes
            elif coast_code == 'sc':
                # South Coast borders Dalmatia (DAL), Istria (IST), Bosnia (BOS)
                # Fleet cannot move to landlocked BOS. Fleet access to ADR is via DAL/IST.
                allowed_codes = ['DAL', 'IST']
                return target_code in allowed_codes
            else: return False # Invalid coast for CRO

        # --- Diplomacy Rule (p.8): Spain (SPA) ---
        elif self.code == 'SPA':
            if coast_code == 'nc':
                # North Coast borders Gascony (GAS), Portugal (POR), Mid-Atlantic Ocean (MAO)
                allowed_codes = ['GAS', 'POR', 'MAO']
                return target_code in allowed_codes
            elif coast_code == 'sc':
                # South Coast borders Portugal (POR), Marseilles (MAR), Gulf of Lyon (GOL), Western Med (WME), Mid-Atlantic Ocean (MAO)
                allowed_codes = ['POR', 'MAR', 'GOL', 'WME', 'MAO']
                return target_code in allowed_codes
            else: return False # Invalid coast for SPA

        # --- Diplomacy Rule (p.8): St. Petersburg (STP) ---
        elif self.code == 'STP':
            if coast_code == 'nc':
                # North Coast borders Norway (NWY), Barents Sea (BAR)
                allowed_codes = ['NWY', 'BAR']
                return target_code in allowed_codes
            elif coast_code == 'sc':
                # South Coast borders Finland (FIN), Livonia (LVN), Gulf of Bothnia (BOT), Baltic Sea (BAL)
                allowed_codes = ['FIN', 'LVN', 'BOT', 'BAL']
                return target_code in allowed_codes
            else: return False # Invalid coast for STP

        # --- Diplomacy Rule (p.8): Bulgaria (BUL) ---
        elif self.code == 'BUL':
            if coast_code == 'ec':
                # East Coast borders Constantinople (CON), Rumania (RUM), Black Sea (BLA)
                allowed_codes = ['CON', 'RUM', 'BLA']
                return target_code in allowed_codes
            elif coast_code == 'sc':
                # South Coast borders Constantinople (CON), Greece (GRE), Aegean Sea (AEG)
                allowed_codes = ['CON', 'GRE', 'AEG']
                return target_code in allowed_codes
            else: return False # Invalid coast for BUL

        # --- Fallback for Unhandled Multi-Coast Areas ---
        else:
            logger.warning("Adjacency check for unhandled multi-coast area '%s' coast '%s' to '%s'. Falling back to standard border check." % (self.code, coast_code, target_code))
            return self.borders.filter(pk=target_area.pk).exists()

    def accepts_type(self, type):
        """ Returns True if a given type of Unit can be in the Area. """
        # ... (accepts_type method - unchanged from previous version) ...
        assert type in ('A', 'F', 'G'), 'Wrong unit type'
        if type=='A':
            if self.is_sea or self.code=='VEN': return False
        elif type=='F':
            if not self.is_sea and not self.is_coast: return False
        else: # Garrison
            if not self.is_fortified: return False
        return True

    def __unicode__(self):
        # Use capfirst for better display
        from django.template.defaultfilters import capfirst
        return "{self.code} - {capfirst(self.name)}"

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
    # Store the *type* of victory condition chosen (e.g., 'basic', 'advanced_15', 'advanced_18', 'ultimate')
    victory_condition_type = models.CharField(max_length=15, default='basic') # Increased max_length
    # Store the actual number required for the chosen type
    cities_to_win = models.PositiveIntegerField(default=12, # Default to Basic Game
                help_text=_("cities that must be controlled to win a game"))
    fast = models.BooleanField(default=0)
    private = models.BooleanField(default=0,
                help_text=_("only invited users can join the game"))
    comment = models.TextField(max_length=255, blank=True, null=True,
                help_text=_("optional comment for joining users"))

    def save(self, *args, **kwargs):
        is_new = not self.pk
        if is_new:
            self.fast = self.time_limit in FAST_LIMITS
            # Set cities_to_win based on type if creating
            # Use the scenario's player count for initial determination
            num_players = self.scenario.get_slots() # Actual players joining

            if self.victory_condition_type == 'basic':          # Rule III.B
                self.cities_to_win = 12
            elif self.victory_condition_type == 'advanced_18':  # Rule II.B (Advanced)
                self.cities_to_win = 18
            elif self.victory_condition_type == 'advanced_15':  # Rule II.C (Advanced)
                self.cities_to_win = 15
            elif self.victory_condition_type == 'ultimate':     # Rule II.D (Advanced)
                self.cities_to_win = 23
            # else: allow custom value if type is not recognized? Or default?
            # Let's default to basic if type is invalid
            elif self.cities_to_win is None: # Ensure a value is set
                 self.cities_to_win = 12
                 self.victory_condition_type = 'basic'

            # Validate chosen advanced type against player count
            if self.victory_condition_type == 'advanced_18' and num_players >= 5:
                 # Auto-correct to advanced_15 if wrong type selected for player count
                 self.victory_condition_type = 'advanced_15'
                 self.cities_to_win = 15
            elif self.victory_condition_type == 'advanced_15' and num_players <= 4:
                 # Auto-correct to advanced_18
                 self.victory_condition_type = 'advanced_18'
                 self.cities_to_win = 18

        super(Game, self).save(*args, **kwargs)
        # Create configuration if it's a new game and doesn't exist yet
        # Moved from signal to ensure it happens reliably within the save transaction
        if is_new:
            Configuration.objects.get_or_create(game=self)

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
                print("Error 1: Area not found!")
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

        msg = "Checking phase change in game %s (Phase: %s, All Done: %s, Time Exceeded: %s)\n" % (self.pk, self.get_phase_display(), all_done, time_exceeded)

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
        config = self.configuration
        is_spring = (self.season == 1)
        is_summer = (self.season == 2)
        # is_fall = (self.season == 3) # Not needed for current logic

        if logging: logging.info("Game %s: Processing phase %s (%s) for %s %s" % (self.id, phase, self.get_phase_display(), self.year, self.get_season_display()))

        if phase == PHREINFORCE: # Spring Adjustments & Income
            # Optional Disasters (Rule III.A/B - Spring only)
            if is_spring and config.famine:
                self.mark_famine_areas()
            if is_spring and config.plague:
                self.kill_plague_units() # Happens after famine

            # Advanced Income (Rule V.B - Spring only)
            if is_spring and config.finances:
                self.assign_incomes() # Calculate income

            # Unit Adjustments (Basic V or Advanced V.B.3/VI.A)
            self.adjust_units() # Place new / Disband unpaid/excess units

        elif phase == PHORDERS: # Order Writing (+ Conceptual Negotiation, Lenders)
             # Optional Storms (Rule III.C - Summer only, before orders conceptually)
             if is_summer and config.storms:
                  self.mark_storm_areas() # Apply storm effects before orders are processed

             # Optional Lenders (Rule X.B - Check defaults before orders)
             if config.lenders:
                  self.check_loans() # Check for defaults

             # Order writing itself happens via user interaction before this phase is marked done.
             pass # No specific server-side action needed *during* this processing step

        elif phase == PHRETREATS: # Order Execution & Retreats (+ Conceptual Expenses, Assassination)
            # Advanced Expenses (Rule VI.B / IV.D - Process before orders)
            if config.finances:
                self.process_expenses()

            # Advanced Assassinations (Rule VI.B / IV.E - Process after expenses, before orders)
            if config.finances and config.assassinations:
                self.process_assassinations()
                # Apply assassination effects (garrison surrender, rebellions) immediately
                for p in self.player_set.filter(assassinated=True):
                    # Remove besieged garrisons (Rule VI.C.6.e)
                    besieged_garrisons = Unit.objects.filter(
                        player=p, type='G', area__unit__siege_stage__gt=0, area__unit__player__game=self # Check siege_stage > 0
                    ).distinct()
                    for garrison in besieged_garrisons:
                        besieger = Unit.objects.filter(area=garrison.area, siege_stage__gt=0).first()
                        if logging: logging.info("Assassination: Garrison %s surrenders to %s." % (garrison, besieger if besieger else 'siege'))
                        if signals: signals.unit_surrendered.send(sender=garrison, context="assassination")
                        garrison.delete()
                        if besieger:
                            besieger.siege_stage = 0 # Reset siege
                            # besieger.besieging = False # Removed field
                            besieger.save(update_fields=['siege_stage'])

                    # Trigger province rebellions (Rule VI.C.6.f)
                    for area in p.gamearea_set.exclude(board_area__is_sea=True):
                         area.check_assassination_rebellion()

                # Apply assassination paralysis (Rule VI.C.6.d) - change orders to Hold
                for p in self.player_set.filter(assassinated=True):
                    p.cancel_orders(hold=True) # Changes relevant orders to 'H'

            # Order Execution (Basic VIII / Advanced IV.F)
            self.process_orders() # Resolve movements, conflicts, sieges, set must_retreat

            # Retreat Processing (If retreats were generated by process_orders)
            if Unit.objects.filter(player__game=self).exclude(must_retreat__exact='').exists():
                # This indicates retreats are needed. The game state should pause here
                # to allow players to input retreat orders via the view (play_retreats).
                # The actual processing of RetreatOrder objects happens when the *next*
                # phase transition occurs (or manually triggered by check_turns).
                # For now, we just note that retreats are pending.
                if logging: logging.info("Game %s: Retreats are required." % self.id)
                # We don't call self.process_retreats() here.
            else:
                 # If no retreats, clear any leftover RetreatOrder objects just in case
                 RetreatOrder.objects.filter(unit__player__game=self).delete()


    def advance_to_next_phase(self):
        """ Determines and sets the next phase based on season and configuration. """
        current_phase = self.phase
        current_season = self.season
        current_year = self.year
        config = self.configuration

        next_phase = PHINACTIVE # Default if game ends
        next_season = current_season
        next_year = current_year

        # --- Determine Next Step Based on Current Phase ---
        if current_phase == PHREINFORCE: # After Spring Reinforce/Income
            next_phase = PHORDERS
        elif current_phase == PHORDERS: # After Order Writing
            # Check if retreats are needed before moving to execution
            if Unit.objects.filter(player__game=self).exclude(must_retreat__exact='').exists():
                 # This case shouldn't happen if process_orders clears must_retreat before phase advance
                 if logging: logging.warning("Game {self.id}: must_retreat flags found unexpectedly before PHRETREATS phase.")
                 next_phase = PHRETREATS # Go to retreats if needed
            else:
                 # If finances are on, potentially go through Expense/Assassination steps conceptually
                 # before the actual execution/retreat phase.
                 # For simplicity, we go directly to the execution phase (PHRETREATS)
                 # and handle expense/assassination effects within its processing.
                 next_phase = PHRETREATS
        elif current_phase == PHRETREATS: # After Order Execution/Retreats
            # --- End of Season Transition ---
            self.end_of_season_checks(season_ended=current_season)
            if self.phase == PHINACTIVE: return # Game ended during checks (winner found)

            if current_season == 3: # End of Fall -> New Year Spring
                next_season = 1
                next_year = current_year + 1
                next_phase = PHREINFORCE # Start Spring with Reinforce/Income
            else: # End of Spring/Summer -> Next Season
                next_season = current_season + 1
                next_phase = PHORDERS # Start Summer/Fall with Order Writing

        # --- Update Game State ---
        if next_phase != PHINACTIVE:
            self.phase = next_phase
            self.season = next_season
            self.year = next_year
            self.last_phase_change = datetime.now()
            # Reset assassination status for the new turn (happens before phase actions)
            self.player_set.filter(assassinated=True).update(assassinated=False)
            # Reset Pope's sentencing status
            self.player_set.filter(has_sentenced=True).update(has_sentenced=False)

            self.save()
            if logging: logging.info("Game {self.id}: Advanced to {self.year} {self.get_season_display()} - {self.get_phase_display()}")
        # else: Game ended, phase remains PHINACTIVE (set by check_winner/game_over)

    
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
        """ Performs checks that happen at the end of a specific season,
            AFTER orders and retreats for that season are fully resolved. """
        if logging: logging.info("Game {self.id}: Performing end-of-season checks for season {season_ended}")
        config = self.configuration

        # --- Actions at End of ANY Season ---
        # Clear standoff markers for the next turn
        self.gamearea_set.filter(standoff=True).update(standoff=False)
        # Clear must_retreat flags (should be clear already, but belt-and-suspenders)
        Unit.objects.filter(player__game=self).exclude(must_retreat__exact='').update(must_retreat='')
        # Clear processed RetreatOrder objects (should be clear already)
        RetreatOrder.objects.filter(unit__player__game=self).delete()

        # --- Actions Specific to End of Spring ---
        if season_ended == 1: # End of Spring
            # Famine units removed (Rule III.B)
            if config.famine:
                famine_units = Unit.objects.filter(player__game=self, area__famine=True)
                if famine_units.exists():
                    if logging: logging.info("Game {self.id} (End of Spring): Removing {famine_units.count()} units due to famine.")
                    # Log which units are removed before deleting
                    for unit in famine_units:
                         if signals: signals.unit_disbanded.send(sender=unit, context="famine")
                    famine_units.delete()
                # Famine markers are reset when famine is checked next Spring
                # self.gamearea_set.filter(famine=True).update(famine=False) # Don't reset here

            # Plague units already killed in PHREINFORCE phase processing

        # --- Actions Specific to End of Summer ---
        elif season_ended == 2: # End of Summer
             # Storm markers are reset when storms are checked next Summer
             # self.gamearea_set.filter(storm=True).update(storm=False) # Don't reset here
             pass

        # --- Actions Specific to End of Fall ---
        elif season_ended == 3: # End of Fall
            # Storm units removed (Rule III.C)
            if config.storms:
                storm_units = Unit.objects.filter(player__game=self, area__storm=True)
                if storm_units.exists():
                     if logging: logging.info("Game {self.id} (End of Fall): Removing {storm_units.count()} units due to storms.")
                     for unit in storm_units:
                          if signals: signals.unit_disbanded.send(sender=unit, context="storm")
                     storm_units.delete()
                # Storm markers reset next Summer

            # Update area control based on final unit presence (Rule V.C)
            self.update_controls()

            # Check eliminations (Rule V.D.1)
            eliminated_this_turn = False
            for p in self.player_set.filter(eliminated=False, user__isnull=False):
                if p.check_eliminated():
                    p.eliminate() # Handles unit removal etc.
                    eliminated_this_turn = True

            # Check conquerings (Rule V.D.2) - only if eliminations happened? No, check anyway.
            if config.conquering:
                self.check_conquerings()

            # Check for winner AFTER all end-of-fall actions (Rule III.A)
            if self.check_winner():
                if logging: logging.info("Game {self.id}: Winner found at end of Fall {self.year}.")
                # Game ends here, set phase to inactive to stop further advancement
                self.phase = PHINACTIVE
                self.save(update_fields=['phase'])
                # Winner processing (scores, etc.) happens in the calling function (check_finished_phase)

    def adjust_units(self):
        """ Places new units and disbands the ones that are not paid (Finance rules).
            Or adjusts units based on city count (Basic rules). """
        if self.configuration.finances:
            # Disband unpaid units
            to_disband = Unit.objects.filter(player__game=self, placed=True, paid=False).exclude(player__user__isnull=True) # Exclude autonomous
            if to_disband.exists():
                if logging: logging.info("Game {self.id}: Disbanding {to_disband.count()} unpaid units.")
                to_disband.delete()
            # Place newly built units
            to_place = Unit.objects.filter(player__game=self, placed=False)
            if to_place.exists():
                 if logging: logging.info("Game {self.id}: Placing {to_place.count()} new units.")
                 for u in to_place: u.place() # Calls signal etc.
            # Mark all remaining non-autonomous units as unpaid for the *next* Spring
            Unit.objects.filter(player__game=self).exclude(player__user__isnull=True).update(paid=False)
        else: # Basic Game Logic
            # Units marked paid=False by view logic need disbanding
            to_disband = Unit.objects.filter(player__game=self, placed=True, paid=False).exclude(player__user__isnull=True)
            if to_disband.exists():
                if logging: logging.info("Game {self.id}: Disbanding {to_disband.count()} excess units (Basic).")
                to_disband.delete()
            # Units marked placed=False by view logic need placing
            to_place = Unit.objects.filter(player__game=self, placed=False)
            if to_place.exists():
                if logging: logging.info("Game {self.id}: Placing {to_place.count()} new units (Basic).")
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
        if logging: logging.info("Game {self.id}: Variable income roll (Spring {self.year}): {die}")

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
            info += "Checking support order {s_order.id} from {supporter}.\n"
            # Find attacks specifically targeting this supporter's area
            attacks_on_supporter = attacking_orders.filter(
                ~Q(unit__player=supporter.player) & # Must be enemy attack
                (Q(destination=supporter.area) | Q(unit__area=supporter.area)) # Target area matches
            )

            if attacks_on_supporter.exists():
                info += "Supporting unit {supporter} is being attacked.\n"
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
                        info += "Attack from {attack_order.unit} is from the supported area ({support_target_area.board_area.code}). Support NOT cut.\n"
                        continue # This attack doesn't cut support
                    else:
                        info += "Attack from {attack_order.unit} (in {attack_order.unit.area.board_area.code}) cuts support into {support_target_area.board_area.code}.\n"
                        support_cut = True
                        break # One cutting attack is enough

                if support_cut:
                    if signals: signals.support_broken.send(sender=supporter)
                    orders_to_delete.append(s_order.id)

        if orders_to_delete:
             Order.objects.filter(id__in=orders_to_delete).delete()
             info += "Deleted {len(orders_to_delete)} cut support orders.\n"

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
            info += "Checking convoy order {c_order.id} by {fleet}.\n"
            # Check attacks targeting the fleet's area
            attacks_on_fleet = Order.objects.filter(
                ~Q(unit__player=fleet.player) & Q(unit__player__game=self, confirmed=True) &
                (Q(code='-', destination=fleet.area) | Q(code='=', unit__area=fleet.area, type__in=['A','F']))
            )
            if not attacks_on_fleet.exists():
                continue # Fleet not attacked

            info += "Convoying fleet {fleet} is under attack.\n"
            fleet_strength_obj = Unit.objects.get_with_strength(self.game, id=fleet.id)
            fleet_strength = fleet_strength_obj.strength

            dislodged = False
            for attack_order in attacks_on_fleet:
                attacker_strength_obj = Unit.objects.get_with_strength(self.game, id=attack_order.unit.id)
                attacker_strength = attacker_strength_obj.strength
                info += "Attacked by {attack_order.unit} (Strength: {attacker_strength}). Fleet strength: {fleet_strength}.\n"
                # If any single attacker has > strength, fleet is dislodged
                # If attacker has == strength, it's a standoff, fleet holds, convoy proceeds.
                if attacker_strength > fleet_strength:
                    info += "Fleet {fleet} will be dislodged by {attack_order.unit}. Cancelling convoy.\n"
                    dislodged = True
                    break # One successful dislodge is enough

            if dislodged:
                orders_to_delete.append(c_order.id)
                # Also cancel the corresponding army's advance order if it relied solely on this convoy
                army_order = Order.objects.filter(unit=c_order.subunit, code='-', destination=c_order.subdestination, confirmed=True).first()
                if army_order:
                    # Check if other convoys exist for this army move (complex)
                    # Simplification: Assume if the main convoy fails, the move fails.
                    info += "Cancelling advance order for convoyed army {c_order.subunit}.\n"
                    orders_to_delete.append(army_order.id)


        if orders_to_delete:
             Order.objects.filter(id__in=orders_to_delete).delete()
             info += "Deleted {len(orders_to_delete)} orders due to disrupted convoys.\n"

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
                    info += "Impossible attack: {order}. Area not adjacent and no valid convoy.\n"
                    orders_to_delete.append(order.id)

        if orders_to_delete:
            Order.objects.filter(id__in=orders_to_delete).delete()
            info += "Deleted {len(orders_to_delete)} unreachable attack orders.\n"
        return info


    def resolve_auto_garrisons(self):
        """ Units with '= G' orders in areas without a garrison, convert into garrison. """
        info = u"Step 1: Process unopposed conversions to Garrison.\n"
        garrisoning_orders = Order.objects.filter(unit__player__game=self, code='=', type='G', confirmed=True)
        orders_to_delete = []
        units_converted = []

        for g_order in garrisoning_orders:
            unit = g_order.unit
            info += "{unit} tries to convert into garrison in {unit.area}.\n"
            # Check if city already has a garrison
            if Unit.objects.filter(area=unit.area, type='G').exists():
                info += "Fail: Garrison already exists in {unit.area}.\n"
                orders_to_delete.append(g_order.id) # Order fails
            else:
                # Check if another unit is trying to convert to G in the same area
                competing_conversions = garrisoning_orders.filter(unit__area=unit.area).exclude(id=g_order.id)
                if competing_conversions.exists():
                     info += "Fail: Competing conversion to Garrison in {unit.area}.\n"
                     # Both fail? Or highest strength wins? Rules don't specify. Assume both fail.
                     orders_to_delete.append(g_order.id)
                     for comp_order in competing_conversions:
                         if comp_order.id not in orders_to_delete: orders_to_delete.append(comp_order.id)
                else:
                    # Conversion successful
                    info += "Success! {unit} converts to Garrison.\n"
                    unit.convert('G') # Update unit type
                    units_converted.append(unit.id)
                    orders_to_delete.append(g_order.id) # Order completed

        if orders_to_delete:
            Order.objects.filter(id__in=orders_to_delete).delete()
            info += "Processed {len(garrisoning_orders)} Garrison conversion orders.\n"

        return info


    def resolve_conflicts(self):
        """ Resolves conflicts based on strength and orders, considering coasts. (Rule VIII.B) """
        info = u"Step 5: Process conflicts.\n"
        # Get potentially conflicting orders (confirmed Advance, Convert A/F)
        conflicting_orders = Order.objects.filter(
            unit__player__game=self, confirmed=True
        ).exclude(code__in=['H', 'S', 'B', 'C', 'L', '0', '=G']) \
         .select_related('unit__area__board_area', 'unit__player', 'destination__board_area', 'subunit') # Optimize

        # Identify unique target areas
        target_areas_ids = set()
        for order in conflicting_orders:
            target_ga = order.get_attacked_area() # Gets destination for '-' or unit.area for '='
            if target_ga: target_areas_ids.add(target_ga.id)

        target_game_areas = GameArea.objects.filter(id__in=target_areas_ids).select_related('board_area')

        processed_units = set() # Track unit IDs whose orders have been resolved
        retreating_units = {} # {unit_id: source_area_code}

        for area in target_game_areas:
            info += "\nResolving conflicts for area: {area.board_area.code}\n"
            area.standoff = False # Reset standoff for this resolution step

            # Units trying to ENTER this area
            invading_orders = conflicting_orders.filter(
                Q(code='-', destination=area) |
                Q(code='=', unit__area=area, type__in=['A', 'F'])
            )

            # Unit(s) currently OCCUPYING this area (A/F unit)
            # Use select_related for efficiency
            occupier = Unit.objects.select_related('area__board_area', 'player') \
                           .filter(area=area, type__in=['A', 'F']).first() # Use first()
            occupying_order = None
            if occupier:
                occupying_order = Order.objects.filter(unit=occupier, confirmed=True).first()
                if occupier.id in retreating_units: # Ignore if already retreating
                    occupier = None
                    occupying_order = None

            # --- Calculate Strengths & Check Adjacency ---
            invader_strengths = {} # {order_id: strength}
            valid_invading_orders = [] # Orders that can actually reach the area

            for order in invading_orders:
                if order.unit.id in processed_units: continue

                # Re-check adjacency/possibility here for robustness, considering coasts
                is_possible_now = False
                if order.code == '-':
                    is_possible_now = order.unit.area.board_area.is_adjacent(
                        area.board_area,
                        fleet=(order.unit.type == 'F'),
                        source_unit_coast=order.unit.coast,
                        target_order_coast=order.destination_coast
                    )
                    # Add convoy check if needed: or order.find_convoy_line() # find_convoy_line needs update for coast?
                elif order.code == '=': # Conversion G->A/F
                    # Adjacency not relevant, but check basic possibility
                    is_possible_now = order.is_possible() # Use the order's check

                if not is_possible_now:
                    info += "Order impossible/unreachable now: {order}. Deleting.\n"
                    processed_units.add(order.unit.id)
                    order.delete()
                    continue # Skip this order

                # If possible, calculate strength
                try:
                    strength_obj = Unit.objects.get_with_strength(self.game, id=order.unit.id)
                    invader_strengths[order.id] = strength_obj.strength
                    valid_invading_orders.append(order) # Add to list of valid invaders
                    info += "Invader: {order.unit} (Strength: {strength_obj.strength})\n"
                except Unit.DoesNotExist:
                    info += "Error: Unit for order {order.id} not found during strength calc.\n"
                    order.delete() # Clean up invalid order


            occupier_strength = 0
            if occupier and occupier.id not in processed_units:
                try:
                    # Occupier strength includes support for HOLDING
                    strength_obj = Unit.objects.get_with_strength(self.game, id=occupier.id)
                    occupier_strength = strength_obj.strength # get_with_strength handles hold support
                    info += "Occupier: {occupier} (Strength: {occupier_strength})\n"
                except Unit.DoesNotExist:
                     info += "Error: Occupier unit {occupier.id} not found during strength calc.\n"
                     occupier = None # Treat as non-existent


            # --- Resolve Standoffs among Invaders ---
            max_invader_strength = 0
            winners = []
            if invader_strengths:
                max_invader_strength = max(invader_strengths.values()) if invader_strengths else 0
                winners = [oid for oid, s in invader_strengths.items() if s == max_invader_strength]

            if len(winners) > 1: # Standoff among invaders
                info += "Standoff among invaders for {area.board_area.code} (Strength: {max_invader_strength}).\n"
                area.standoff = True
                # All involved invaders fail and hold
                for order_id in invader_strengths.keys():
                    try:
                        order = Order.objects.get(id=order_id)
                        processed_units.add(order.unit.id)
                        order.delete()
                    except Order.DoesNotExist: pass # Might have been deleted already
                if occupier: processed_units.add(occupier.id) # Occupier holds
                # Save standoff status after processing all orders for the area
                # area.save() # Moved save outside loop
                continue # Move to next area

            # --- Resolve Single Winner vs Occupier ---
            winning_order = None
            if len(winners) == 1:
                try:
                    winning_order = Order.objects.get(id=winners[0])
                    winning_strength = max_invader_strength
                    info += "Winning invader: {winning_order.unit} (Strength: {winning_strength})\n"

                    if occupier:
                        if winning_strength > occupier_strength: # Invader wins, occupier retreats
                            info += "{winning_order.unit} dislodges {occupier}.\n"
                            retreating_units[occupier.id] = winning_order.unit.area.board_area.code
                            processed_units.add(occupier.id)
                            if occupying_order: occupying_order.delete()
                            # Execute winning order, passing coast
                            if winning_order.code == '-':
                                winning_order.unit.invade_area(area, target_coast=winning_order.destination_coast)
                            elif winning_order.code == '=':
                                winning_order.unit.convert(winning_order.type)
                            processed_units.add(winning_order.unit.id)
                            winning_order.delete()
                        elif winning_strength == occupier_strength: # Bounce / Standoff
                            info += "Bounce between {winning_order.unit} and {occupier}.\n"
                            area.standoff = True
                            processed_units.add(winning_order.unit.id)
                            winning_order.delete()
                            processed_units.add(occupier.id)
                        else: # Occupier wins, invader holds
                            info += "{occupier} holds against {winning_order.unit}.\n"
                            processed_units.add(winning_order.unit.id)
                            winning_order.delete()
                            processed_units.add(occupier.id)
                    else: # No occupier, invader succeeds
                        info += "{winning_order.unit} successfully enters empty {area.board_area.code}.\n"
                        # Execute winning order, passing coast
                        if winning_order.code == '-':
                            winning_order.unit.invade_area(area, target_coast=winning_order.destination_coast)
                        elif winning_order.code == '=':
                            winning_order.unit.convert(winning_order.type)
                        processed_units.add(winning_order.unit.id)
                        winning_order.delete()

                except Order.DoesNotExist:
                    info += "Error: Winning order {winners[0]} not found.\n"

            elif not winners and occupier: # No valid invaders, occupier holds
                 info += "Occupier {occupier} holds uncontested.\n"
                 processed_units.add(occupier.id)
                 # Occupier executes original order only if it wasn't just holding/supporting hold
                 if occupying_order and occupying_order.code not in ['H', 'S'] : # If it was moving/convoying etc.
                      # This order should have been processed when resolving *its* target area.
                      # If it's still here, it likely failed. Delete it.
                      info += "Deleting occupier's non-hold order {occupying_order.id} as it likely failed elsewhere.\n"
                      occupying_order.delete()

            # Save standoff status for the area after all checks
            if area.standoff:
                area.save(update_fields=['standoff'])

        # --- Update retreating units ---
        for unit_id, source_code in retreating_units.items():
            Unit.objects.filter(id=unit_id).update(must_retreat=source_code)

        # --- Cleanup remaining confirmed orders ---
        remaining_orders = Order.objects.filter(
            unit__player__game=self, confirmed=True
        ).exclude(unit_id__in=processed_units)

        orders_to_delete_ids = []
        units_to_disband_ids = []
        for order in remaining_orders:
             # Process non-conflicting orders like Lift, Disband, Convoy(hold), Support(hold)
             if order.code == 'L':
                 if order.unit.siege_stage > 0:
                     order.unit.siege_stage = 0
                     order.unit.besieging = False
                     order.unit.save(update_fields=['siege_stage', 'besieging'])
                     info += "{order.unit} lifts siege.\n"
                 orders_to_delete_ids.append(order.id)
             elif order.code == '0':
                 info += "{order.unit} disbands.\n"
                 units_to_disband_ids.append(order.unit.id)
                 # Order deleted with unit
             elif order.code == 'C':
                 info += "{order.unit} provides convoy (holds position).\n"
                 orders_to_delete_ids.append(order.id)
             elif order.code == 'S':
                 info += "{order.unit} provides support (holds position).\n"
                 orders_to_delete_ids.append(order.id)
             elif order.code == 'H':
                 info += "{order.unit} holds.\n"
                 orders_to_delete_ids.append(order.id)
             # Besiege ('B') orders are handled in resolve_sieges

        if units_to_disband_ids:
            Unit.objects.filter(id__in=units_to_disband_ids).delete()
        if orders_to_delete_ids:
            Order.objects.filter(id__in=orders_to_delete_ids).delete()

        info += u"End of conflicts processing.\n"
        return info

    def process_retreats(self):
        """ Processes RetreatOrder objects created by the view, considering coasts. """
        info = u"Processing Retreats:\n"
        # Use select_related for efficiency
        retreat_orders = RetreatOrder.objects.filter(unit__player__game=self) \
                                             .select_related('unit', 'area__board_area')

        # Units ordered to disband (area is None)
        disband_units_ids = retreat_orders.filter(area__isnull=True).values_list('unit_id', flat=True)
        if disband_units_ids:
            units_to_delete = Unit.objects.filter(id__in=disband_units_ids)
            info += "Disbanding units: {', '.join(str(u) for u in units_to_delete)}\n"
            units_to_delete.delete()

        # Units ordered to retreat to a specific area
        move_orders = retreat_orders.exclude(area__isnull=True)
        # Check for conflicts (multiple units retreating to the same area/coast combo)
        retreat_targets = defaultdict(list) # {(area_id, coast): [unit_id, ...]}
        for order in move_orders:
            target_key = (order.area_id, order.coast)
            retreat_targets[target_key].append(order.unit_id)

        units_to_disband_conflict = set()
        valid_retreats = [] # Store (unit, destination_area, destination_coast)

        for target_key, unit_ids in retreat_targets.items():
            if len(unit_ids) > 1:
                # Conflict: Multiple units targeting same area/coast -> all disband
                area_id, coast = target_key
                dest_ga = GameArea.objects.get(id=area_id) # For logging
                coast_str = "/{coast}" if coast else ""
                info += "Retreat conflict: Units {unit_ids} targeting {dest_ga}{coast_str}. All disband.\n"
                units_to_disband_conflict.update(unit_ids)
            else:
                # Potential valid retreat, store details
                order = move_orders.get(unit_id=unit_ids[0], area_id=target_key[0], coast=target_key[1])
                valid_retreats.append((order.unit, order.area, order.coast))

        # Disband units involved in conflicts
        if units_to_disband_conflict:
             Unit.objects.filter(id__in=units_to_disband_conflict).delete()

        # Process potentially valid retreats
        for unit, destination, retreat_coast in valid_retreats:
            if unit.id in units_to_disband_conflict: continue # Already disbanded

            # Final check: Is destination still valid? (Not standoff, not occupied by A/F)
            try:
                # Refresh destination state from DB
                dest_area = GameArea.objects.get(id=destination.id)
                can_retreat_here = True
                if dest_area.standoff:
                    info += "Cannot retreat {unit} to {destination}: Area became standoff.\n"
                    can_retreat_here = False
                # Check for A/F units that might have moved *into* the destination *after* conflicts were resolved
                # This check might be complex/redundant if conflict resolution is perfect.
                # Let's assume conflict resolution correctly cleared the path or marked standoff.
                # if Unit.objects.filter(area=dest_area, type__in=['A','F']).exists():
                #     info += "Cannot retreat {unit} to {destination}: Area became occupied.\n"
                #     can_retreat_here = False

                if can_retreat_here:
                    coast_str = "/{retreat_coast}" if retreat_coast else ""
                    info += "{unit} retreats to {destination}{coast_str}.\n"
                    unit.retreat(destination, target_coast=retreat_coast) # Pass coast
                else:
                     info += "No valid retreat for {unit} to {destination}. Unit disbands.\n"
                     unit.delete()

            except GameArea.DoesNotExist:
                 info += "Retreat destination {destination.id} not found for {unit}. Unit disbands.\n"
                 try: unit.delete()
                 except Unit.DoesNotExist: pass # Already deleted
            except Unit.DoesNotExist:
                 pass # Unit already deleted (e.g., conflict disband)

        # Clean up processed RetreatOrder objects
        retreat_orders.delete() # Delete all original retreat orders
        info += "Retreat processing complete.\n"
        if logging: logging.info(info)

    def resolve_sieges(self):
        """ Handles starting, continuing, and resolving sieges based on siege_stage. (Rule VIII.C.2) """
        info = u"Step 6: Process sieges.\n"

        # --- Process units ordered to Besiege ('B') ---
        besieging_orders = Order.objects.filter(unit__player__game=self, code='B', confirmed=True)
        processed_order_ids = set()

        for b_order in besieging_orders:
            if b_order.id in processed_order_ids: continue # Skip if already processed (e.g., via assassination)

            b = b_order.unit
            area = b.area
            info += "{b} ordered to besiege in {area.board_area.code}. "
            target_unit = None
            target_rebellion = None

            # Check if player is assassinated (cannot progress siege - Rule VI.C.6.d)
            if b.player.assassinated:
                info += "Player assassinated. Siege does not progress.\n"
                processed_order_ids.add(b_order.id)
                continue # Skip to next order, don't change siege_stage

            # Find target (Enemy Garrison or Garrisoned Rebellion)
            try:
                target_unit = Unit.objects.get(area=area, type='G')
                if target_unit.player == b.player: target_unit = None # Cannot besiege self
                else: info += "Target: Garrison {target_unit}. "
            except Unit.DoesNotExist:
                target_rebellion = area.has_rebellion(b.player, same=False) # Target enemy rebellion
                if target_rebellion and target_rebellion.garrisoned:
                    info += "Target: Garrisoned Rebellion. "
                else: target_rebellion = None # Not a valid siege target

            if not target_unit and not target_rebellion:
                info += "No valid target found. Invalid siege order.\n"
                processed_order_ids.add(b_order.id)
                continue

            # --- Process Siege Stages (Rule VIII.C.2.a) ---
            if b.siege_stage == 0: # Start siege (Stage 1)
                b.siege_stage = 1
                # b.besieging = True # Removed field
                b.save(update_fields=['siege_stage'])
                info += "Siege started (Stage 1).\n"
                if signals: signals.siege_started.send(sender=b)
                # Check immediate surrender if target assassinated (Rule VI.C.6.e) - Handled in process_assassinations

            elif b.siege_stage == 1: # Continue siege (Stage 2)
                b.siege_stage = 2
                b.save(update_fields=['siege_stage'])
                info += "Siege continues (Stage 2).\n"
                # Check immediate surrender if target assassinated - Handled in process_assassinations

            elif b.siege_stage == 2: # Siege successful (End of Stage 2)
                info += "Siege successful! "
                if target_unit:
                    info += "Garrison {target_unit} removed.\n"
                    if signals: signals.unit_surrendered.send(sender=target_unit, context="siege")
                    target_unit.delete()
                elif target_rebellion:
                    info += "Rebellion removed.\n"
                    target_rebellion.delete()
                b.siege_stage = 0 # Reset siege state
                # b.besieging = False # Removed field
                b.save(update_fields=['siege_stage'])

            processed_order_ids.add(b_order.id) # Mark order as processed

        # Delete processed Besiege orders
        Order.objects.filter(id__in=processed_order_ids).delete()

        # --- Process units ordered to Lift Siege ('L') ---
        # This is now handled in resolve_conflicts cleanup as 'L' orders don't conflict

        # --- Reset siege stage for units whose siege was broken ---
        # (e.g., forced to retreat, or didn't give 'B' order)
        broken_sieges = Unit.objects.filter(
            player__game=self, siege_stage__gt=0
        ).exclude(
            order__code='B', order__confirmed=True # Exclude units that successfully continued siege
        ).exclude(
            must_retreat__exact='' # Exclude units currently retreating
        )

        for b in broken_sieges:
            info += "Siege by {b} broken (no Besiege order or forced retreat).\n"
            b.siege_stage = 0
            # b.besieging = False # Removed field
            b.save(update_fields=['siege_stage'])

        return info

    def announce_retreats(self):
        """ Logs units that must retreat. """
        info = u"Step 7: Announce Retreats\n"
        retreating = Unit.objects.filter(player__game=self).exclude(must_retreat__exact='')
        if retreating.exists():
            for u in retreating:
                info += "{u} must retreat from {u.area} (attack from {u.must_retreat}).\n"
                if signals: signals.forced_to_retreat.send(sender=u)
        else:
            info += "No retreats required this turn.\n"
        return info

# Example in models.py Game class
def adjudicate_movement_phase(self):
    """Runs only the core adjudication logic for movement orders."""
    # Ensure orders are marked confirmed if needed by logic
    # Order.objects.filter(unit__player__game=self).update(confirmed=True) # Or assume they are confirmed

    info = u"Adjudicating Movement Phase for DATC:\n"
    # Call the sequence of filtering and resolution steps
    # Make sure these methods operate correctly in isolation
    info += self.resolve_auto_garrisons() # Step 1
    info += self.filter_supports()        # Step 2
    info += self.filter_convoys()         # Step 3
    info += self.filter_unreachable_attacks() # Step 4
    info += self.resolve_conflicts()      # Step 5 (Sets must_retreat)
    info += self.resolve_sieges()         # Step 6
    info += self.announce_retreats()      # Step 7 (Logs who must retreat)

    # DO NOT delete orders here if _get_actual_poststate needs them
    # DO NOT change game phase/season/year
    if logging: logging.debug("DATC Adjudication Log Game {self.id}:\n{info}") # Use debug level

    def preprocess_orders(self):
        """
        Deletes unconfirmed orders, logs confirmed ones, and handles basic validation/cleanup.
        """
        # Delete unconfirmed orders
        Order.objects.filter(unit__player__game=self, confirmed=False).delete()

        # Delete orders from players who don't control the unit (unless finances/bribes allow)
        if not self.configuration.finances: # Basic game: only owner can order
             orders_to_delete = Order.objects.filter(player__game=self, confirmed=True).exclude(player=F('unit__player'))
             if orders_to_delete.exists():
                  if logging: logging.warning("Game {self.id}: Deleting {orders_to_delete.count()} confirmed orders from non-owning players (Basic Game).")
                  orders_to_delete.delete()
        # else: Advanced game allows ordering bought units, validation happens later.

        # Log confirmed orders (excluding simple Holds)
        for o in Order.objects.filter(player__game=self, confirmed=True).exclude(code='H'):
            if signals:
                signals.order_placed.send(sender=o)

    def process_orders(self):
        """ Run a batch of methods in the correct order to process all the orders. """
        self.preprocess_orders() # Clean up unconfirmed/invalid orders first

        info = "Processing orders in game {self.slug} ({self.year} {self.get_season_display()})\n"
        info += "------------------------------\n\n"

        # Adjudication Steps (Based on Diplomacy Adjudication Test Cases order)
        info += self.resolve_auto_garrisons() # Step 1: Unopposed G conversions (Not standard Diplomacy, specific to this implementation?)
        info += "\n"
        info += self.filter_supports()        # Step 2: Cut supports
        info += "\n"
        info += self.filter_convoys()         # Step 3: Disrupt convoys
        info += "\n"
        info += self.filter_unreachable_attacks() # Step 4: Remove impossible moves
        info += "\n"
        info += self.resolve_conflicts()      # Step 5: Resolve bounces, dislodgements, set must_retreat
        info += "\n"
        info += self.resolve_sieges()         # Step 6: Process siege starts/continuations/successes
        info += "\n"
        info += self.announce_retreats()      # Step 7: Log required retreats

        info += "--- END ORDER PROCESSING ---\n"

        if logging:
            logging.info(info)

        # Log the adjudication details for the turn
        turn_log = TurnLog(game=self, year=self.year,
                            season=self.season,
                            phase=self.phase, # Log the phase where orders were executed (PHRETREATS)
                            log=info)
        turn_log.save()

        # Note: Retreat processing (handling RetreatOrder objects) happens *after* this,
        # typically triggered by advancing the phase if retreats are needed.

    def process_retreats(self):
        """ Processes RetreatOrder objects created by the view. (Rule VIII.B.6) """
        info = u"Processing Retreats:\n"
        retreat_orders = RetreatOrder.objects.filter(unit__player__game=self)

        # Units ordered to disband
        disband_units = retreat_orders.filter(area__isnull=True).values_list('unit', flat=True)
        if disband_units:
            units_to_delete = Unit.objects.filter(id__in=disband_units)
            info += "Disbanding units: {', '.join(map(str, units_to_delete))}\n"
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
                info += "Retreat conflict for {unit} targeting {destination}. Unit disbands.\n"
                try: unit.delete()
                except Unit.DoesNotExist: pass # Might already be deleted if involved in multiple conflicts
            else:
                # Check if destination is still valid (not standoff, not occupied by A/F)
                try:
                    dest_area = GameArea.objects.get(id=destination.id)
                    can_retreat_here = True
                    if dest_area.standoff: # Rule VIII.B.6.c.1
                        info += "Cannot retreat {unit} to {destination}: Area is standoff.\n"
                        can_retreat_here = False
                    if Unit.objects.filter(area=dest_area, type__in=['A','F']).exists():
                        info += "Cannot retreat {unit} to {destination}: Area occupied.\n"
                        can_retreat_here = False
                    # Cannot retreat where attacker came from (already filtered in get_possible_retreats)

                    if can_retreat_here:
                        info += "{unit} retreats to {destination}.\n"
                        unit.retreat(destination) # Handles conversion if retreating to own city
                    else:
                         info += "No valid retreat for {unit}. Unit disbands.\n"
                         unit.delete()

                except GameArea.DoesNotExist:
                     info += "Retreat destination {destination.id} not found for {unit}. Unit disbands.\n"
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
                    info += "Area {area.board_area.code}: Control changed from {old_controller_name} to {new_controller.country.name}.\n"
                    area.player = new_controller
                    area.save()
                    if signals: signals.area_controlled.send(sender=area)
            elif len(players_present) > 1:
                # Contested area, no one controls (Rule V.C.1.a)
                if area.player is not None:
                    info += "Area {area.board_area.code}: Control lost by {area.player.country.name} (contested).\n"
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
        if self.phase == PHINACTIVE: return False # Game already finished

        for p in self.player_set.filter(user__isnull=False, eliminated=False):
            num_cities = p.number_of_cities()

            if num_cities >= self.cities_to_win:
                # Basic condition check (Rule III.B)
                if self.victory_condition_type == 'basic':
                    # Must control all original home cities
                    all_home_cities = p.home_country(original=True).filter(board_area__has_city=True)
                    if not all_home_cities.exists(): # Should not happen in valid setup
                         if logging: logging.warning("Player {p} has no original home cities defined for basic win check.")
                         continue
                    if p.controlled_home_cities(original=True).count() != all_home_cities.count():
                         continue # Doesn't control all original home cities

                    # Must control at least 6 conquered cities
                    conquered_cities_count = num_cities - all_home_cities.count()
                    if conquered_cities_count >= 6:
                        if logging: logging.info("Basic Victory: Player {p} controls {num_cities} cities (all home + {conquered_cities_count} conquered).")
                        return True # Basic win condition met

                # Advanced/Ultimate condition check (Rule II.B, II.C, II.D)
                elif self.victory_condition_type in ['advanced_15', 'advanced_18', 'ultimate']:
                    required_conquered_homes = 1 if self.victory_condition_type != 'ultimate' else 2
                    conquered_homes_count = 0
                    # Check players this player has conquered
                    for conquered_player in p.conquered.all():
                         # Check if the conquered player's *original* home country is fully controlled
                         # Note: The rule V.D.2.a implies the conqueror uses the conquered home country,
                         # but the victory condition II.B/C/D just says "control of at least one other player's home country".
                         # Let's interpret this as needing full control at the moment of checking victory.
                         if conquered_player.is_fully_conquered_by(p):
                             conquered_homes_count += 1

                    if conquered_homes_count >= required_conquered_homes:
                        if logging: logging.info("Advanced/Ultimate Victory: Player {p} controls {num_cities} cities and {conquered_homes_count} conquered home countries.")
                        return True # Advanced/Ultimate win condition met

                # Add check for custom victory conditions if needed
                # elif self.victory_condition_type == 'custom':
                #    # Implement custom logic here
                #    pass

        return False # No winner found

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
                print("Error 2: Area not found!")
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
            If original=False, includes conquered home countries the player can use. (Rule V.D.2)
        """
        if not self.country: # Handle autonomous player
             return GameArea.objects.none()

        q = Q(game=self.game) & Q(board_area__home__scenario=self.game.scenario) & Q(board_area__home__is_home=True)

        valid_home_countries = [self.country] # Always include original

        if not original and self.game.configuration.conquering:
            # Rule V.D.2.a: Once complete control is gained, player may use conquered home country.
            # Rule V.D.2.b: This applies even if control of some provinces is later lost.
            # So, we check the 'conqueror' link.
            conquered_players = Player.objects.filter(game=self.game, conqueror=self)
            valid_home_countries.extend([p.country for p in conquered_players if p.country])

        q &= Q(board_area__home__country__in=valid_home_countries)
        return GameArea.objects.filter(q).select_related('board_area') # Optimize

    def controlled_home_country(self):
        """ Returns a queryset with GameAreas in home country controlled by player.
        """

        return self.home_country().filter(player=self)

    def controlled_home_cities(self, original=True):
        """ Returns a queryset with GameAreas in home country (original or all),
            with city, controlled by the player """
        # Use home_country() helper with appropriate 'original' flag
        return self.home_country(original=original).filter(
            player=self,
            board_area__has_city=True
        ).select_related('board_area') # Optimize


    def get_areas_for_new_units(self, finances=False):
        """ Returns a queryset with the GameAreas that accept new units.
            Rule V.B.1.b/c (Basic) / V.B.3.b/c (Advanced)
        """
        # Placement only in controlled home city provinces (original or conquered)
        # Use home_country(original=False) to get all usable home provinces
        q = Q(player=self) & Q(board_area__has_city=True) # Must control, have city
        if self.game.configuration.famine:
             q &= Q(famine=False) # Cannot place in famine area (Rule III.B implied?) - Let's assume this restriction.

        home_provinces = self.home_country(original=False) # Get all usable home provinces
        if not home_provinces.exists():
             return GameArea.objects.none() # No home provinces available

        q &= Q(id__in=home_provinces.values_list('id', flat=True)) # Filter by ID

        areas = GameArea.objects.filter(q).select_related('board_area') # Optimize

        # Exclude areas where placement is blocked (Rule V.B.1.b / V.B.3.c)
        excludes = []
        for a in areas:
            units_in_area = a.unit_set.all() # Units physically in the GameArea
            unit_in_city = units_in_area.filter(type='G').exists()
            unit_in_province = units_in_area.exclude(type='G').exists()

            # Cannot place if both city and province are occupied by *any* unit
            if unit_in_city and unit_in_province:
                excludes.append(a.id)
            # Cannot place if target spot (city/province) is occupied by *another* unit
            # This check is complex without knowing the intended placement type (A/F/G).
            # The form validation should handle this based on user input.
            # Here, we only exclude if *both* spots are full.

        if finances:
            # Exclude areas where an existing unit hasn't been paid (prevents replacing unpaid)
            # Rule V.B.3.d: Old units cannot be traded for new ones *in that same province*.
            for u in self.unit_set.filter(placed=True, paid=False):
                if u.area_id not in excludes:
                    excludes.append(u.area_id)

        return areas.exclude(id__in=excludes)

    def is_fully_conquered_by(self, potential_conqueror):
        """ Checks if this player's original home country is fully controlled
            by the potential_conqueror at the end of a Campaign. (Helper for Rule V.D.2.a/b & Victory) """
        if not self.country: return False # Autonomous players cannot be conquered this way

        # Get all provinces defined as original home for this player in the scenario
        original_home_provinces = GameArea.objects.filter(
            game=self.game,
            board_area__home__scenario=self.game.scenario,
            board_area__home__country=self.country,
            board_area__home__is_home=True
        ).select_related('board_area') # Optimize

        if not original_home_provinces.exists():
             if logging: logging.warning("Player {self} has no original home provinces defined for conquer check.")
             return False # Cannot be conquered if no home provinces defined

        # Check if *any* of these original home provinces are NOT controlled by the potential conqueror
        uncontrolled_exists = original_home_provinces.exclude(player=potential_conqueror).exists()

        # If no uncontrolled provinces exist, the potential conqueror has full control
        return not uncontrolled_exists

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
        """ Checks if the player is eliminated based on Rule V.D.1 and V.D.2.c. This check happens at the end of the Fall campaign. """
        if not self.user: return False # Autonomous players are not eliminated this way

        # Rule V.D.1: Check control of *any* original home city
        if self.controlled_home_cities(original=True).exists():
            return False # Still controls at least one original home city

        # Rule V.D.2.c: If no original home cities, check if *all* home provinces (original + conquered) are lost
        all_home_provinces_q = self.home_country(original=False) # Get queryset of all usable home provinces

        if not all_home_provinces_q.exists():
             # This case implies the player had no home country defined, shouldn't happen.
             # If they have no home provinces, are they eliminated? Rule implies yes if no original home cities.
             if logging: logging.warning("Player {self} has no defined home provinces for elimination check.")
             return True # Eliminated if no original home cities and no home provinces exist

        # Check if they control *any* province within their original OR conquered home countries
        if all_home_provinces_q.filter(player=self).exists():
            return False # Still controls at least one province in the combined home territories

        # If no original home cities controlled AND no provinces controlled in *any* home territory (original+conquered) -> Eliminated
        if logging: logging.info("Player {self} eliminated (lost all original home cities AND all provinces in combined home territories)")
        return True

    def eliminate(self):
        """ Eliminates the player and removes units, controls, etc. (Rule V.D.1) """
        if self.user and not self.eliminated: # Prevent double elimination
            if logging: logging.info("Game {self.game.id}: Eliminating player {self.user.username} ({self.country})")
            self.eliminated = True
            self.ducats = 0 # Lose all money
            self.is_excommunicated = False # Excommunication lifted on elimination
            self.pope_excommunicated = False
            # Keep conqueror status if already conquered by someone else
            self.save(update_fields=['eliminated', 'ducats', 'is_excommunicated', 'pope_excommunicated']) # Specify fields

            if signals: signals.country_eliminated.send(sender=self, country=self.country)

            # Remove military units (Rule V.D.1)
            self.unit_set.all().delete()
            # Remove control from all areas they owned
            self.gamearea_set.all().update(player=None)
            # Remove pending orders
            self.order_set.all().delete()
            # Remove pending expenses and refund ducats? Rule doesn't say. Let's just delete.
            self.expense_set.all().delete()
            # Remove pending assassination attempts *by* this player
            self.assassination_attempts.all().delete()
            # Remove assassin tokens *owned* by this player
            self.assassin_set.all().delete()
            # Remove loans owed *by* this player (Rule X doesn't specify, assume forgiven/lost)
            Loan.objects.filter(player=self).delete()
            # Remove pending revolution attempts *against* this player
            Revolution.objects.filter(government=self).delete()

            # Clear excommunications *if* they were the Pope (Rule implies Papacy is unique)
            if self.game.configuration.excommunication and self.may_excommunicate:
                if logging: logging.info("Game {self.game.id}: Eliminated Pope ({self.user.username}) lifts all excommunications.")
                self.game.player_set.all().update(is_excommunicated=False, pope_excommunicated=False)

            # Mark player as done for the current phase
            self.done = True
            self.save(update_fields=['done'])
            self.game.reset_players_cache() # Update cached player list


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

    def get_income(self, die_roll, major_city_ids):
        """ Gets the total income in one Spring turn (Advanced Rule V.B). """
        income = 0
        config = self.game.configuration

        # 1. Bodies of Water (Rule V.B.1.a)
        income += self.unit_set.filter(type='F', area__board_area__is_sea=True).count()

        # Get controlled areas, excluding seas and handling rebellions/famine
        controlled_areas = self.gamearea_set.exclude(board_area__is_sea=True)
        if config.finances: # Rebellions only matter with finances
             rebellion_area_ids = Rebellion.objects.filter(area__game=self.game).values_list('area_id', flat=True)
             controlled_areas = controlled_areas.exclude(id__in=rebellion_area_ids) # Rule VI.C.5.c.3
        if config.famine:
             controlled_areas = controlled_areas.exclude(famine=True) # Rule VI.C.3

        # 2. Provinces (Rule V.B.1.b)
        # Income from province itself (1d)
        income += controlled_areas.count()

        # 3. Cities (Rule V.B.1.c)
        controlled_city_areas = controlled_areas.filter(board_area__has_city=True)
        for city_area in controlled_city_areas:
            board_area = city_area.board_area
            is_besieged = city_area.unit_set.filter(siege_stage__gt=0).exists() # Rule VI.C.2
            is_garrisoned_by_owner = city_area.unit_set.filter(type='G', player=self).exists()

            if is_besieged:
                 continue # No income from besieged city

            # Check if city is major
            is_major = board_area.id in major_city_ids
            city_income_value = 0
            if is_major:
                 # Get income value (from Area model first, fallback to CityIncome if needed)
                 city_income_value = board_area.major_city_income
                 if city_income_value is None:
                      try:
                           # Fallback to CityIncome model if Area.major_city_income is null
                           # This assumes CityIncome model stores the value, which it doesn't currently.
                           # Best practice: Store value ONLY in Area.major_city_income.
                           # If using CityIncome model, it needs a 'value' field.
                           # For now, assume Area.major_city_income is the source.
                           if board_area.major_city_income: # Check again if it has a value
                                city_income_value = board_area.major_city_income
                           else: # If still None, treat as normal city for income calc
                                city_income_value = 1
                                is_major = False # Not actually major for income purposes
                      except AttributeError: # If major_city_income field doesn't exist
                           city_income_value = 1
                           is_major = False
                 if city_income_value <= 1: # Treat as normal if value is 1 or less
                      is_major = False
                      city_income_value = 1

            else: # Normal city
                 city_income_value = 1

            # Add city income
            income += city_income_value

            # Handle case where province is in rebellion/famine but city is garrisoned (Rule VI.C.3 / VI.C.5.c.3)
            # If the province itself was excluded earlier due to rebellion/famine,
            # but the city *is* garrisoned by the owner, the city *still* provides income.
            province_excluded = False
            if config.finances and city_area.id in rebellion_area_ids: province_excluded = True
            if config.famine and city_area.famine: province_excluded = True

            if province_excluded and is_garrisoned_by_owner:
                 # We already added the city income value above.
                 # We need to make sure we didn't *miss* adding it because the area was excluded initially.
                 # The current logic iterates through controlled_areas *after* filtering.
                 # This means garrisoned cities in rebellious/famine provinces *are* correctly included.
                 pass # Logic seems correct

        # 4. Variable Income (Rule V.B.1.d)
        # Base variable income for own country
        income += finances.get_ducats(self.static_name, die_roll, self.double_income)
        # Variable income for controlled major cities (if applicable per scenario)
        # This requires scenario-specific rules not easily modeled here.
        # Assuming major_city_ids passed in correctly identifies cities eligible for variable roll.
        controlled_major_cities_for_variable = controlled_city_areas.filter(board_area_id__in=major_city_ids)
        for city_area in controlled_major_cities_for_variable:
             # Check scenario rules if this specific city grants a variable roll
             # This might need a flag on Area or CityIncome model, or scenario-specific logic.
             # Example: if self.game.scenario.city_gives_variable_income(city_area.board_area.code):
             # For now, let's assume controlling the major city area grants the roll based on its code.
             income += finances.get_ducats(city_area.board_area.code, die_roll) # Use city code

        # Variable income for conquered home countries (Rule V.B.1.d.3)
        if config.conquering:
            for conquered_player in Player.objects.filter(game=self.game, conqueror=self):
                 if conquered_player.country: # Check if country exists
                      income += finances.get_ducats(conquered_player.static_name, die_roll, conquered_player.double_income)

        return max(0, income) # Ensure income is not negative


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
        # Fetch the unit instance using provided kwargs (e.g., id=unit_id)
        u = self.get_query_set().get(**kwargs)
        # Basic strength is unit's power
        strength = u.power
        u_order = u.get_order() # Get the order for the unit we're calculating strength for

        # --- Calculate Support Strength ---
        support_query = Q(unit__player__game=game, code='S', confirmed=True, subunit=u)

        # Determine the specific action being supported based on the unit's order
        if not u_order or u_order.code in ('H', 'S', 'C', 'B', 'L', '0'): # Holding or non-moving order
            support_query &= Q(subcode='H') # Find orders supporting Hold for this unit
        elif u_order.code == '=': # Conversion
            support_query &= Q(subcode='=', subtype=u_order.type) # Find orders supporting this specific conversion
        elif u_order.code == '-': # Advance
            # Find orders supporting this specific move, including coast
            support_query &= Q(
                subcode='-',
                subdestination=u_order.destination,
                # Match coast only if the destination requires one
                subdestination_coast=u_order.destination_coast if u_order.destination.board_area.has_multiple_coasts() else None
            )
        else:
            # Should not happen if orders are validated, but handle defensively
            support_query = Q(pk__in=[]) # No support for invalid/unhandled order types

        # Sum the 'power' of supporting units
        support_sum = Order.objects.filter(support_query).aggregate(support_power=Sum('unit__power'))
        support_strength = support_sum['support_power'] or 0

        strength += support_strength

        # --- Rebellion Support (Advanced Rule VI.C.5.c.9) ---
        if game.configuration.finances and u_order and u_order.code == '-':
            target_area = u_order.destination
            # Check for rebellion against *another* player in the target area
            rebellion = target_area.has_rebellion(u.player, same=False)
            if rebellion:
                # Check if multiple players are trying to use the same rebellion support
                other_attackers_count = Order.objects.filter(
                    player__game=game, code='-', confirmed=True, destination=target_area
                ).exclude(unit=u).count()
                if other_attackers_count == 0:
                    strength += 1 # Rebellion adds 1 strength if uncontested

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
    # besieging = models.BooleanField(default=False) # UI flag, logic uses siege_stage (REMOVED)
    siege_stage = models.PositiveSmallIntegerField(default=0, help_text="0:Not besieging, 1:Besieging(1st turn), 2:Besieging(2nd turn)") # Added (Rule VIII.C.2)
    must_retreat = models.CharField(max_length=5, blank=True, default='') # Stores code of area attacker came FROM
    placed = models.BooleanField(default=True)
    paid = models.BooleanField(default=True) # Advanced V.B.3
    cost = models.PositiveIntegerField(default=3) # Advanced V.B.3 / Optional IV
    power = models.PositiveIntegerField(default=1) # Optional IV (Base strength)
    loyalty = models.PositiveIntegerField(default=1) # Optional IV / Advanced VI.C.4.g (Bribe resistance)
    # Added coast field, nullable. Choices defined for validation/forms.
    coast = models.CharField(max_length=2, blank=True, null=True, choices=(('nc','NC'),('sc','SC'),('ec','EC'))) # North, South, East

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
        """Returns a description of the unit for the support order dropdown."""
        coast_str = "/{self.coast}" if self.coast else ""
        return _("%(type)s in %(area)s%(coast)s") % {
            'type': self.get_type_display(),
            'area': self.area,
            'coast': coast_str
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
        coast_str = "/{self.coast}" if self.coast else ""
        return _("%(type)s in %(area)s%(coast)s") % {
            'type': self.get_type_display(),
            'area': self.area,
            'coast': coast_str
        }

    def describe_with_cost(self):
        coast_str = "/{self.coast}" if self.coast else ""
        return _("%(type)s in %(area)s%(coast)s (%(cost)s ducats)") % {
            'type': self.get_type_display(),
            'area': self.area,
            'coast': coast_str,
            'cost': self.cost,
        }
    
    def get_possible_retreats(self):
        """ Returns a queryset of GameAreas the unit can retreat to, considering coasts. (Rule VIII.B.6) """
        if not self.must_retreat: # must_retreat stores code of area attacker came FROM
            return GameArea.objects.none()

        possible_areas_ids = set()
        board_area = self.area.board_area
        game = self.player.game

        # Get potential adjacent areas based on basic borders
        potential_retreats_qs = GameArea.objects.filter(
            game=game,
            board_area__borders=board_area,
            standoff=False # Cannot retreat to standoff (Rule VIII.B.6.c.1)
        ).exclude(
            board_area__code=self.must_retreat # Cannot retreat where attacker came from (Rule VIII.B.6.c.2)
        ).exclude(
            unit__type__in=['A', 'F'] # Cannot retreat where another A/F unit is
        ).select_related('board_area') # Optimize

        for dest_ga in potential_retreats_qs:
            # Check adjacency rules considering unit type and coasts
            # Rule VIII.B.6.a: Retreat into area it could ordinarily advance into (without transport)
            if board_area.is_adjacent(dest_ga.board_area,
                                      fleet=(self.type == 'F'),
                                      source_unit_coast=self.coast): # Pass unit's current coast
                # Rule VIII.B.6.b: Fleet cannot retreat inland, Army cannot retreat to sea
                if self.type == 'F' and not dest_ga.board_area.is_sea and not dest_ga.board_area.is_coast:
                     continue
                if self.type == 'A' and dest_ga.board_area.is_sea:
                     continue
                possible_areas_ids.add(dest_ga.id)

        # Option to convert to Garrison (Rule VIII.B.6.d)
        can_convert_to_garrison = False
        if board_area.is_fortified and board_area.accepts_type('G'):
            # Check if city/fortress is unoccupied by another garrison
            if not Unit.objects.filter(area=self.area, type='G').exclude(id=self.id).exists():
                # Check for rebellion in city/fortress
                rebellion = self.area.has_rebellion(self.player, same=True) # Check for rebellion against self
                if not rebellion or not rebellion.garrisoned:
                    # Fleet needs port to retreat into garrison spot (Rule VIII.B.6.b implies)
                    if self.type == 'A' or (self.type == 'F' and board_area.has_port):
                         can_convert_to_garrison = True

        # If no other retreats available, conversion is the only option (represented by current area)
        if not possible_areas_ids and can_convert_to_garrison:
            possible_areas_ids.add(self.area.id)
        # If other retreats exist, still offer conversion as an option
        elif can_convert_to_garrison:
            possible_areas_ids.add(self.area.id)

        return GameArea.objects.filter(id__in=list(possible_areas_ids)).select_related('board_area')

    def invade_area(self, ga, target_coast=None): # Add target_coast parameter
        """ Moves unit to a new area after successful advance/conversion. """
        if signals: signals.unit_moved.send(sender=self, destination=ga)
        old_area_code = self.area.board_area.code
        self.area = ga
        # Set coast based on destination and unit type
        if ga.board_area.has_multiple_coasts() and self.type == 'F':
            self.coast = target_coast # Use the specified target coast from the order
            if not self.coast:
                # Log error if fleet moves to multi-coast without specifying
                if logging: logging.error("Fleet {self.id} moved to multi-coast {ga.board_area.code} without target_coast!")
                # Default to first available coast? Or clear? Clearing is safer.
                self.coast = None
        else:
            self.coast = None # Clear coast if not a fleet or not multi-coast dest

        self.must_retreat = '' # Successful move clears retreat status
        self.siege_stage = 0 # Moving resets siege
        # self.besieging = False # Removed field
        self.save()
        if logging: logging.info("Unit {self.id} ({self.type}) moved from {old_area_code} to {ga.board_area.code}{'/' + self.coast if self.coast else ''}")
        self.check_rebellion() # Check for liberating rebellion

    def retreat(self, destination, target_coast=None): # Add target_coast parameter
        """ Moves unit after retreat order, handles conversion option. """
        if self.area == destination: # Retreating into own city/fortress (Conversion - Rule VIII.B.6.d)
            if signals: signals.unit_converted.send(sender=self, before=self.type, after='G', context="retreat")
            if logging: logging.info("Unit {self.id} ({self.type}) retreats by converting to Garrison in {self.area.board_area.code}")
            self.type = 'G'
            self.coast = None # Garrisons don't have coasts
            self.siege_stage = 0
            # self.besieging = False # Removed field
            self.must_retreat = ''
            self.save()
            # No rebellion check needed when converting to G
        else: # Retreating to adjacent area
            if signals: signals.unit_retreated.send(sender=self, destination=destination)
            old_area_code = self.area.board_area.code
            self.area = destination
            # Set coast if retreating to a multi-coast province
            if destination.board_area.has_multiple_coasts() and self.type == 'F':
                self.coast = target_coast # Use specified coast from RetreatOrder
                if not self.coast:
                     if logging: logging.error("Fleet {self.id} retreated to multi-coast {destination.board_area.code} without target_coast specified!")
                     self.coast = None # Clear coast if invalid
            else:
                self.coast = None # Clear coast otherwise

            self.must_retreat = '' # Successful retreat clears status
            self.save()
            if logging: logging.info("Unit {self.id} ({self.type}) retreated from {old_area_code} to {destination.board_area.code}{'/' + self.coast if self.coast else ''}")
            self.check_rebellion() # Check for liberating rebellion


    def convert(self, new_type):
        """ Executes a conversion order, checking rules. (Rule VII.B.7) """
        # Rule VII.B.7.h: Besieged Garrison may not convert.
        # Check if *another* unit is besieging this garrison's area
        if self.type == 'G' and Unit.objects.filter(area=self.area, siege_stage__gt=0).exclude(id=self.id).exists():
             if logging: logging.info("Conversion failed: Garrison {self.id} in {self.area.board_area.code} is besieged.")
             # Order fails, unit holds implicitly. Delete the order? Adjudication loop might handle this.
             return # Stop the conversion

        # Check if conversion is valid (redundant with Order.is_possible but good defense)
        board_area = self.area.board_area
        valid = False
        if board_area.is_fortified: # Rule VII.B.7.a
            if self.type == 'G': # G -> A or F
                if new_type == 'A': valid = True
                elif new_type == 'F' and board_area.has_port: valid = True # Rule VII.B.7.c
            elif new_type == 'G': # A/F -> G
                if self.type == 'A': valid = True
                elif self.type == 'F' and board_area.has_port: valid = True # Rule VII.B.7.b implies fleet needs port
                # Check if city already occupied by another Garrison
                if Unit.objects.filter(area=self.area, type='G').exclude(id=self.id).exists(): valid = False
            # Direct A<->F disallowed (Rule VII.B.7.d)

        if not valid:
             if logging: logging.warning("Invalid conversion attempt: {self.id} ({self.type}) to {new_type} in {board_area.code}.")
             # Order fails, unit holds implicitly.
             return

        if signals: signals.unit_converted.send(sender=self, before=self.type, after=new_type)
        if logging: logging.info("Unit {self.id} converting from {self.type} to {new_type} in {board_area.code}")

        old_type = self.type
        self.type = new_type
        # Rule VIII.B.6.f suggests conversion happens, *then* retreat if forced.
        # Do not clear must_retreat here.
        self.siege_stage = 0 # Reset siege status on conversion
        # self.besieging = False # Removed field

        # Handle coast attribute based on the NEW type and area
        if new_type == 'G':
            self.coast = None # Garrisons don't have coasts
        elif not board_area.has_multiple_coasts():
            self.coast = None # Clear coast if area is not multi-coastal
        else: # Converting A->F or F->A in a multi-coast area
            # Rule VII.B.7.b/c implies the new unit is placed 'in the province'.
            # It doesn't specify which coast. Clearing seems safest.
            self.coast = None

        self.save() # Save all changes made during conversion

        # If converting *out* of Garrison into A/F, check for liberating rebellion
        if old_type == 'G' and new_type != 'G':
            self.check_rebellion() # Liberate rebellion if present (Rule VI.C.5.c.8)

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
    # Destination for Advance, target area for Besiege/Lift Siege (unit's area), target area for Support Hold/Move
    destination = models.ForeignKey(GameArea, blank=True, null=True, related_name='targeted_by_orders')
    # Type for Conversion (=) or Support Conversion (S =)
    type = models.CharField(max_length=1, blank=True, null=True, choices=UNIT_TYPES)
    # Subunit for Support (S) or Convoy (C)
    subunit = models.ForeignKey(Unit, related_name='affecting_orders', blank=True, null=True)
    # Subcode for Support (S): H, -, =
    subcode = models.CharField(max_length=1, choices=ORDER_SUBCODES, blank=True, null=True)
    # Subdestination for Support Advance (S -) or Convoy (C -)
    subdestination = models.ForeignKey(GameArea, related_name='sub_targeted_by_orders', blank=True, null=True)
    # Subtype for Support Conversion (S =)
    subtype = models.CharField(max_length=1, blank=True, null=True, choices=UNIT_TYPES)
    confirmed = models.BooleanField(default=False)
    player = models.ForeignKey(Player, null=True) # Tracks who issued the order (can differ from unit.player if bought)
    # Coast specifiers
    destination_coast = models.CharField(max_length=2, blank=True, null=True, choices=(('nc','NC'),('sc','SC'),('ec','EC')))
    subdestination_coast = models.CharField(max_length=2, blank=True, null=True, choices=(('nc','NC'),('sc','SC'),('ec','EC')))

    class Meta:
        # Ensure only one confirmed order per unit per turn (player check removed as bribes allow ordering others)
        # unique_together = (('unit', 'player'),) # Removed player constraint
        unique_together = (('unit', 'confirmed'),) # Allow multiple unconfirmed, only one confirmed

    # ... (as_dict method - unchanged) ...

    def explain(self):
        """ Returns a human readable order, including coasts. """
        unit_str = "{self.unit}" # Uses Unit.__unicode__ which includes coast
        dest_coast_str = "/{self.destination_coast}" if self.destination_coast else ""
        subdest_coast_str = "/{self.subdestination_coast}" if self.subdestination_coast else ""

        if self.code == 'H': msg = _("%(unit)s holds.") % {'unit': unit_str}
        elif self.code == '0': msg = _("%(unit)s disbands.") % {'unit': unit_str}
        elif self.code == 'L': msg = _("%(unit)s lifts siege.") % {'unit': unit_str}
        elif self.code == '-': msg = _("%(unit)s -> %(area)s%(coast)s.") % {'unit': unit_str, 'area': self.destination, 'coast': dest_coast_str}
        elif self.code == 'B': msg = _("%(unit)s besieges.") % {'unit': unit_str}
        elif self.code == '=': msg = _("%(unit)s converts to %(type)s.") % {'unit': unit_str, 'type': self.get_type_display()}
        elif self.code == 'C':
            subunit_str = "{self.subunit}" # Includes subunit coast
            msg = _("%(unit)s C %(subunit)s -> %(area)s%(coast)s.") % {'unit': unit_str, 'subunit': subunit_str, 'area': self.subdestination, 'coast': subdest_coast_str}
        elif self.code == 'S':
            subunit_str = "{self.subunit}" # Includes subunit coast
            if self.subcode == 'H': msg = _("%(unit)s S %(subunit)s H.") % {'unit': unit_str, 'subunit': subunit_str}
            elif self.subcode == '-': msg = _("%(unit)s S %(subunit)s -> %(area)s%(coast)s.") % {'unit': unit_str, 'subunit': subunit_str, 'area': self.subdestination, 'coast': subdest_coast_str}
            # elif self.subcode == '=': msg = _("%(unit)s S %(subunit)s = %(type)s.") % {'unit': unit_str, 'subunit': subunit_str, 'type': self.get_subtype_display()} # Support conversion?
            else: msg = _("%(unit)s supports %(subunit)s (unknown action).") % {'unit': unit_str, 'subunit': subunit_str}
        else: msg = _("Unknown order for %(unit)s.") % {'unit': unit_str}
        return msg

    # ... (confirm method - unchanged) ...
    # ... (format_suborder method - unchanged) ...

    def format(self):
        """ Returns abbreviated order string, including coasts. """
        # Get unit representation including coast
        f = "{self.unit.type} {self.unit.area.board_area.code}"
        if self.unit.coast: f += "/{self.unit.coast}"

        f += " {self.code}" # Add the order code

        if self.code == '-':
            f += " {self.destination.board_area.code}"
            if self.destination_coast: f += "/{self.destination_coast}"
        elif self.code == '=':
            f += " {self.type}"
        elif self.code in ['S', 'C']:
            # Get subunit representation including coast
            sub_f = "{self.subunit.type} {self.subunit.area.board_area.code}"
            if self.subunit.coast: sub_f += "/{self.subunit.coast}"

            if self.code == 'S':
                sub_f += " {self.subcode or 'H'}" # Default subcode to H if None
                if self.subcode == '-':
                    sub_f += " {self.subdestination.board_area.code}"
                    if self.subdestination_coast: sub_f += "/{self.subdestination_coast}"
                # elif self.subcode == '=': sub_f += " {self.subtype}" # Support conversion?
            elif self.code == 'C':
                sub_f += " - {self.subdestination.board_area.code}" # Convoy implies move (-)
                if self.subdestination_coast: sub_f += "/{self.subdestination_coast}"
            f += " {sub_f}"
        # Codes H, B, L, 0 require no further parts
        return f


    def find_convoy_line(self):
        """
        Checks if a valid, contiguous convoy path exists for an Army Advance order.
        Uses BFS and considers coasts, rules VII.B.6, VII.D.1, VII.D.2.
        Returns True if a valid path exists, False otherwise.
        """
        # --- 1. Initial Checks ---
        if not (self.code == '-' and self.unit and self.unit.type == 'A'):
            return False # Only for Army Advance orders
        if not self.destination:
            return False # Needs a destination

        army = self.unit
        start_area = army.area
        target_area = self.destination
        target_coast = self.destination_coast
        game = army.player.game

        if not start_area.board_area.is_coast or not target_area.board_area.is_coast:
            return False # Army start and end must be coastal

        # Validate target coast if required
        if target_area.board_area.has_multiple_coasts():
            if not target_coast or target_coast not in target_area.board_area.get_coast_list():
                 if logging: logging.warning("Convoy Check Fail: Invalid/missing target coast '{target_coast}' for multi-coast destination {target_area.board_area.code}")
                 return False
        elif target_coast:
             if logging: logging.warning("Convoy Check Fail: Target coast '{target_coast}' specified for single-coast destination {target_area.board_area.code}")
             return False # Cannot specify coast for single coast dest

        # --- 2. Pre-fetch Potential Convoying Fleets ---
        # Fleets must have the correct confirmed C order targeting this army and destination/coast
        convoy_orders = Order.objects.filter(
            code='C',
            confirmed=True,
            subunit=army,
            subdestination=target_area,
            subdestination_coast=target_coast, # Match target coast exactly
            unit__player__game=game, # Fleet must be in the same game
            unit__type='F' # Must be a fleet
        ).filter(
            # Fleet must be in a Sea or Venice Lagoon (Rule VII.B.6.b implies chain uses seas)
            Q(unit__area__board_area__is_sea=True) | Q(unit__area__board_area__code='VEN')
        ).select_related('unit', 'unit__area', 'unit__area__board_area') # Optimize

        # Create a map of Area ID -> Convoying Fleet Unit for quick lookup
        convoy_fleet_map = {order.unit.area_id: order.unit for order in convoy_orders}
        convoy_area_ids = set(convoy_fleet_map.keys())

        if not convoy_area_ids:
            return False # No fleets ordered to perform this specific convoy

        # --- 3. BFS Initialization ---
        queue = collections.deque()
        visited = set() # Store visited GameArea IDs

        # Find starting fleets adjacent to the army's start area
        possible_first_fleets = GameArea.objects.filter(
            game=game,
            id__in=convoy_area_ids, # Must be one of the convoying fleets
            board_area__borders=start_area.board_area # Must border army's area
        )

        for fleet_area in possible_first_fleets:
            fleet_unit = convoy_fleet_map.get(fleet_area.id)
            if not fleet_unit: continue # Should not happen

            # Check coast-aware adjacency: Army Area <-> First Fleet Area
            if start_area.board_area.is_adjacent(fleet_area.board_area,
                                                 fleet=True, # Check as if fleet moving from sea to coast
                                                 source_unit_coast=fleet_unit.coast, # Fleet's coast (if any)
                                                 target_order_coast=army.coast): # Army's coast
                if fleet_area.id not in visited:
                    # Check for strait blockage on the first link
                    if not is_strait_blocked(start_area.board_area.code, fleet_area.board_area.code, game, army.player):
                        visited.add(fleet_area.id)
                        queue.append(fleet_area)

        # --- 4. BFS Loop ---
        while queue:
            current_area = queue.popleft()
            current_fleet = convoy_fleet_map.get(current_area.id)
            if not current_fleet: continue # Should not happen

            # ** Check Final Link (Rule VII.B.6.d) **
            # Is the current fleet's area adjacent to the army's final destination/coast?
            if current_area.board_area.is_adjacent(target_area.board_area,
                                                   fleet=True,
                                                   source_unit_coast=current_fleet.coast,
                                                   target_order_coast=target_coast):
                # Check for strait blockage on the final link
                if not is_strait_blocked(current_area.board_area.code, target_area.board_area.code, game, army.player):
                    return True # Valid path found!

            # ** Explore Neighbors for Chain Extension **
            neighbors = GameArea.objects.filter(
                game=game,
                board_area__borders=current_area.board_area
            ).select_related('board_area') # Optimize

            for neighbor in neighbors:
                if neighbor.id in visited:
                    continue # Already processed

                # Is the neighbor part of the convoy chain?
                if neighbor.id in convoy_area_ids:
                    next_fleet = convoy_fleet_map.get(neighbor.id)
                    if not next_fleet: continue

                    # Check coast-aware adjacency: Current Fleet Area <-> Next Fleet Area
                    if current_area.board_area.is_adjacent(neighbor.board_area,
                                                           fleet=True,
                                                           source_unit_coast=current_fleet.coast,
                                                           target_order_coast=next_fleet.coast):
                        # Check for strait blockage between fleets
                        if not is_strait_blocked(current_area.board_area.code, neighbor.board_area.code, game, army.player):
                            visited.add(neighbor.id)
                            queue.append(neighbor)

        # --- 5. No Path Found ---
        return False

    def get_attacked_area(self):
        """ Returns the game area being targeted by this order (for conflict resolution). """
        if self.code == '-':
            return self.destination
        elif self.code == '=' and self.type in ['A', 'F']: # Conversion G->A/F attacks the province
            return self.unit.area
        # Other orders don't directly attack/enter a new area in the same way
        return None

    def is_possible(self):
        """ Checks if an Order is possible based on rules, including coasts. """
        unit = self.unit
        area = unit.area
        board_area = area.board_area

        # --- Basic Type/State Checks ---
        if self.code == '-': # Advance
            if unit.type not in ['A', 'F']: return False
            if unit.siege_stage > 0: return False # Rule VII.B.4
            if not self.destination: return False
        elif self.code == 'B': # Besiege
            if unit.type not in ['A', 'F']: return False
            if not board_area.is_fortified: return False
            if unit.type == 'F' and not board_area.has_port: return False # Rule VII.B.2.a
            # Check target validity (enemy G or garrisoned R) is complex here, better handled in resolve_sieges
            if unit.siege_stage == 2: return False # Already at max stage
        elif self.code == 'L': # Lift Siege
            if unit.type not in ['A', 'F']: return False
            if unit.siege_stage == 0: return False # Rule VII.B.4
        elif self.code == '=': # Conversion
            if not board_area.is_fortified: return False # Rule VII.B.7.a
            if not self.type: return False
            if unit.type == self.type: return False # Must be different type
            # Rule VII.B.7.h: Besieged Garrison may not convert. Check if *another* unit is besieging.
            if unit.type == 'G' and Unit.objects.filter(area=area, siege_stage__gt=0).exclude(id=unit.id).exists(): return False
            # Type specific conversion rules (Rule VII.B.7.b/c)
            if unit.type == 'G': # G -> A or F
                 if self.type not in ['A', 'F']: return False
                 if self.type == 'F' and not board_area.has_port: return False
            elif self.type == 'G': # A/F -> G
                 if unit.type not in ['A', 'F']: return False # Should not happen
                 # Fleet needs port to convert to G? Rule VII.B.7.b implies yes.
                 if unit.type == 'F' and not board_area.has_port: return False
                 # Check if city already occupied by another Garrison (Rule VII.B.1.b)
                 if Unit.objects.filter(area=area, type='G').exclude(id=unit.id).exists(): return False
            else: # A->F or F->A not allowed directly (Rule VII.B.7.d)
                 return False
        elif self.code == 'C': # Convoy
            if unit.type != 'F': return False # Rule VII.B.6
            if not self.subunit or self.subunit.type != 'A': return False # Rule VII.B.6.a
            if not self.subdestination: return False
            # Rule VII.B.6.b: Fleet must remain in place (sea or coastal province)
            # Rule VII.B.6.d: Fleet can only transport into provinces it could move to.
            if not board_area.is_sea and not board_area.is_coast: return False # Must be in sea/coast
            if not self.subunit.area.board_area.is_coast: return False # Army must be on coast
            if not self.subdestination.board_area.is_coast: return False # Destination must be coast
            # Check basic adjacency for fleet->army and fleet->destination
            if not board_area.is_adjacent(self.subunit.area.board_area, fleet=True, source_unit_coast=unit.coast, target_order_coast=self.subunit.coast): return False
            if not board_area.is_adjacent(self.subdestination.board_area, fleet=True, source_unit_coast=unit.coast, target_order_coast=self.subdestination_coast): return False
            # Full path check (find_convoy_line) is complex, rely on basic adjacency for now.
        elif self.code == 'S': # Support
            if not self.subunit: return False
            # Determine target area of support
            support_target_area = None
            support_target_coast = None
            if self.subcode == 'H': support_target_area = self.subunit.area; support_target_coast = self.subunit.coast
            elif self.subcode == '-': support_target_area = self.subdestination; support_target_coast = self.subdestination_coast
            # elif self.subcode == '=': support_target_area = self.subunit.area # Support conversion? Rule VII.B.5 doesn't explicitly allow/disallow. Assume disallowed for now.
            else: return False # Invalid subcode

            if not support_target_area: return False
            # Check if supporter can reach the target area/coast (Rule VII.B.5.a)
            if not board_area.is_adjacent(support_target_area.board_area,
                                          fleet=(unit.type == 'F'),
                                          source_unit_coast=unit.coast,
                                          target_order_coast=support_target_coast):
                return False
        elif self.code == '0': return True # Disband always possible
        elif self.code == 'H': return True # Hold always possible
        else: return False # Unknown code

        # --- Adjacency Check for Advance ---
        if self.code == '-':
            if not board_area.is_adjacent(self.destination.board_area,
                                          fleet=(unit.type == 'F'),
                                          source_unit_coast=unit.coast,
                                          target_order_coast=self.destination_coast):
                 # If not directly adjacent, check if it's a valid convoy move
                 if not (unit.type == 'A' and board_area.is_coast and self.destination.board_area.is_coast):
                     return False # Only coastal armies can be convoyed
                 # Basic check: Is *any* fleet ordered to convoy this unit to this dest?
                 # More robust check would use find_convoy_line.
                 if not Order.objects.filter(code='C', confirmed=True, subunit=unit, subdestination=self.destination, subdestination_coast=self.destination_coast).exists():
                      return False # No convoy order found

        # --- Coast Specifier Validation ---
        # Check destination coast
        if self.destination:
            if self.destination.board_area.has_multiple_coasts():
                # If fleet moving or army being convoyed to multi-coast, coast MUST be specified
                if (unit.type == 'F' or self.code == 'C') and (not self.destination_coast or self.destination_coast not in self.destination.board_area.get_coast_list()):
                    return False # Invalid or missing coast for multi-coast destination
            elif self.destination_coast:
                return False # Cannot specify coast for single-coast destination

        # Check subdestination coast (for Support Move or Convoy)
        if self.subdestination:
            if self.subdestination.board_area.has_multiple_coasts():
                 # If supporting a fleet move or convoying an army to multi-coast, coast MUST be specified
                 if (self.code == 'C' or (self.code == 'S' and self.subcode == '-' and self.subunit.type == 'F')) and \
                    (not self.subdestination_coast or self.subdestination_coast not in self.subdestination.board_area.get_coast_list()):
                     return False
            elif self.subdestination_coast:
                 return False

        return True # Order seems possible based on these checks

    def __unicode__(self):
        return self.format()

class RetreatOrder(models.Model):
    """ Defines the area where the unit must try to retreat. If ``area`` is
    blank, the unit will be disbanded.
    """
    unit = models.ForeignKey(Unit)
    area = models.ForeignKey(GameArea, null=True, blank=True)
    # New field for target coast
    coast = models.CharField(max_length=2, blank=True, null=True, choices=(('nc','NC'),('sc','SC'),('ec','EC')))

    def __unicode__(self):
        coast_str = "/{self.coast}" if self.coast else ""
        # Use unit's __unicode__ which includes its current location/coast
        unit_str = "{self.unit}"
        dest_str = "{self.area}{coast_str}" if self.area else "Disband"
        return "{unit_str} Retreat -> {dest_str}"
    
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
    """ Defines the configuration options for each game. """
    game = models.OneToOneField('Game', verbose_name=_('game'), editable=False) # Assuming Game model is defined above

    # Existing Flags
    finances = models.BooleanField(_('finances'), default=False)
    assassinations = models.BooleanField(_('assassinations'), default=False,
                    help_text=_('will enable Finances'))
    bribes = models.BooleanField(_('bribes'), default=False,
                    help_text=_('will enable Finances'))
    excommunication = models.BooleanField(_('excommunication'), default=False)
    special_units = models.BooleanField(_('special units'), default=False,
                    help_text=_('will enable Finances'))
    strategic = models.BooleanField(_('strategic movement'), default=False) # Assuming this exists
    lenders = models.BooleanField(_('money lenders'), default=False,
                    help_text=_('will enable Finances'))
    unbalanced_loans = models.BooleanField(_('unbalanced loans'), default=False,
        help_text=_('the credit for all players will be 25d'))
    conquering = models.BooleanField(_('conquering'), default=False)
    famine = models.BooleanField(_('famine'), default=False)
    plague = models.BooleanField(_('plague'), default=False)
    storms = models.BooleanField(_('storms'), default=False)
    gossip = models.BooleanField(_('gossip'), default=False) # Assuming this exists

    # --- New Optional Rule Flags ---
    bribes_via_ally = models.BooleanField(_('Bribes via Ally (Opt V.A)'), default=False,
                        help_text=_("Allow bribes adjacent to ally units (permission not enforced)."))
    bribes_anywhere = models.BooleanField(_('Bribes Anywhere (Opt V.B)'), default=False,
                        help_text=_("Allow bribes into any province, ignoring adjacency."))
    random_assassins = models.BooleanField(_('Random Assassin Setup (Opt VI.B)'), default=False,
                        help_text=_("Use random draw for initial assassin tokens instead of standard."))
    no_luck = models.BooleanField(_('No Luck Option (Opt IX)'), default=False,
                        help_text=_("Disable dice rolls (fixed income, no assassination/disasters)."))
    # --- End New Flags ---

    def __unicode__(self):
        return unicode(self.game)

    def get_enabled_rules(self):
        rules = []
        # Iterate through fields, check if BooleanField and True
        for f in self._meta.fields:
            if isinstance(f, models.BooleanField) and f.name != 'id': # Exclude 'id'
                # Use getattr for safety, check if value is True
                if getattr(self, f.name, False):
                    rules.append(unicode(f.verbose_name)) # Use verbose_name
        return rules

def create_configuration(sender, instance, created, **kwargs):
    if isinstance(instance, Game) and created:
        config = Configuration(game=instance)
        config.save()

models.signals.post_save.connect(create_configuration, sender=Game)

###
### EXPENSES (Advanced Rule VI)
###

EXPENSE_TYPES = (
    (0, _("Famine relief")),           # Rule VI.C.1
    (1, _("Pacify rebellion")),        # Rule VI.C.2
    (2, _("Conquered province to rebel")), # Rule VI.C.5.a
    (3, _("Home province to rebel")),    # Rule VI.C.5.b
    (4, _("Counter bribe")),           # Rule VI.C.3
    # Bribes (Rule VI.C.4)
    (5, _("Disband autonomous garrison")), # D
    (6, _("Buy autonomous garrison")),     # E
    (7, _("Committed garrison to autonomous")),# F
    (8, _("Disband committed garrison")),   # G (Changed from Disband enemy unit)
    (9, _("Disband army or fleet")),      # H
    (10, _("Buy army or fleet")),         # I (Changed from Buy enemy unit)
    # Assassination is handled separately by Assassination model
)

# Base costs from Rule VI.C
EXPENSE_COST = {
    0: 3,   # Famine relief
    1: 12,  # Pacify rebellion
    2: 9,   # Conquered rebel
    3: 15,  # Home rebel
    4: 3,   # Counter bribe (minimum)
    5: 6,   # Disband auto G (minimum)
    6: 9,   # Buy auto G (minimum)
    7: 9,   # Commit G -> Auto (minimum)
    8: 12,  # Disband commit G (minimum)
    9: 12,  # Disband A/F (minimum)
    10: 18, # Buy A/F (minimum)
}

def get_expense_cost(type, unit=None):
    """ Calculates the minimum cost for an expense, considering unit loyalty and major cities. """
    if type not in EXPENSE_COST:
        raise ValueError("Invalid expense type")

    base_cost = EXPENSE_COST[type]
    multiplier = 1
    loyalty_factor = 1 # Default for non-bribes or loyalty 1 units

    # Bribes targeting a specific unit (Types 5-10)
    if type in (5, 6, 7, 8, 9, 10):
        if not isinstance(unit, Unit):
            # Counter-bribe (type 4) also targets a unit, but cost is variable >= 3
            if type != 4:
                 raise ValueError("Unit required for bribe cost calculation")

        if unit: # Check if unit is provided (might be None for type 4 initially)
            # Optional Rule IV: Special unit loyalty affects bribe cost
            # Assuming loyalty > 1 doubles the cost (Rule doesn't specify exact mechanism)
            if unit.loyalty > 1:
                loyalty_factor = 2 # Example: Double cost for higher loyalty

            # Rule VI.C.4.g.3: Double cost for Garrisons in major cities
            if unit.type == 'G':
                area_board = unit.area.board_area
                # Check if the area itself has major city income OR if it's linked via CityIncome model
                is_major = (area_board.major_city_income is not None and area_board.major_city_income > 1)
                # Fallback check using CityIncome model if needed (assuming it links scenario+city)
                # is_major = is_major or CityIncome.objects.filter(city=area_board, scenario=unit.player.game.scenario).exists()
                if is_major:
                    multiplier = 2

    # Counter-bribe cost is minimum 3, but can be increased in multiples of 3 (handled by form)
    if type == 4:
        return base_cost # Minimum is 3

    # Apply multipliers for final minimum cost
    return base_cost * multiplier * loyalty_factor

class Expense(models.Model):
    """ A player may expend ducats to affect some units or areas in the game. """
    player = models.ForeignKey(Player)
    ducats = models.PositiveIntegerField(default=0)
    type = models.PositiveIntegerField(choices=EXPENSE_TYPES)
    area = models.ForeignKey(GameArea, null=True, blank=True) # Target for types 0, 1, 2, 3
    unit = models.ForeignKey(Unit, null=True, blank=True) # Target for types 4, 5, 6, 7, 8, 9, 10
    # Added field for 'Buy' bribes to specify resulting unit type/ID - complex, handle in view/processing for now
    # new_unit_id = models.PositiveIntegerField(null=True, blank=True) # Example
    confirmed = models.BooleanField(default=False) # Mark true when player confirms actions

    def save(self, *args, **kwargs):
        # Basic validation based on type
        if self.type in (0, 1, 2, 3): # Famine Relief, Pacify, Rebel
            if not self.area: raise ValidationError("Expense type requires an area.")
            self.unit = None # Ensure unit is None
        elif self.type in (4, 5, 6, 7, 8, 9, 10): # Counter-Bribe, Bribes
            if not self.unit: raise ValidationError("Expense type requires a unit.")
            self.area = None # Ensure area is None
        else:
            raise ValidationError("Unknown expense type {self.type}")

        # Ensure ducats meet minimum cost (can be overridden by form validation)
        try:
            min_cost = get_expense_cost(self.type, self.unit)
            if self.ducats < min_cost:
                 # Allow saving if unconfirmed (form handles validation), but log warning
                 if self.confirmed:
                      raise ValidationError("Ducats ({self.ducats}) is less than minimum cost ({min_cost}) for confirmed expense.")
                 # else: print("Warning: Unconfirmed expense ducats {self.ducats} < min {min_cost}")
        except ValueError as e:
             raise ValidationError(str(e))

        super(Expense, self).save(*args, **kwargs)
        # Logging moved to view upon successful form save

    def __unicode__(self):
        # Use explain method for user-facing description
        return self.explain()

    def explain(self):
        """ Provides a user-readable explanation of the expense. """
        data = {
            'player': self.player.country if self.player.country else 'Unknown',
            'ducats': self.ducats,
            'area': self.area,
            'unit': self.unit,
        }
        messages = {
            0: _("%(ducats)sd: %(player)s reliefs famine in %(area)s"),
            1: _("%(ducats)sd: %(player)s pacifies rebellion in %(area)s"),
            2: _("%(ducats)sd: %(player)s promotes rebellion (conquered) in %(area)s"),
            3: _("%(ducats)sd: %(player)s promotes rebellion (home) in %(area)s"),
            4: _("%(ducats)sd: %(player)s counter-bribes %(unit)s"),
            5: _("%(ducats)sd: %(player)s bribes to disband %(unit)s (Auto G)"),
            6: _("%(ducats)sd: %(player)s bribes to buy %(unit)s (Auto G)"),
            7: _("%(ducats)sd: %(player)s bribes %(unit)s (Commit G) to become Autonomous"),
            8: _("%(ducats)sd: %(player)s bribes to disband %(unit)s (Commit G)"),
            9: _("%(ducats)sd: %(player)s bribes to disband %(unit)s (A/F)"),
            10: _("%(ducats)sd: %(player)s bribes to buy %(unit)s (A/F)"),
        }
        try:
            return messages[self.type] % data
        except KeyError:
            return "Unknown expense type {self.type}"

    def is_bribe(self):
        """ Checks if the expense type is a bribe (Rule VI.C.4). """
        return self.type in (5, 6, 7, 8, 9, 10)

    def is_counter_bribe(self):
        return self.type == 4

    def is_rebellion_action(self):
        return self.type in (1, 2, 3)

    def undo(self):
        """ Deletes the expense and returns the money to the player (if unconfirmed). """
        if self.confirmed:
             if logging: logging.warning("Attempted to undo confirmed expense {self.id}")
             return False # Cannot undo confirmed expense

        # Refund ducats using F expression
        Player.objects.filter(id=self.player.id).update(ducats=F('ducats') + self.ducats)

        if logging: logging.info("Undoing expense {self.id} ({self.explain()}). Refunding {self.ducats}d to {self.player}.")
        self.delete()
        return True
    

class Rebellion(models.Model):
    """
    A Rebellion may be placed in a GameArea if finances rules are applied.
    Rebellion.player is the player who controlled the GameArea when the
    Rebellion was placed. Rebellion.garrisoned is True if the Rebellion is
    in a fortified city/fortress. (Rule VI.C.5)
    """
    area = models.OneToOneField(GameArea, unique=True) # Only one rebellion per area
    player = models.ForeignKey(Player) # Player the rebellion is AGAINST
    garrisoned = models.BooleanField(default=False) # True if in city/fortress

    def __unicode__(self):
        loc = _("in city") if self.garrisoned else _("in province")
        return _("Rebellion %(loc)s %(area)s against %(player)s") % {
            'loc': loc,
            'area': self.area.board_area.code, # Use code for brevity
            'player': self.player.country if self.player.country else 'Unknown'
        }

    def save(self, *args, **kwargs):
        # Ensure area is valid for rebellion
        if self.area.board_area.is_sea:
            raise ValidationError("Cannot place rebellion in a sea area.")
        # Rule VI.C.5.c.11: No Rebellion unit may be placed in Venice if occupied
        if self.area.board_area.code == 'VEN' and self.area.unit_set.exists():
             raise ValidationError("Cannot place rebellion in occupied Venice.")

        # Determine player the rebellion is against (current controller)
        # This should be set by the view/logic creating the rebellion based on Expense target
        if not self.player_id: # If player not set, try to get current controller
             if self.area.player:
                  self.player = self.area.player
             else:
                  raise ValidationError("Cannot determine which player the rebellion is against.")

        # Determine if rebellion is garrisoned (Rule VI.C.5)
        if self.area.board_area.is_fortified:
            # Place in city/fortress if no garrison unit is present
            if not self.area.unit_set.filter(type='G').exists():
                self.garrisoned = True
            else:
                self.garrisoned = False # Place in province if city occupied
        else:
             self.garrisoned = False # Cannot be garrisoned if not fortified

        super(Rebellion, self).save(*args, **kwargs)
        if signals:
            # Pass the player who *caused* the rebellion if known? Signal doesn't support it yet.
            signals.rebellion_started.send(sender=self.area)
        if logging: logging.info("Rebellion started: {self}")

    def get_strength(self):
        """ Returns strength for supporting attacks (Rule VI.C.5.c.9). """
        return 1

class Loan(models.Model):
    """ A Loan describes a quantity of money that a player borrows from the bank,
        with a term and interest. (Optional Rule X) """
    player = models.OneToOneField(Player) # Player can only have one loan at a time? Rule X.A.1 implies limit on total owed. Let's allow multiple loans but track total.
    # player = models.ForeignKey(Player) # Allow multiple loans? Let's stick to OneToOne for simplicity first.
    principal = models.PositiveIntegerField(default=0) # Amount borrowed
    interest_rate = models.FloatField(default=0.0) # e.g., 0.20 or 0.50
    debt = models.PositiveIntegerField(default=0) # Total amount to repay (principal + interest)
    due_season = models.PositiveIntegerField(choices=SEASONS)
    due_year = models.PositiveIntegerField(default=0)

    def __unicode__(self):
        return _("%(player)s owes %(debt)s ducats by %(season)s, %(year)s") % {
            'player': self.player.country if self.player.country else 'Unknown',
            'debt': self.debt,
            'season': self.get_due_season_display(),
            'year': self.due_year,
        }

    def is_due(self, current_year, current_season):
        """ Checks if the loan is due or overdue. """
        if current_year > self.due_year:
            return True
        if current_year == self.due_year and current_season >= self.due_season:
            return True
        return False

class Assassin(models.Model):
    """ An Assassin represents a counter that a Player owns, to potentially murder
        the leader of another country. (Advanced Rule III / Optional VI) """
    owner = models.ForeignKey(Player, related_name='assassin_set') # Use related_name
    target = models.ForeignKey(Country) # Target is a Country

    class Meta:
        unique_together = (('owner', 'target'),) # Player has only one token per target

    def __unicode__(self):
        owner_name = self.owner.country.name if self.owner.country else 'Unknown'
        return _("Assassin token owned by %(owner)s for target %(target)s") % {
            'owner': owner_name,
            'target': self.target.name,
        }

class Assassination(models.Model):
    """ An Assassination describes an attempt made by a Player to murder the
        leader of another Country, spending some Ducats. (Advanced Rule VI.C.6) """
    killer = models.ForeignKey(Player, related_name="assassination_attempts")
    target = models.ForeignKey(Player, related_name="assassination_targets")
    ducats = models.PositiveIntegerField(default=0) # Must be 12, 24, or 36
    # Store chosen numbers? Or resolve immediately? Let's resolve immediately in view/processing.
    # success = models.BooleanField(default=False) # Store result?

    def __unicode__(self):
        killer_name = self.killer.country.name if self.killer.country else 'Unknown'
        target_name = self.target.country.name if self.target.country else 'Unknown'
        return _("%(killer)s attempts assassination on %(target)s for %(ducats)sd") % {
            'killer': killer_name,
            'target': target_name,
            'ducats': self.ducats,
        }

    def explain(self):
        # Already provided by __unicode__ essentially
        return unicode(self)

    def get_dice_count(self):
        """ Returns number of dice based on ducats spent (Rule VI.C.6.a). """
        return self.ducats // 12

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

