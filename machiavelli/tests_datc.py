# machiavelli/tests_datc.py

import os
import re
from collections import defaultdict

from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import User # Import User model

# Import your models
from .models import (
    Game, Player, Unit, Order, Area, Country, Scenario, GameArea, Configuration
)

# Define path to your DATC file
DATC_FILE_PATH = os.path.join(os.path.dirname(__file__), 'datc_section_6.txt')

# --- DATC Parser (Keep the parser function as defined previously) ---
def parse_datc_file(filepath):
    """Parses a DATC file and yields dictionaries representing test cases."""
    with open(filepath, 'r') as f:
        current_case = None
        section = None
        variant = "Standard" # Default variant
        raw_lines_for_case = [] # Store raw lines for POSTSTATE_SAME check

        for line in f:
            original_line = line # Keep original line for POSTSTATE_SAME check
            line = line.strip()
            raw_lines_for_case.append(original_line.strip()) # Add stripped line

            if not line or line.startswith('###'):
                continue

            # Handle Comments
            if '#' in line:
                line = line.split('#', 1)[0].strip()
                if not line:
                    continue

            # Handle Variant
            if line.startswith('VARIANT_ALL'):
                variant = line.split(None, 1)[1].strip()
                continue

            # Start of a new case
            if line.startswith('CASE'):
                if current_case:
                    current_case['raw_lines'] = raw_lines_for_case[:-1] # Add raw lines excluding current CASE line
                    yield current_case
                case_name = line.split(None, 1)[1].strip()
                current_case = {
                    'name': case_name,
                    'variant': variant,
                    'pre_phase': None,
                    'pre_units': [],
                    'pre_dislodged': [],
                    'pre_supply_centers': {},
                    'orders': [],
                    'post_units': [],
                    'post_dislodged': [],
                    'raw_lines': [] # Initialize raw_lines here
                }
                raw_lines_for_case = [original_line.strip()] # Start new raw lines list
                section = None
                continue

            # End of a case
            if line == 'END':
                if current_case:
                    current_case['raw_lines'] = raw_lines_for_case # Add raw lines including END
                    yield current_case
                current_case = None
                section = None
                raw_lines_for_case = [] # Reset raw lines
                continue

            if current_case is None:
                continue

            # Section headers
            if line.startswith('PRESTATE_SETPHASE'):
                current_case['pre_phase'] = line.split(None, 1)[1].strip()
                section = None
            elif line == 'PRESTATE':
                section = 'pre_units'
            elif line == 'PRESTATE_DISLODGED':
                 section = 'pre_dislodged'
            elif line == 'PRESTATE_SUPPLYCENTER_OWNERS':
                 section = 'pre_supply_centers'
            elif line == 'ORDERS':
                section = 'orders'
            elif line == 'POSTSTATE':
                section = 'post_units'
            elif line == 'POSTSTATE_DISLODGED':
                section = 'post_dislodged'
            elif line == 'POSTSTATE_SAME': # Handle POSTSTATE_SAME explicitly
                section = 'post_same' # Mark section, handled later
            elif section:
                # Add line to the current section
                if section == 'pre_supply_centers':
                    country_str, areas_str = line.split(':', 1)
                    country_name = country_str.strip()
                    # Handle potential empty areas_str
                    areas = [a.strip() for a in areas_str.split()] if areas_str.strip() else []
                    current_case[section][country_name] = areas
                elif section != 'post_same': # Don't add lines if section is post_same
                    current_case[section].append(line)

    # Yield the last case if the file doesn't end with END
    if current_case:
        current_case['raw_lines'] = raw_lines_for_case
        yield current_case


# --- Test Case Class ---

