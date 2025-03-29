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

def load_areas():
    # Disable foreign key checks
    cursor = connection.cursor()
    # Use 'SET session.foreign_key_checks = 0;' for newer MySQL/MariaDB if SET FOREIGN_KEY_CHECKS=0; causes issues
    cursor.execute('SET FOREIGN_KEY_CHECKS=0;')

    # Delete existing areas
    Area.objects.all().delete()

    # Read areas.yaml
    try:
        with open('machiavelli/fixtures/areas.yaml', 'r') as f:
            # Use SafeLoader
            areas_data = yaml.load(f, Loader=SafeLoader)
    except IOError:
        print "Error: machiavelli/fixtures/areas.yaml not found."
        cursor.execute('SET FOREIGN_KEY_CHECKS=1;') # Re-enable checks before exiting
        return
    except yaml.YAMLError as e:
        print "Error parsing areas.yaml:", e
        cursor.execute('SET FOREIGN_KEY_CHECKS=1;') # Re-enable checks before exiting
        return

    # First pass: Create all areas without borders
    created_areas = {}
    for item in areas_data:
        try:
            area_obj = Area.objects.create(
                id=item['pk'],
                code=item['fields']['code'],
                name=item['fields']['name'],
                has_city=item['fields'].get('has_city', False), # Use .get with default
                has_port=item['fields'].get('has_port', False),
                is_coast=item['fields'].get('is_coast', False),
                is_fortified=item['fields'].get('is_fortified', False),
                is_sea=item['fields'].get('is_sea', False),
                # --- REMOVED control_income and garrison_income ---
                # control_income=item['fields'].get('control_income', 0),
                # garrison_income=item['fields'].get('garrison_income', 0)
                # --- Keep major_city_income if it exists in your model/fixture ---
                major_city_income=item['fields'].get('major_city_income', None),
                # --- Add coast_names if it exists in your model/fixture ---
                coast_names=item['fields'].get('coast_names', None)
            )
            created_areas[area_obj.id] = area_obj
        except KeyError as e:
            print "KeyError processing area PK {}: Missing key {}".format(item.get('pk'), e)
        except Exception as e:
            print "Error creating area PK {}: {}".format(item.get('pk'), e)


    # Second pass: Update borders
    print "Updating borders..."
    for item in areas_data:
        try:
            area = created_areas.get(item['pk'])
            if not area:
                print "Skipping borders for area PK {} (not created)".format(item['pk'])
                continue

            border_ids = item['fields'].get('borders', [])
            borders_to_add = []
            for border_id in border_ids:
                border_area = created_areas.get(border_id)
                if border_area:
                    borders_to_add.append(border_area)
                else:
                    print "Warning: Border area PK {} not found for area PK {}".format(border_id, item['pk'])
            if borders_to_add:
                area.borders.add(*borders_to_add) # Use bulk add
        except Exception as e:
            print "Error adding borders for area PK {}: {}".format(item.get('pk'), e)

    # Re-enable foreign key checks
    cursor.execute('SET FOREIGN_KEY_CHECKS=1;')
    print "Area loading complete."

def load_other_fixtures():
    print "Loading other fixtures..."
    try:
        management.call_command('loaddata', 'countries.yaml')
        management.call_command('loaddata', 'tokens.yaml')
        management.call_command('loaddata', 'scenarios.yaml')
        # Add other fixtures if needed
        print "Other fixtures loaded."
    except Exception as e:
        print "Error loading other fixtures:", e

if __name__ == '__main__':
    print "Starting fixture loading..."
    load_areas()
    load_other_fixtures()
    print "Fixture loading finished."