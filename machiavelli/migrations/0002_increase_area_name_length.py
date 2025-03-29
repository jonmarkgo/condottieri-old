# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Area.name'
        db.alter_column('machiavelli_area', 'name', self.gf('machiavelli.fields.AutoTranslateField')(max_length=30))

    def backwards(self, orm):

        # Changing field 'Area.name'
        db.alter_column('machiavelli_area', 'name', self.gf('machiavelli.fields.AutoTranslateField')(max_length=20))

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
        'machiavelli.aftoken': {
            'Meta': {'object_name': 'AFToken'},
            'area': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['machiavelli.Area']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'x': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'y': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'machiavelli.area': {
            'Meta': {'ordering': "('code',)", 'object_name': 'Area'},
            'borders': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'borders_rel_+'", 'to': "orm['machiavelli.Area']"}),
            'coast_names': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '5'}),
            'has_city': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_port': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_coast': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_fortified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_sea': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'major_city_income': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'name': ('machiavelli.fields.AutoTranslateField', [], {'max_length': '30'})
        },
        'machiavelli.assassin': {
            'Meta': {'unique_together': "(('owner', 'target'),)", 'object_name': 'Assassin'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'assassin_set'", 'to': "orm['machiavelli.Player']"}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Country']"})
        },
        'machiavelli.assassination': {
            'Meta': {'object_name': 'Assassination'},
            'ducats': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'killer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'assassination_attempts'", 'to': "orm['machiavelli.Player']"}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'assassination_targets'", 'to': "orm['machiavelli.Player']"})
        },
        'machiavelli.cityincome': {
            'Meta': {'unique_together': "(('city', 'scenario'),)", 'object_name': 'CityIncome'},
            'city': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'scenario': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Scenario']"})
        },
        'machiavelli.configuration': {
            'Meta': {'object_name': 'Configuration'},
            'assassinations': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'bribes': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'bribes_anywhere': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'bribes_via_ally': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'conquering': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'excommunication': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'famine': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'finances': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'game': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['machiavelli.Game']", 'unique': 'True'}),
            'gossip': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lenders': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'no_luck': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'plague': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'random_assassins': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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
        'machiavelli.expense': {
            'Meta': {'object_name': 'Expense'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.GameArea']", 'null': 'True', 'blank': 'True'}),
            'confirmed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ducats': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Player']"}),
            'type': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Unit']", 'null': 'True', 'blank': 'True'})
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
            'victory_condition_type': ('django.db.models.fields.CharField', [], {'default': "'basic'", 'max_length': '15'}),
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
        'machiavelli.loan': {
            'Meta': {'object_name': 'Loan'},
            'debt': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'due_season': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'due_year': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interest_rate': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'player': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['machiavelli.Player']", 'unique': 'True'}),
            'principal': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'machiavelli.order': {
            'Meta': {'unique_together': "(('unit', 'confirmed'),)", 'object_name': 'Order'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'confirmed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'destination': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'targeted_by_orders'", 'null': 'True', 'to': "orm['machiavelli.GameArea']"}),
            'destination_coast': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Player']", 'null': 'True'}),
            'subcode': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'subdestination': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sub_targeted_by_orders'", 'null': 'True', 'to': "orm['machiavelli.GameArea']"}),
            'subdestination_coast': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'subtype': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'subunit': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'affecting_orders'", 'null': 'True', 'to': "orm['machiavelli.Unit']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Unit']"})
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
        'machiavelli.rebellion': {
            'Meta': {'object_name': 'Rebellion'},
            'area': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['machiavelli.GameArea']", 'unique': 'True'}),
            'garrisoned': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Player']"})
        },
        'machiavelli.retreatorder': {
            'Meta': {'object_name': 'RetreatOrder'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.GameArea']", 'null': 'True', 'blank': 'True'}),
            'coast': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Unit']"})
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
        'machiavelli.treasury': {
            'Meta': {'unique_together': "(('scenario', 'country'),)", 'object_name': 'Treasury'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Country']"}),
            'double': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ducats': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'scenario': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Scenario']"})
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
            'coast': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'cost': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'loyalty': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'must_retreat': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '5', 'blank': 'True'}),
            'paid': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'placed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['machiavelli.Player']"}),
            'power': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'siege_stage': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '1'})
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