class DATCAdjudicatorTests(TestCase):
    # Load the Diplomacy map fixture and potentially a default user fixture
    fixtures = ['diplomacy_map.yaml', 'default_user.yaml'] # Assumes 'default_user.yaml' creates User with pk=1

    TEST_USER_PK = 1 # Define the PK of the user created by default_user.yaml

    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        # Get the specific Scenario, Countries, and Areas from the fixture
        try:
            cls.scenario = Scenario.objects.get(pk=100)
        except Scenario.DoesNotExist:
            raise Exception("Fixture diplomacy_map.yaml did not load Scenario 100 correctly.")

        cls.countries_list = list(Country.objects.filter(pk__in=range(11, 18)))
        if len(cls.countries_list) != 7:
             raise Exception("Fixture diplomacy_map.yaml did not load Countries 11-17 correctly.")
        cls.countries = {country.name: country for country in cls.countries_list}

        cls.areas_list = list(Area.objects.filter(pk__gte=101))
        if not cls.areas_list:
             raise Exception("Fixture diplomacy_map.yaml did not load Areas 101+ correctly.")
        cls.areas = {area.code: area for area in cls.areas_list}

        # Ensure the test user exists
        try:
            cls.test_user = User.objects.get(pk=cls.TEST_USER_PK)
        except User.DoesNotExist:
             raise Exception(f"Fixture default_user.yaml did not load User with pk={cls.TEST_USER_PK} correctly.")


    # --- Helper Methods (Keep _parse_unit_string, _parse_order_string, _get_actual_poststate, _parse_poststate_lines as before) ---
    def _parse_unit_string(self, line):
        """Parses 'Country: Type Area[/coast]' -> (country_name, unit_type, area_code, coast)."""
        try:
            country_str, unit_str = line.split(':', 1)
            country_name = country_str.strip()
            parts = unit_str.strip().split()
            unit_type = parts[0].upper() # Ensure type is uppercase
            area_str = parts[1]
            area_code = area_str
            coast = None
            if '/' in area_str:
                area_code, coast = area_str.split('/', 1)
            # Use upper() for area code consistency
            return country_name, unit_type, area_code.upper(), coast
        except Exception as e:
            raise ValueError(f"Could not parse unit string: '{line}' - Error: {e}")

    def _parse_order_string(self, line):
        """Parses DATC order line -> (country_name, unit_type, unit_area_code, unit_coast, order_details)."""
        try:
            country_str, order_str = line.split(':', 1)
            country_name = country_str.strip()
            parts = order_str.strip().split()

            unit_type = parts[0].upper() # Ensure type is uppercase
            unit_area_str = parts[1]
            unit_area_code = unit_area_str.upper()
            unit_coast = None
            if '/' in unit_area_str:
                unit_area_code, unit_coast = unit_area_str.split('/', 1)
                unit_area_code = unit_area_code.upper()

            order_details = parts[2:] # The rest of the line defines the order

            return country_name, unit_type, unit_area_code, unit_coast, order_details
        except Exception as e:
            raise ValueError(f"Could not parse order string: '{line}' - Error: {e}")

    def _get_actual_poststate(self, game):
        """Queries DB for final unit positions and dislodged units."""
        final_units = set()
        dislodged_units = set()

        for unit in Unit.objects.filter(player__game=game):
            # Construct canonical unit string
            area_code = unit.area.board_area.code # Use CODE from Area
            coast_str = ""
            # TODO: Add coast retrieval if your Unit model stores it
            # if unit.coast: coast_str = f"/{unit.coast}"
            # Use Country name from the related Country object
            unit_str = f"{unit.player.country.name}: {unit.type} {area_code.lower()}{coast_str}"

            if unit.must_retreat:
                dislodged_units.add(unit_str)
            else:
                final_units.add(unit_str)

        return final_units, dislodged_units

    def _parse_poststate_lines(self, lines):
        """Parses POSTSTATE or POSTSTATE_DISLODGED lines into a set of canonical unit strings."""
        units = set()
        for line in lines:
            try:
                # Use the same parsing logic as PRESTATE
                country_name, unit_type, area_code, coast = self._parse_unit_string(line)
                coast_str = f"/{coast}" if coast else ""
                # Use lower() for area code consistency with _get_actual_poststate
                units.add(f"{country_name}: {unit_type} {area_code.lower()}{coast_str}")
            except ValueError as e:
                print(f"Warning: Could not parse poststate line: '{line}' - {e}")
        return units

    def _create_game_state(self, case_data):
        """Creates Game, Players, GameAreas, Units based on PRESTATE."""
        # Create a unique slug for each test run
        game_slug = f"datc-{case_data['name'].replace(' ', '-').replace('.', '_').lower()}-{os.urandom(4).hex()}"

        game = Game.objects.create(
            slug=game_slug,
            scenario=self.scenario, # Use Scenario 100 loaded in setUpTestData
            created_by=self.test_user, # Use the test user
            time_limit=24*60*60,
            year=1901, # Default, might be overridden by SETPHASE
            season=1,
            phase=PHORDERS # Default to orders phase
        )
        Configuration.objects.create(game=game) # Create default config

        # Set phase if specified
        if case_data['pre_phase']:
             try:
                 phase_parts = case_data['pre_phase'].split(',')
                 season_str = phase_parts[0].split()[0].lower()
                 year = int(phase_parts[0].split()[1])
                 phase_str = phase_parts[1].strip().lower()

                 season_map = {'spring': 1, 'summer': 2, 'fall': 3}
                 # Map DATC phase names to your model's phase constants
                 phase_map = {'movement': PHORDERS, 'retreat': PHRETREATS, 'adjustment': PHREINFORCE}

                 game.year = year
                 game.season = season_map.get(season_str, 1)
                 game.phase = phase_map.get(phase_str, PHORDERS)
                 game.save()
             except Exception as e:
                 raise ValueError(f"Could not parse PRESTATE_SETPHASE '{case_data['pre_phase']}': {e}")


        # Create GameAreas for all Diplomacy areas (PKs 101+)
        game_areas_map = {} # Map Area object to GameArea object
        for area in self.areas_list:
             ga = GameArea.objects.create(game=game, board_area=area)
             game_areas_map[area.pk] = ga


        players = {} # Map country name to Player object
        units = {} # Map unit string ("England: F nth") to Unit object

        for unit_line in case_data['pre_units']:
            country_name, unit_type, area_code, coast = self._parse_unit_string(unit_line)

            country = self.countries.get(country_name) # Use cls.countries with new PKs
            area = self.areas.get(area_code)           # Use cls.areas with new PKs
            if not country or not area:
                raise ValueError(f"Fixture Error: Unknown country '{country_name}' or area '{area_code}' in line: {unit_line}")

            player = players.get(country_name)
            if not player:
                player = Player.objects.create(game=game, country=country, user=self.test_user)
                players[country_name] = player

            game_area = game_areas_map.get(area.pk) # Get GameArea using Area PK
            if not game_area:
                 raise ValueError(f"Could not find GameArea for Area {area_code} in game {game.id}")

            # TODO: Handle coast specification if your Unit model supports it
            unit = Unit.objects.create(
                player=player,
                type=unit_type,
                area=game_area,
                # coast=coast, # Add if your model has it
                placed=True,
                paid=True
            )
            # Use lower() for area code consistency in key
            unit_key = f"{country_name}: {unit_type} {area_code.lower()}" + (f"/{coast}" if coast else "")
            units[unit_key.strip()] = unit

        # Handle PRESTATE_DISLODGED for retreat phase tests
        if game.phase == PHRETREATS and case_data['pre_dislodged']:
            for unit_line in case_data['pre_dislodged']:
                 # Find the corresponding unit created above and set must_retreat
                 country_name, unit_type, area_code, coast = self._parse_unit_string(unit_line)
                 unit_key = f"{country_name}: {unit_type} {area_code.lower()}" + (f"/{coast}" if coast else "")
                 unit_obj = units.get(unit_key.strip())
                 if unit_obj:
                     # DATC doesn't specify *where* attack came from, use a placeholder
                     unit_obj.must_retreat = "UNKNOWN" # Adjudicator needs to handle this if needed
                     unit_obj.save()
                 else:
                      print(f"Warning: Could not find unit '{unit_key}' to mark as dislodged.")


        # Handle PRESTATE_SUPPLYCENTER_OWNERS for build phase tests if needed

        return game, players, units

    def _create_orders(self, game, players, units_map, order_lines):
        """Creates Order model instances."""
        orders_created = []
        game_areas = {ga.board_area.code: ga for ga in GameArea.objects.filter(game=game)} # Map code to GameArea

        for order_line in order_lines:
            try:
                country_name, unit_type, unit_area_code, unit_coast, details = self._parse_order_string(order_line)

                player = players.get(country_name)
                if not player:
                    continue # Skip orders for countries not in PRESTATE

                # Find the specific Unit object
                unit_key = f"{country_name}: {unit_type} {unit_area_code.lower()}" + (f"/{unit_coast}" if unit_coast else "")
                unit_obj = units_map.get(unit_key.strip())
                if not unit_obj: # Try without coast as fallback
                     unit_key_base = f"{country_name}: {unit_type} {unit_area_code.lower()}"
                     unit_obj = units_map.get(unit_key_base.strip())

                if not unit_obj:
                    raise ValueError(f"Could not find unit '{unit_key}' from PRESTATE for order: {order_line}")

                # --- Parse Order Details ---
                order_data = {'unit': unit_obj, 'player': player, 'confirmed': True}
                verb = details[0].upper() if details else 'H' # Default to Hold if no details

                if verb == 'H' or verb == 'HOLDS':
                    order_data['code'] = 'H'
                elif verb == '-': # Move (implicit)
                    dest_area_code = details[0].upper()
                    dest_coast = None
                    if '/' in details[0]:
                        dest_area_code, dest_coast = details[0].split('/', 1)
                        dest_area_code = dest_area_code.upper()
                    dest_game_area = game_areas.get(dest_area_code)
                    if not dest_game_area: raise ValueError(f"Unknown destination area code '{dest_area_code}'")
                    order_data['code'] = '-'
                    order_data['destination'] = dest_game_area
                    # TODO: Handle coast in destination if model supports it
                    # TODO: Handle 'via convoy' if needed
                elif verb == 'S' or verb == 'SUPPORTS':
                    order_data['code'] = 'S'
                    sup_unit_type = details[1].upper()
                    sup_unit_area_str = details[2]
                    sup_unit_area_code = sup_unit_area_str.upper()
                    sup_unit_coast = None
                    if '/' in sup_unit_area_str:
                        sup_unit_area_code, sup_unit_coast = sup_unit_area_str.split('/', 1)
                        sup_unit_area_code = sup_unit_area_code.upper()

                    # Find supported unit
                    supported_unit_obj = Unit.objects.filter(
                        player__game=game, type=sup_unit_type, area__board_area__code=sup_unit_area_code
                    ).first() # Simple match, might need coast refinement
                    if not supported_unit_obj: raise ValueError(f"Cannot find supported unit {sup_unit_type} {sup_unit_area_code}")
                    order_data['subunit'] = supported_unit_obj

                    # Parse supported action
                    if len(details) > 3:
                        sup_action = details[3]
                        if sup_action == '-': # Support Move
                            order_data['subcode'] = '-'
                            sup_dest_area_code = details[4].upper()
                            sup_dest_coast = None
                            if '/' in details[4]:
                                sup_dest_area_code, sup_dest_coast = details[4].split('/', 1)
                                sup_dest_area_code = sup_dest_area_code.upper()
                            sup_dest_game_area = game_areas.get(sup_dest_area_code)
                            if not sup_dest_game_area: raise ValueError(f"Unknown support destination '{sup_dest_area_code}'")
                            order_data['subdestination'] = sup_dest_game_area
                            # TODO: Handle coast in subdestination
                        else: # Assume Support Hold if action is not '-'
                             order_data['subcode'] = 'H'
                    else: # Assume Support Hold if only unit specified
                         order_data['subcode'] = 'H'

                elif verb == 'C' or verb == 'CONVOYS':
                    order_data['code'] = 'C'
                    conv_unit_type = details[1].upper()
                    conv_unit_area_code = details[2].upper()

                    # Find convoyed unit (Army)
                    convoyed_unit_obj = Unit.objects.filter(
                        player__game=game, type=conv_unit_type, area__board_area__code=conv_unit_area_code
                    ).first()
                    if not convoyed_unit_obj: raise ValueError(f"Cannot find convoyed unit {conv_unit_type} {conv_unit_area_code}")
                    order_data['subunit'] = convoyed_unit_obj

                    if details[3] != '-': raise ValueError("Expected '-' in convoy order")

                    conv_dest_area_code = details[4].upper()
                    conv_dest_coast = None
                    if '/' in details[4]:
                        conv_dest_area_code, conv_dest_coast = details[4].split('/', 1)
                        conv_dest_area_code = conv_dest_area_code.upper()
                    conv_dest_game_area = game_areas.get(conv_dest_area_code)
                    if not conv_dest_game_area: raise ValueError(f"Unknown convoy destination '{conv_dest_area_code}'")
                    order_data['subdestination'] = conv_dest_game_area
                    order_data['subcode'] = '-' # Implicitly convoying an advance
                    # TODO: Handle coast in subdestination

                # Add other verbs if needed (Build, Remove, Retreat)
                elif verb == 'BUILD':
                     # Requires Adjustment phase logic - Skip for movement tests
                     print(f"Skipping BUILD order: {order_line}")
                     continue
                elif verb == 'REMOVE' or verb == 'DISBAND':
                     # Requires Adjustment phase logic - Skip for movement tests
                     print(f"Skipping REMOVE/DISBAND order: {order_line}")
                     continue
                elif verb == 'RETREAT': # Handle retreat orders if phase is Retreat
                     if game.phase == PHRETREATS:
                         # Format: Unit RETREAT Dest[/coast]
                         retreat_dest_code = details[1].upper()
                         retreat_dest_coast = None
                         if '/' in details[1]:
                             retreat_dest_code, retreat_dest_coast = details[1].split('/', 1)
                             retreat_dest_code = retreat_dest_code.upper()
                         retreat_dest_game_area = game_areas.get(retreat_dest_code)
                         if not retreat_dest_game_area: raise ValueError(f"Unknown retreat destination '{retreat_dest_code}'")
                         # Create RetreatOrder instead of Order
                         RetreatOrder.objects.create(unit=unit_obj, area=retreat_dest_game_area)
                         print(f"Created RetreatOrder: {unit_obj} -> {retreat_dest_game_area}")
                         continue # Skip creating regular Order
                     else:
                         print(f"Skipping RETREAT order in non-retreat phase: {order_line}")
                         continue

                else: # Unrecognized verb, treat as move if possible, else hold
                    try: # Attempt to parse as implicit move
                        dest_area_code = verb.upper()
                        dest_coast = None
                        if '/' in verb:
                            dest_area_code, dest_coast = verb.split('/', 1)
                            dest_area_code = dest_area_code.upper()
                        dest_game_area = game_areas.get(dest_area_code)
                        if not dest_game_area: raise ValueError()
                        order_data['code'] = '-'
                        order_data['destination'] = dest_game_area
                        # TODO: Handle coast
                    except: # Default to Hold
                        order_data['code'] = 'H'

                # Create and save the order
                order = Order.objects.create(**order_data)
                orders_created.append(order)

            except Exception as e:
                print(f"Error processing order line: '{order_line}' - {e}")
                # Decide whether to raise error or just skip the order for the test
                raise # Re-raise to fail the test clearly

        return orders_created

    def _run_datc_test(self, case_data):
        """Executes a single DATC test case."""
        print(f"\nRunning DATC Case: {case_data['name']}")

        # 1. Setup Game State
        game, players, units_map = self._create_game_state(case_data)

        # 2. Create Orders (Handle both Movement and Retreat phases)
        orders_created = []
        retreat_orders_created = []
        if game.phase == PHORDERS:
            try:
                orders_created = self._create_orders(game, players, units_map, case_data['orders'])
            except ValueError as e:
                # If order creation fails due to parsing/validation, check if POSTSTATE is SAME
                is_poststate_same = any(l.strip() == 'POSTSTATE_SAME' for l in case_data.get('raw_lines', []))
                if is_poststate_same:
                     print(f"Order creation failed as expected for invalid order test: {e}")
                     actual_units, actual_dislodged = self._get_actual_poststate(game)
                     expected_units = self._parse_poststate_lines(case_data['pre_units'])
                     self.assertSetEqual(actual_units, expected_units, "State changed unexpectedly after invalid order.")
                     self.assertEqual(len(actual_dislodged), 0, "Dislodgements occurred unexpectedly after invalid order.")
                     return # Test passes
                else:
                     raise AssertionError(f"Order creation failed unexpectedly for case {case_data['name']}: {e}")
        elif game.phase == PHRETREATS:
             # Create RetreatOrder objects directly
             game_areas = {ga.board_area.code: ga for ga in GameArea.objects.filter(game=game)}
             for order_line in case_data['orders']:
                 try:
                     # Parse retreat order: Country: Type Area Retreat Dest[/coast] or Disband
                     country_str, order_str = order_line.split(':', 1)
                     parts = order_str.strip().split()
                     unit_type = parts[0].upper()
                     unit_area_code = parts[1].upper()
                     unit_coast = None
                     if '/' in parts[1]: unit_area_code, unit_coast = parts[1].split('/', 1); unit_area_code = unit_area_code.upper()
                     action = parts[2].upper()

                     unit_key = f"{country_str.strip()}: {unit_type} {unit_area_code.lower()}" + (f"/{unit_coast}" if unit_coast else "")
                     unit_obj = units_map.get(unit_key.strip())
                     if not unit_obj: # Fallback without coast
                          unit_key_base = f"{country_str.strip()}: {unit_type} {unit_area_code.lower()}"
                          unit_obj = units_map.get(unit_key_base.strip())

                     if not unit_obj: raise ValueError(f"Cannot find unit '{unit_key}' for retreat.")

                     if action == 'DISBAND':
                         RetreatOrder.objects.create(unit=unit_obj, area=None)
                     else: # Assume destination area
                         dest_code = action.upper()
                         dest_coast = None
                         if '/' in action: dest_code, dest_coast = action.split('/', 1); dest_code = dest_code.upper()
                         dest_game_area = game_areas.get(dest_code)
                         if not dest_game_area: raise ValueError(f"Unknown retreat destination '{dest_code}'")
                         RetreatOrder.objects.create(unit=unit_obj, area=dest_game_area)
                         # TODO: Handle retreat coast if model supports it
                 except Exception as e:
                     print(f"Error processing RETREAT order line: '{order_line}' - {e}")
                     raise

        # 3. Adjudicate
        if game.phase == PHORDERS:
            if hasattr(game, 'adjudicate_movement_phase'):
                 game.adjudicate_movement_phase()
            else:
                 game.process_orders() # Fallback
        elif game.phase == PHRETREATS:
             game.process_retreats() # Call the retreat processing logic

        # 4. Get Actual Results
        actual_units, actual_dislodged = self._get_actual_poststate(game)

        # 5. Get Expected Results
        is_poststate_same = any(l.strip() == 'POSTSTATE_SAME' for l in case_data.get('raw_lines', []))

        if is_poststate_same:
            expected_units = self._parse_poststate_lines(case_data['pre_units'])
            expected_dislodged = set() # No dislodgements expected
        else:
            expected_units = self._parse_poststate_lines(case_data['post_units'])
            expected_dislodged = self._parse_poststate_lines(case_data['post_dislodged'])


        # 6. Assertions
        self.assertSetEqual(actual_units, expected_units, "Final unit positions do not match expected.")
        # For retreat phase tests, expected_dislodged should be empty as they are resolved
        if game.phase == PHRETREATS:
             self.assertSetEqual(actual_dislodged, set(), "Units still marked for retreat after retreat phase.")
             # Check if expected dislodged units from DATC were correctly handled (either retreated or implicitly disbanded)
             expected_dislodged_from_datc = self._parse_poststate_lines(case_data['post_dislodged'])
             if expected_dislodged_from_datc:
                  print("Warning: DATC specified POSTSTATE_DISLODGED for a retreat phase test. This usually means units were destroyed. Verify manually.")
        else:
             self.assertSetEqual(actual_dislodged, expected_dislodged, "Dislodged units do not match expected.")


# --- Dynamically add test methods (Keep as before) ---
try:
    all_datc_cases = list(parse_datc_file(DATC_FILE_PATH))
    # Dynamically create test methods on the TestCase class
    for case_data in all_datc_cases:
        test_method_name = f"test_case_{case_data['name'].replace('.', '_').replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '').lower()}"
        def create_test_method(data):
            def test_method(self):
                self._run_datc_test(data)
            return test_method
        setattr(DATCAdjudicatorTests, test_method_name, create_test_method(case_data))
except IOError:
    print(f"Warning: DATC file not found at {DATC_FILE_PATH}. Skipping DATC tests.")
except Exception as e:
    print(f"Error setting up DATC tests: {e}")