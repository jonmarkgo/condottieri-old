import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import yaml
from django.core import management
from django.db import connection
# Ensure all necessary models are imported if needed elsewhere, but only Area is needed here
from machiavelli.models import Area

# Use SafeLoader for YAML loading
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from yaml import SafeLoader # Import SafeLoader

def load_machiavelli_areas():
    """Load the original Machiavelli areas (PKs 1-73)"""
    cursor = connection.cursor()
    cursor.execute('SET FOREIGN_KEY_CHECKS=0;')

    try:
        print "Loading Machiavelli areas..."
        try:
            with open('machiavelli/fixtures/areas.yaml', 'r') as f:
                areas_data = yaml.load(f, Loader=SafeLoader)
        except IOError:
            print "Error: machiavelli/fixtures/areas.yaml not found."
            return
        except yaml.YAMLError as e:
            print "Error parsing areas.yaml:", e
            return

        # First pass: Create all areas without borders
        created_areas = {}
        for item in areas_data:
            try:
                area_obj = Area.objects.create(
                    id=item['pk'],
                    code=item['fields']['code'],
                    name=item['fields']['name'],
                    has_city=item['fields'].get('has_city', False),
                    has_port=item['fields'].get('has_port', False),
                    is_coast=item['fields'].get('is_coast', False),
                    is_fortified=item['fields'].get('is_fortified', False),
                    is_sea=item['fields'].get('is_sea', False),
                    major_city_income=item['fields'].get('major_city_income', None),
                    coast_names=item['fields'].get('coast_names', None)
                )
                created_areas[area_obj.id] = area_obj
                print "Created Machiavelli area:", area_obj.code
            except KeyError as e:
                print "KeyError processing area PK {}: Missing key {}".format(item.get('pk'), e)
            except Exception as e:
                print "Error creating area PK {}: {}".format(item.get('pk'), e)

        # Second pass: Update borders
        print "\nUpdating Machiavelli area borders..."
        for item in areas_data:
            try:
                area = created_areas.get(item['pk'])
                if not area:
                    continue

                border_ids = item['fields'].get('borders', [])
                borders_to_add = []
                for border_id in border_ids:
                    border_area = created_areas.get(border_id)
                    if border_area:
                        borders_to_add.append(border_area)
                    else:
                        print "Warning: Border area PK {} not found for area {}".format(border_id, area.code)
                
                if borders_to_add:
                    area.borders.add(*borders_to_add)
                    print "Added {} borders to {}".format(len(borders_to_add), area.code)

            except Exception as e:
                print "Error adding borders for area {}: {}".format(item.get('pk'), e)

    finally:
        cursor.execute('SET FOREIGN_KEY_CHECKS=1;')
        print "\nMachiavelli area loading complete."

def load_diplomacy_areas():
    """Load the Diplomacy map areas (PKs 101+)"""
    cursor = connection.cursor()
    cursor.execute('SET FOREIGN_KEY_CHECKS=0;')

    try:
        print "\nLoading Diplomacy map areas..."
        try:
            with open('machiavelli/fixtures/diplomacy_map.yaml', 'r') as f:
                data = yaml.load(f, Loader=SafeLoader)
        except IOError:
            print "Error: diplomacy_map.yaml not found."
            return
        except yaml.YAMLError as e:
            print "Error parsing diplomacy_map.yaml:", e
            return

        # First create all areas
        created_areas = {}
        for item in data:
            if item['model'] == 'machiavelli.area':
                try:
                    area_obj = Area.objects.create(
                        id=item['pk'],
                        code=item['fields']['code'],
                        name=item['fields']['name'],
                        has_city=item['fields'].get('has_city', False),
                        has_port=item['fields'].get('has_port', False),
                        is_coast=item['fields'].get('is_coast', False),
                        is_fortified=item['fields'].get('is_fortified', False),
                        is_sea=item['fields'].get('is_sea', False),
                        coast_names=item['fields'].get('coast_names', None)
                    )
                    created_areas[area_obj.id] = area_obj
                    print "Created Diplomacy area:", area_obj.code
                except Exception as e:
                    print "Error creating Diplomacy area PK {}: {}".format(item.get('pk'), e)

        # Then update borders
        print "\nUpdating Diplomacy area borders..."
        for item in data:
            if item['model'] == 'machiavelli.area':
                try:
                    area = created_areas.get(item['pk'])
                    if not area:
                        continue

                    border_ids = item['fields'].get('borders', [])
                    borders_to_add = []
                    for border_id in border_ids:
                        border_area = created_areas.get(border_id)
                        if border_area:
                            borders_to_add.append(border_area)
                        else:
                            print "Warning: Border area PK {} not found for area {}".format(border_id, area.code)
                    
                    if borders_to_add:
                        area.borders.add(*borders_to_add)
                        print "Added {} borders to {}".format(len(borders_to_add), area.code)

                except Exception as e:
                    print "Error adding borders for area {}: {}".format(item.get('pk'), e)

    finally:
        cursor.execute('SET FOREIGN_KEY_CHECKS=1;')
        print "\nDiplomacy map loading complete."

def load_diplomacy_data():
    """Load the remaining Diplomacy map data (countries, scenarios, homes, etc.)"""
    print "\nLoading remaining Diplomacy map data..."
    try:
        # Load only the non-area data from diplomacy_map.yaml
        with open('machiavelli/fixtures/diplomacy_map.yaml', 'r') as f:
            data = yaml.load(f, Loader=SafeLoader)
        
        # Filter out area data and add PKs to entries that need them
        non_area_data = []
        next_pk = 201  # Start PKs for non-area entries at 201
        
        for item in data:
            if item['model'] != 'machiavelli.area':
                # Add PK if missing
                if 'pk' not in item:
                    item['pk'] = next_pk
                    next_pk += 1
                
                # Remove coast field from setup entries if it exists
                if item['model'] == 'machiavelli.setup' and 'fields' in item and 'coast' in item['fields']:
                    del item['fields']['coast']
                
                non_area_data.append(item)
        
        if not non_area_data:
            print "No valid non-area data found in diplomacy_map.yaml"
            return
        
        # Write filtered data to temporary file
        temp_file = 'machiavelli/fixtures/diplomacy_data_temp.yaml'
        with open(temp_file, 'w') as f:
            yaml.dump(non_area_data, f, Dumper=Dumper)
        
        # Load the filtered data
        management.call_command('loaddata', temp_file, verbosity=1)
        
        # Clean up temp file
        os.remove(temp_file)
        
    except Exception as e:
        print "Error loading remaining Diplomacy data:", e
        if os.path.exists(temp_file):
            os.remove(temp_file)

def load_other_fixtures():
    print "\nLoading other fixtures..."
    fixtures = [
        'countries.yaml',
        'tokens.yaml',
        'scenarios.yaml'
    ]
    
    for fixture in fixtures:
        try:
            print "\nLoading fixture:", fixture
            management.call_command('loaddata', fixture, verbosity=1)
            print "Successfully loaded", fixture
        except Exception as e:
            print "Error loading {}: {}".format(fixture, e)
            print "Continuing with next fixture..."

if __name__ == '__main__':
    print "Starting fixture loading..."
    # First clear all areas
    print "Clearing existing areas..."
    Area.objects.all().delete()
    
    # Load areas in correct order
    load_machiavelli_areas()  # Load PKs 1-73
    load_diplomacy_areas()    # Load PKs 101+ and related data
    load_diplomacy_data()     # Load remaining Diplomacy data
    load_other_fixtures()     # Load remaining fixtures
    print "\nFixture loading finished."