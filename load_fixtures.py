import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import yaml
from django.core import management
from django.db import connection
from machiavelli.models import Area

def load_areas():
    # Disable foreign key checks
    cursor = connection.cursor()
    cursor.execute('SET FOREIGN_KEY_CHECKS=0;')
    
    # Delete existing areas
    Area.objects.all().delete()
    
    # Read areas.yaml
    with open('machiavelli/fixtures/areas.yaml', 'r') as f:
        areas_data = yaml.load(f, Loader=yaml.SafeLoader)  # Use SafeLoader to address the warning
    
    # First pass: Create all areas without borders
    for item in areas_data:
        Area.objects.create(
            id=item['pk'],
            code=item['fields']['code'],
            name=item['fields']['name'],
            has_city=item['fields']['has_city'],
            has_port=item['fields']['has_port'],
            is_coast=item['fields']['is_coast'],
            is_fortified=item['fields']['is_fortified'],
            is_sea=item['fields']['is_sea'],
            control_income=item['fields'].get('control_income', 0),
            garrison_income=item['fields'].get('garrison_income', 0)
        )
    
    # Second pass: Update borders
    for item in areas_data:
        area = Area.objects.get(id=item['pk'])
        border_ids = item['fields'].get('borders', [])
        for border_id in border_ids:
            border_area = Area.objects.get(id=border_id)
            area.borders.add(border_area)
    
    # Re-enable foreign key checks
    cursor.execute('SET FOREIGN_KEY_CHECKS=1;')

def load_other_fixtures():
    management.call_command('loaddata', 'countries.yaml')
    management.call_command('loaddata', 'tokens.yaml')
    management.call_command('loaddata', 'scenarios.yaml')

if __name__ == '__main__':
    load_areas()
    load_other_fixtures() 