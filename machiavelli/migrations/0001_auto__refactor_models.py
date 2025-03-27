# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

# NOTE: The 'models' dictionary below MUST accurately reflect
# the state of your models BEFORE this migration runs.

class Migration(SchemaMigration):

    def forwards(self, orm):
        # --- Phase 1: Remove old constraints/fields ---

        # Remove unique constraint for ('unit', 'player') on Order
        db.delete_unique('machiavelli_order', ['unit_id', 'player_id'])

        # Deleting field 'Unit.besieging'
        db.delete_column('machiavelli_unit', 'besieging')

        # Deleting field 'Area.control_income'
        db.delete_column('machiavelli_area', 'control_income')

        # Deleting field 'Area.garrison_income'
        db.delete_column('machiavelli_area', 'garrison_income')


        # --- Phase 2: Add new models ---

        # Adding model 'Expense'
        db.create_table('machiavelli_expense', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('player', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Player'])),
            ('ducats', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('type', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('area', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.GameArea'], null=True, blank=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Unit'], null=True, blank=True)),
            ('confirmed', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('machiavelli', ['Expense'])

        # Adding model 'Rebellion'
        db.create_table('machiavelli_rebellion', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            # area is OneToOne, implies unique=True
            ('area', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['machiavelli.GameArea'], unique=True)),
            ('player', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Player'])),
            ('garrisoned', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('machiavelli', ['Rebellion'])

        # Adding model 'Loan'
        db.create_table('machiavelli_loan', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            # player is OneToOne, implies unique=True
            ('player', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['machiavelli.Player'], unique=True)),
            ('principal', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('interest_rate', self.gf('django.db.models.fields.FloatField')(default=0.0)),
            ('debt', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('due_season', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('due_year', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal('machiavelli', ['Loan'])

        # Adding model 'Assassin'
        db.create_table('machiavelli_assassin', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(related_name='assassin_set', to=orm['machiavelli.Player'])),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Country'])),
        ))
        db.send_create_signal('machiavelli', ['Assassin'])

        # Adding unique constraint on 'Assassin', fields ['owner', 'target']
        db.create_unique('machiavelli_assassin', ['owner_id', 'target_id'])

        # Adding model 'Assassination'
        db.create_table('machiavelli_assassination', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('killer', self.gf('django.db.models.fields.related.ForeignKey')(related_name='assassination_attempts', to=orm['machiavelli.Player'])),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(related_name='assassination_targets', to=orm['machiavelli.Player'])),
            ('ducats', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal('machiavelli', ['Assassination'])


        # --- Phase 3: Add new columns/fields ---

        # Adding field 'Unit.siege_stage'
        db.add_column('machiavelli_unit', 'siege_stage',
                      self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0),
                      keep_default=False)

        # Adding field 'Unit.coast'
        db.add_column('machiavelli_unit', 'coast',
                      self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Unit.cost'
        db.add_column('machiavelli_unit', 'cost',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=3),
                      keep_default=False)

        # Adding field 'Unit.power'
        db.add_column('machiavelli_unit', 'power',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=1),
                      keep_default=False)

        # Adding field 'Unit.loyalty'
        db.add_column('machiavelli_unit', 'loyalty',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=1),
                      keep_default=False)

        # Adding field 'Area.coast_names'
        db.add_column('machiavelli_area', 'coast_names',
                      self.gf('django.db.models.fields.CharField')(max_length=10, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Order.destination_coast'
        db.add_column('machiavelli_order', 'destination_coast',
                      self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Order.subdestination_coast'
        db.add_column('machiavelli_order', 'subdestination_coast',
                      self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True),
                      keep_default=False)

        # Adding field 'RetreatOrder.coast'
        db.add_column('machiavelli_retreatorder', 'coast',
                      self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True),
                      keep_default=False)


        # --- Phase 4: Alter existing columns/fields ---

        # Changing field 'Game.victory_condition_type'
        db.alter_column('machiavelli_game', 'victory_condition_type', self.gf('django.db.models.fields.CharField')(max_length=15))


        # --- Phase 5: Add new constraints ---

        # Adding unique constraint on 'Order', fields ['unit', 'confirmed']
        db.create_unique('machiavelli_order', ['unit_id', 'confirmed'])


    def backwards(self, orm):
        # --- Phase 1: Remove new constraints ---
        # Removing unique constraint on 'Order', fields ['unit', 'confirmed']
        db.delete_unique('machiavelli_order', ['unit_id', 'confirmed'])


        # --- Phase 2: Alter columns/fields back ---
        # Changing field 'Game.victory_condition_type'
        db.alter_column('machiavelli_game', 'victory_condition_type', self.gf('django.db.models.fields.CharField')(max_length=10))


        # --- Phase 3: Remove new columns/fields ---
        # Deleting field 'Unit.siege_stage'
        db.delete_column('machiavelli_unit', 'siege_stage')

        # Deleting field 'Unit.coast'
        db.delete_column('machiavelli_unit', 'coast')

        # Deleting field 'Unit.cost'
        db.delete_column('machiavelli_unit', 'cost')

        # Deleting field 'Unit.power'
        db.delete_column('machiavelli_unit', 'power')

        # Deleting field 'Unit.loyalty'
        db.delete_column('machiavelli_unit', 'loyalty')

        # Deleting field 'Area.coast_names'
        db.delete_column('machiavelli_area', 'coast_names')

        # Deleting field 'Order.destination_coast'
        db.delete_column('machiavelli_order', 'destination_coast')

        # Deleting field 'Order.subdestination_coast'
        db.delete_column('machiavelli_order', 'subdestination_coast')

        # Deleting field 'RetreatOrder.coast'
        db.delete_column('machiavelli_retreatorder', 'coast')


        # --- Phase 4: Remove new models ---
        # Removing unique constraint on 'Assassin', fields ['owner', 'target']
        db.delete_unique('machiavelli_assassin', ['owner_id', 'target_id'])

        # Deleting model 'Expense'
        db.delete_table('machiavelli_expense')

        # Deleting model 'Rebellion'
        db.delete_table('machiavelli_rebellion')

        # Deleting model 'Loan'
        db.delete_table('machiavelli_loan')

        # Deleting model 'Assassin'
        db.delete_table('machiavelli_assassin')

        # Deleting model 'Assassination'
        db.delete_table('machiavelli_assassination')


        # --- Phase 5: Add old fields/constraints back ---
        # Adding unique constraint on 'Order', fields ['unit', 'player']
        # Note: This assumes player_id was not nullable before. If it was, adjust accordingly.
        db.create_unique('machiavelli_order', ['unit_id', 'player_id'])

        # Adding field 'Unit.besieging'
        db.add_column('machiavelli_unit', 'besieging',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Area.control_income'
        db.add_column('machiavelli_area', 'control_income',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=0),
                      keep_default=False)

        # Adding field 'Area.garrison_income'
        db.add_column('machiavelli_area', 'garrison_income',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=0),
                      keep_default=False)


    # The 'models' dictionary below represents the state *BEFORE* this migration.
    # It's crucial for South to calculate the changes correctly.
    # This is based on the original code provided and the changes identified.
    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        # --- Machiavelli Models (State BEFORE this migration) ---
        'machiavelli.aftoken': {
            'Meta': {'object_name': 'AFToken'},
            'area': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['machiavelli.Area']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'x': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'y': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'machiavelli.area': {
            'Meta': {'ordering': "('code',)", 'object_name': 'Area'},
            'borders': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'borders_rel_+'", 'editable': 'False', 'to': "orm['machiavelli.Area']"}),
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '5'}),
            # 'control_income': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}), # Removed in this migration
            # 'garrison_income': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}), # Removed in this migration
            'has_city': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_port': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_coast': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_fortified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_sea': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'major_city_income': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'name': ('machiavelli.fields.AutoTranslateField', [], {'max_length': '20'})
            # 'coast_names' was added in this migration
        },
        'machiavelli.configuration': {
            'Meta': {'object_name': 'Configuration'},
            'assassinations': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'bribes': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'conquering': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'excommunication': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'famine': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'finances': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'game': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['machiavelli.Game']", 'unique': 'True'}),
            'gossip': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lenders': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'plague': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'special_units': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'storms': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'strategic': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'unbalanced_loans': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'machiavelli.controltoken': {
            'Meta': {'object_name': 'ControlToken'},
            'area': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['machiavelli.Area']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'x': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'y': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'machiavelli.country': {
            'Meta': {'object_name': 'Country'},
            'can_excommunicate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'css_class': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('machiavelli.fields.AutoTranslateField', [], {'unique': 'True', 'max_length': '20'}),
            'special_units': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['machiavelli.SpecialUnit']", 'symmetrical': 'False'}),
            'static_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '20'})
        },
        'machiavelli.disabledarea': {
            'Meta': {'unique_together': "(('scenario', 'area'),)", 'object_name': 'DisabledArea'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'scenario': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Scenario']"})
        },
        'machiavelli.game': {
            'Meta': {'object_name': 'Game'},
            'cities_to_win': ('django.db.models.fields.PositiveIntegerField', [], {'default': '12'}),
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'fast': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_phase_change': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'map_outdated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'phase': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'scenario': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Scenario']"}),
            'season': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slots': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '20'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'time_limit': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'victory_condition_type': ('django.db.models.fields.CharField', [], {'default': "'basic'", 'max_length': '10'}), # max_length was 10
            'visible': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'year': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'machiavelli.gamearea': {
            'Meta': {'object_name': 'GameArea'},
            'board_area': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Area']"}),
            'famine': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Player']", 'null': 'True', 'blank': 'True'}),
            'standoff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'storm': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'machiavelli.gtoken': {
            'Meta': {'object_name': 'GToken'},
            'area': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['machiavelli.Area']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'x': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'y': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'machiavelli.home': {
            'Meta': {'unique_together': "(('scenario', 'country', 'area'),)", 'object_name': 'Home'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Area']"}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Country']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_home': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'scenario': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Scenario']"})
        },
        'machiavelli.invitation': {
            'Meta': {'unique_together': "(('game', 'user'),)", 'object_name': 'Invitation'},
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'machiavelli.order': {
            'Meta': {'unique_together': "(('unit', 'player'),)", 'object_name': 'Order'}, # Old unique_together
            'code': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'confirmed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'destination': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'targeted_by_orders'", 'null': 'True', 'to': "orm['machiavelli.GameArea']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Player']", 'null': 'True'}),
            'subcode': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'subdestination': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sub_targeted_by_orders'", 'null': 'True', 'to': "orm['machiavelli.GameArea']"}),
            'subunit': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'affecting_orders'", 'null': 'True', 'to': "orm['machiavelli.Unit']"}),
            'subtype': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Unit']"})
            # destination_coast, subdestination_coast added in this migration
        },
        'machiavelli.player': {
            'Meta': {'object_name': 'Player'},
            'assassinated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'conqueror': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'conquered'", 'null': 'True', 'to': "orm['machiavelli.Player']"}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Country']", 'null': 'True', 'blank': 'True'}),
            'defaulted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'done': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'double_income': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ducats': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'eliminated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'excommunicated': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Game']"}),
            'has_sentenced': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_excommunicated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'may_excommunicate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'pope_excommunicated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'static_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '20'}),
            'step': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'machiavelli.retreatorder': {
            'Meta': {'object_name': 'RetreatOrder'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.GameArea']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Unit']"})
            # coast added in this migration
        },
        'machiavelli.revolution': {
            'Meta': {'object_name': 'Revolution'},
            'government': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Player']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'opposition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'machiavelli.scenario': {
            'Meta': {'object_name': 'Scenario'},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '16'}),
            'number_of_players': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'start_year': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'title': ('machiavelli.fields.AutoTranslateField', [], {'max_length': '128'})
        },
        'machiavelli.score': {
            'Meta': {'object_name': 'Score'},
            'cities': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Country']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'points': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'position': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'machiavelli.setup': {
            'Meta': {'unique_together': "(('scenario', 'area', 'unit_type'),)", 'object_name': 'Setup'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Area']"}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Country']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'scenario': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Scenario']"}),
            'unit_type': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'machiavelli.specialunit': {
            'Meta': {'object_name': 'SpecialUnit'},
            'cost': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'loyalty': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'power': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'static_title': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'title': ('machiavelli.fields.AutoTranslateField', [], {'max_length': '50'})
        },
        'machiavelli.turnlog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'TurnLog'},
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.TextField', [], {}),
            'phase': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'season': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'year': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'machiavelli.unit': {
            'Meta': {'object_name': 'Unit'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.GameArea']"}),
            # 'besieging': ('django.db.models.fields.BooleanField', [], {'default': 'False'}), # Removed in this migration
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'must_retreat': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '5', 'blank': 'True'}),
            'paid': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'placed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Player']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '1'})
            # siege_stage, coast, cost, power, loyalty added in this migration
        },
        'machiavelli.whisper': {
            'Meta': {'ordering': "['-created_at']", 'unique_together': "(('game', 'order'),)", 'object_name': 'Whisper'},
            'as_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['machiavelli']