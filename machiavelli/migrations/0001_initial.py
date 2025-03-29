# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Scenario'
        db.create_table('machiavelli_scenario', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=16)),
            ('title', self.gf('machiavelli.fields.AutoTranslateField')(max_length=128)),
            ('start_year', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('number_of_players', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('machiavelli', ['Scenario'])

        # Adding model 'SpecialUnit'
        db.create_table('machiavelli_specialunit', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('static_title', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('title', self.gf('machiavelli.fields.AutoTranslateField')(max_length=50)),
            ('cost', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('power', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('loyalty', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('machiavelli', ['SpecialUnit'])

        # Adding model 'Country'
        db.create_table('machiavelli_country', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('machiavelli.fields.AutoTranslateField')(unique=True, max_length=20)),
            ('css_class', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
            ('can_excommunicate', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('static_name', self.gf('django.db.models.fields.CharField')(default='', max_length=20)),
        ))
        db.send_create_signal('machiavelli', ['Country'])

        # Adding M2M table for field special_units on 'Country'
        db.create_table('machiavelli_country_special_units', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('country', models.ForeignKey(orm['machiavelli.country'], null=False)),
            ('specialunit', models.ForeignKey(orm['machiavelli.specialunit'], null=False))
        ))
        db.create_unique('machiavelli_country_special_units', ['country_id', 'specialunit_id'])

        # Adding model 'Area'
        db.create_table('machiavelli_area', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('machiavelli.fields.AutoTranslateField')(max_length=20)),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=5)),
            ('is_sea', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_coast', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('has_city', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_fortified', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('has_port', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('major_city_income', self.gf('django.db.models.fields.PositiveIntegerField')(default=None, null=True, blank=True)),
            ('coast_names', self.gf('django.db.models.fields.CharField')(max_length=10, null=True, blank=True)),
        ))
        db.send_create_signal('machiavelli', ['Area'])

        # Adding M2M table for field borders on 'Area'
        db.create_table('machiavelli_area_borders', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_area', models.ForeignKey(orm['machiavelli.area'], null=False)),
            ('to_area', models.ForeignKey(orm['machiavelli.area'], null=False))
        ))
        db.create_unique('machiavelli_area_borders', ['from_area_id', 'to_area_id'])

        # Adding model 'DisabledArea'
        db.create_table('machiavelli_disabledarea', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('scenario', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Scenario'])),
            ('area', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Area'])),
        ))
        db.send_create_signal('machiavelli', ['DisabledArea'])

        # Adding unique constraint on 'DisabledArea', fields ['scenario', 'area']
        db.create_unique('machiavelli_disabledarea', ['scenario_id', 'area_id'])

        # Adding model 'Home'
        db.create_table('machiavelli_home', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('scenario', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Scenario'])),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Country'])),
            ('area', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Area'])),
            ('is_home', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('machiavelli', ['Home'])

        # Adding unique constraint on 'Home', fields ['scenario', 'country', 'area']
        db.create_unique('machiavelli_home', ['scenario_id', 'country_id', 'area_id'])

        # Adding model 'Setup'
        db.create_table('machiavelli_setup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('scenario', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Scenario'])),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Country'], null=True, blank=True)),
            ('area', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Area'])),
            ('unit_type', self.gf('django.db.models.fields.CharField')(max_length=1)),
        ))
        db.send_create_signal('machiavelli', ['Setup'])

        # Adding unique constraint on 'Setup', fields ['scenario', 'area', 'unit_type']
        db.create_unique('machiavelli_setup', ['scenario_id', 'area_id', 'unit_type'])

        # Adding model 'Treasury'
        db.create_table('machiavelli_treasury', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('scenario', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Scenario'])),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Country'])),
            ('ducats', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('double', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('machiavelli', ['Treasury'])

        # Adding unique constraint on 'Treasury', fields ['scenario', 'country']
        db.create_unique('machiavelli_treasury', ['scenario_id', 'country_id'])

        # Adding model 'CityIncome'
        db.create_table('machiavelli_cityincome', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('city', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Area'])),
            ('scenario', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Scenario'])),
        ))
        db.send_create_signal('machiavelli', ['CityIncome'])

        # Adding unique constraint on 'CityIncome', fields ['city', 'scenario']
        db.create_unique('machiavelli_cityincome', ['city_id', 'scenario_id'])

        # Adding model 'Game'
        db.create_table('machiavelli_game', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=20)),
            ('year', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('season', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('phase', self.gf('django.db.models.fields.PositiveIntegerField')(default=0, null=True, blank=True)),
            ('slots', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('scenario', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Scenario'])),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('visible', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('map_outdated', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('time_limit', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('last_phase_change', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('started', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('finished', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('victory_condition_type', self.gf('django.db.models.fields.CharField')(default='basic', max_length=15)),
            ('cities_to_win', self.gf('django.db.models.fields.PositiveIntegerField')(default=12)),
            ('fast', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('private', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('comment', self.gf('django.db.models.fields.TextField')(max_length=255, null=True, blank=True)),
        ))
        db.send_create_signal('machiavelli', ['Game'])

        # Adding model 'GameArea'
        db.create_table('machiavelli_gamearea', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Game'])),
            ('board_area', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Area'])),
            ('player', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Player'], null=True, blank=True)),
            ('standoff', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('famine', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('storm', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('machiavelli', ['GameArea'])

        # Adding model 'Score'
        db.create_table('machiavelli_score', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Game'])),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Country'])),
            ('points', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('cities', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('position', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('machiavelli', ['Score'])

        # Adding model 'Player'
        db.create_table('machiavelli_player', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Game'])),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Country'], null=True, blank=True)),
            ('done', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('eliminated', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('conqueror', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='conquered', null=True, to=orm['machiavelli.Player'])),
            ('excommunicated', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('assassinated', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('defaulted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('ducats', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('double_income', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('may_excommunicate', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('static_name', self.gf('django.db.models.fields.CharField')(default='', max_length=20)),
            ('step', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('has_sentenced', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_excommunicated', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('pope_excommunicated', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('machiavelli', ['Player'])

        # Adding model 'Revolution'
        db.create_table('machiavelli_revolution', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('government', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Player'])),
            ('opposition', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
        ))
        db.send_create_signal('machiavelli', ['Revolution'])

        # Adding model 'Unit'
        db.create_table('machiavelli_unit', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('area', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.GameArea'])),
            ('player', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Player'])),
            ('siege_stage', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
            ('must_retreat', self.gf('django.db.models.fields.CharField')(default='', max_length=5, blank=True)),
            ('placed', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('paid', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('cost', self.gf('django.db.models.fields.PositiveIntegerField')(default=3)),
            ('power', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('loyalty', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('coast', self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True)),
        ))
        db.send_create_signal('machiavelli', ['Unit'])

        # Adding model 'Order'
        db.create_table('machiavelli_order', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Unit'])),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('destination', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='targeted_by_orders', null=True, to=orm['machiavelli.GameArea'])),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
            ('subunit', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='affecting_orders', null=True, to=orm['machiavelli.Unit'])),
            ('subcode', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
            ('subdestination', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='sub_targeted_by_orders', null=True, to=orm['machiavelli.GameArea'])),
            ('subtype', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
            ('confirmed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('player', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Player'], null=True)),
            ('destination_coast', self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True)),
            ('subdestination_coast', self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True)),
        ))
        db.send_create_signal('machiavelli', ['Order'])

        # Adding unique constraint on 'Order', fields ['unit', 'confirmed']
        db.create_unique('machiavelli_order', ['unit_id', 'confirmed'])

        # Adding model 'RetreatOrder'
        db.create_table('machiavelli_retreatorder', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Unit'])),
            ('area', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.GameArea'], null=True, blank=True)),
            ('coast', self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True)),
        ))
        db.send_create_signal('machiavelli', ['RetreatOrder'])

        # Adding model 'ControlToken'
        db.create_table('machiavelli_controltoken', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('area', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['machiavelli.Area'], unique=True)),
            ('x', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('y', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('machiavelli', ['ControlToken'])

        # Adding model 'GToken'
        db.create_table('machiavelli_gtoken', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('area', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['machiavelli.Area'], unique=True)),
            ('x', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('y', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('machiavelli', ['GToken'])

        # Adding model 'AFToken'
        db.create_table('machiavelli_aftoken', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('area', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['machiavelli.Area'], unique=True)),
            ('x', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('y', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('machiavelli', ['AFToken'])

        # Adding model 'TurnLog'
        db.create_table('machiavelli_turnlog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Game'])),
            ('year', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('season', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('phase', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('log', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('machiavelli', ['TurnLog'])

        # Adding model 'Configuration'
        db.create_table('machiavelli_configuration', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['machiavelli.Game'], unique=True)),
            ('finances', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('assassinations', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('bribes', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('excommunication', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('special_units', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('strategic', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('lenders', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('unbalanced_loans', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('conquering', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('famine', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('plague', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('storms', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('gossip', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('bribes_via_ally', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('bribes_anywhere', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('random_assassins', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('no_luck', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('machiavelli', ['Configuration'])

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
            ('area', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['machiavelli.GameArea'], unique=True)),
            ('player', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Player'])),
            ('garrisoned', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('machiavelli', ['Rebellion'])

        # Adding model 'Loan'
        db.create_table('machiavelli_loan', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
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

        # Adding model 'Whisper'
        db.create_table('machiavelli_whisper', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('as_admin', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Game'])),
            ('text', self.gf('django.db.models.fields.CharField')(max_length=140)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal('machiavelli', ['Whisper'])

        # Adding unique constraint on 'Whisper', fields ['game', 'order']
        db.create_unique('machiavelli_whisper', ['game_id', 'order'])

        # Adding model 'Invitation'
        db.create_table('machiavelli_invitation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['machiavelli.Game'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('message', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
        ))
        db.send_create_signal('machiavelli', ['Invitation'])

        # Adding unique constraint on 'Invitation', fields ['game', 'user']
        db.create_unique('machiavelli_invitation', ['game_id', 'user_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'Invitation', fields ['game', 'user']
        db.delete_unique('machiavelli_invitation', ['game_id', 'user_id'])

        # Removing unique constraint on 'Whisper', fields ['game', 'order']
        db.delete_unique('machiavelli_whisper', ['game_id', 'order'])

        # Removing unique constraint on 'Assassin', fields ['owner', 'target']
        db.delete_unique('machiavelli_assassin', ['owner_id', 'target_id'])

        # Removing unique constraint on 'Order', fields ['unit', 'confirmed']
        db.delete_unique('machiavelli_order', ['unit_id', 'confirmed'])

        # Removing unique constraint on 'CityIncome', fields ['city', 'scenario']
        db.delete_unique('machiavelli_cityincome', ['city_id', 'scenario_id'])

        # Removing unique constraint on 'Treasury', fields ['scenario', 'country']
        db.delete_unique('machiavelli_treasury', ['scenario_id', 'country_id'])

        # Removing unique constraint on 'Setup', fields ['scenario', 'area', 'unit_type']
        db.delete_unique('machiavelli_setup', ['scenario_id', 'area_id', 'unit_type'])

        # Removing unique constraint on 'Home', fields ['scenario', 'country', 'area']
        db.delete_unique('machiavelli_home', ['scenario_id', 'country_id', 'area_id'])

        # Removing unique constraint on 'DisabledArea', fields ['scenario', 'area']
        db.delete_unique('machiavelli_disabledarea', ['scenario_id', 'area_id'])

        # Deleting model 'Scenario'
        db.delete_table('machiavelli_scenario')

        # Deleting model 'SpecialUnit'
        db.delete_table('machiavelli_specialunit')

        # Deleting model 'Country'
        db.delete_table('machiavelli_country')

        # Removing M2M table for field special_units on 'Country'
        db.delete_table('machiavelli_country_special_units')

        # Deleting model 'Area'
        db.delete_table('machiavelli_area')

        # Removing M2M table for field borders on 'Area'
        db.delete_table('machiavelli_area_borders')

        # Deleting model 'DisabledArea'
        db.delete_table('machiavelli_disabledarea')

        # Deleting model 'Home'
        db.delete_table('machiavelli_home')

        # Deleting model 'Setup'
        db.delete_table('machiavelli_setup')

        # Deleting model 'Treasury'
        db.delete_table('machiavelli_treasury')

        # Deleting model 'CityIncome'
        db.delete_table('machiavelli_cityincome')

        # Deleting model 'Game'
        db.delete_table('machiavelli_game')

        # Deleting model 'GameArea'
        db.delete_table('machiavelli_gamearea')

        # Deleting model 'Score'
        db.delete_table('machiavelli_score')

        # Deleting model 'Player'
        db.delete_table('machiavelli_player')

        # Deleting model 'Revolution'
        db.delete_table('machiavelli_revolution')

        # Deleting model 'Unit'
        db.delete_table('machiavelli_unit')

        # Deleting model 'Order'
        db.delete_table('machiavelli_order')

        # Deleting model 'RetreatOrder'
        db.delete_table('machiavelli_retreatorder')

        # Deleting model 'ControlToken'
        db.delete_table('machiavelli_controltoken')

        # Deleting model 'GToken'
        db.delete_table('machiavelli_gtoken')

        # Deleting model 'AFToken'
        db.delete_table('machiavelli_aftoken')

        # Deleting model 'TurnLog'
        db.delete_table('machiavelli_turnlog')

        # Deleting model 'Configuration'
        db.delete_table('machiavelli_configuration')

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

        # Deleting model 'Whisper'
        db.delete_table('machiavelli_whisper')

        # Deleting model 'Invitation'
        db.delete_table('machiavelli_invitation')


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
            'name': ('machiavelli.fields.AutoTranslateField', [], {'max_length': '20'})
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