# Project Focus: condo2

**Current Goal:** Project directory structure and information

**Project Context:**
Type: Language: python
Target Users: Users of condo2
Main Functionality: Project directory structure and information
Key Requirements:
- Type: Python Project
- Language: python
- Framework: django
- File and directory tracking
- Automatic updates

**Development Guidelines:**
- Keep code modular and reusable
- Follow best practices for the project type
- Maintain clean separation of concerns

# 📁 Project Structure
├─ 📄 __init__.py (6 lines) - Python script containing project logic
├─ 📄 load_fixtures.py (54 lines) - Python script containing project logic
├─ 📄 local_settings.py (49 lines) - Python script containing project logic
├─ 📄 manage.py (28 lines) - Python script containing project logic
├─ 📄 settings.py (362 lines) - Python script containing project logic
├─ 📄 timezone_fix_middleware.py (53 lines) - Python script containing project logic
├─ 📄 urls.py (88 lines) - Python script containing project logic
├─ 📁 clones
│  ├─ 📄 __init__.py (0 lines) - Python script containing project logic
│  ├─ 📄 admin.py (9 lines) - Python script containing project logic
│  ├─ 📄 models.py (44 lines) - Python script containing project logic
│  ├─ 📄 tests.py (23 lines) - Python script containing project logic
│  └─ 📄 views.py (1 lines) - Python script containing project logic
├─ 📁 condottieri_common
│  ├─ 📄 __init__.py (0 lines) - Python script containing project logic
│  ├─ 📄 admin.py (5 lines) - Python script containing project logic
│  ├─ 📄 models.py (56 lines) - Python script containing project logic
│  └─ 📁 management
│     ├─ 📄 __init__.py (0 lines) - Python script containing project logic
│     └─ 📁 commands
│        ├─ 📄 __init__.py (0 lines) - Python script containing project logic
│        ├─ 📄 backupdb.py (70 lines) - Python script containing project logic
│        └─ 📄 update_weighted_scores.py (64 lines) - Python script containing project logic
├─ 📁 condottieri_events
│  ├─ 📄 __init__.py (0 lines) - Python script containing project logic
│  ├─ 📄 admin.py (101 lines) - Python script containing project logic
│  ├─ 📄 models.py (756 lines) - Python script containing project logic
│  ├─ 📄 paginator.py (168 lines) - Python script containing project logic
│  ├─ 📄 tests.py (23 lines) - Python script containing project logic
│  ├─ 📄 views.py (1 lines) - Python script containing project logic
│  └─ 📁 management
│     ├─ 📄 __init__.py (0 lines) - Python script containing project logic
│     └─ 📁 commands
│        ├─ 📄 __init__.py (0 lines) - Python script containing project logic
│        └─ 📄 clean_events.py (24 lines) - Python script containing project logic
├─ 📁 condottieri_help
│  ├─ 📄 __init__.py (0 lines) - Python script containing project logic
│  ├─ 📄 models.py (3 lines) - Python script containing project logic
│  ├─ 📄 tests.py (23 lines) - Python script containing project logic
│  ├─ 📄 urls.py (17 lines) - Python script containing project logic
│  └─ 📄 views.py (1 lines) - Python script containing project logic
├─ 📁 condottieri_messages
│  ├─ 📄 __init__.py (0 lines) - Python script containing project logic
│  ├─ 📄 admin.py (8 lines) - Python script containing project logic
│  ├─ 📄 exceptions.py (29 lines) - Python script containing project logic
│  ├─ 📄 forms.py (36 lines) - Python script containing project logic
│  ├─ 📄 management.py (13 lines) - Python script containing project logic
│  ├─ 📄 models.py (64 lines) - Python script containing project logic
│  ├─ 📄 tests.py (23 lines) - Python script containing project logic
│  ├─ 📄 urls.py (28 lines) - Python script containing project logic
│  └─ 📄 views.py (258 lines) - Python script containing project logic
├─ 📁 condottieri_profiles
│  ├─ 📄 __init__.py (0 lines) - Python script containing project logic
│  ├─ 📄 admin.py (13 lines) - Python script containing project logic
│  ├─ 📄 forms.py (8 lines) - Python script containing project logic
│  ├─ 📄 models.py (132 lines) - Python script containing project logic
│  ├─ 📄 tests.py (23 lines) - Python script containing project logic
│  ├─ 📄 urls.py (13 lines) - Python script containing project logic
│  ├─ 📄 views.py (55 lines) - Python script containing project logic
│  └─ 📁 management
│     ├─ 📄 __init__.py (1 lines) - Python script containing project logic
│     ├─ 📄 base.py (16 lines) - Python script containing project logic
│     └─ 📁 commands
│        ├─ 📄 __init__.py (0 lines) - Python script containing project logic
│        └─ 📄 heal_karma.py (32 lines) - Python script containing project logic
├─ 📁 doc
│  └─ 📄 conf.py (216 lines) - Python script containing project logic
└─ 📁 machiavelli
   ├─ 📄 __init__.py (0 lines) - Python script containing project logic
   ├─ 📄 admin.py (181 lines) - Python script containing project logic
   ├─ 📄 dice.py (33 lines) - Python script containing project logic
   ├─ 📄 disasters.py (122 lines) - Python script containing project logic
   ├─ 📄 exceptions.py (30 lines) - Python script containing project logic
   ├─ 📄 fields.py (43 lines) - Python script containing project logic
   ├─ 📄 finances.py (54 lines) - Python script containing project logic
   ├─ 📄 forms.py (523 lines) - Python script containing project logic
   ├─ 📄 graphics.py (186 lines) - Python script containing project logic
   ├─ 📄 logging.py (59 lines) - Python script containing project logic
   ├─ 📄 middleware.py (71 lines) - Python script containing project logic
   ├─ 📄 models.py (3420 lines) - Python script containing project logic
   ├─ 📄 signals.py (59 lines) - Python script containing project logic
   ├─ 📄 translate.py (102 lines) - Python script containing project logic
   ├─ 📄 urls.py (51 lines) - Python script containing project logic
   ├─ 📄 views.py (1570 lines) - Python script containing project logic
   ├─ 📁 management
   │  ├─ 📄 __init__.py (1 lines) - Python script containing project logic
   │  ├─ 📄 base.py (40 lines) - Python script containing project logic
   │  └─ 📁 commands
   │     ├─ 📄 __init__.py (0 lines) - Python script containing project logic
   │     ├─ 📄 check_turns.py (38 lines) - Python script containing project logic
   │     ├─ 📄 clean_logs.py (21 lines) - Python script containing project logic
   │     └─ 📄 clean_notices.py (21 lines) - Python script containing project logic
   ├─ 📁 migrations
   │  └─ 📄 __init__.py (0 lines) - Python script containing project logic
   └─ 📁 templatetags
      ├─ 📄 __init__.py (0 lines) - Python script containing project logic
      ├─ 📄 game_icons.py (36 lines) - Python script containing project logic
      └─ 📄 stars.py (39 lines) - Python script containing project logic

# 🔍 Key Files with Methods

`condottieri_messages/admin.py` (8 lines)
Functions:
- LetterAdmin

`clones/admin.py` (9 lines)
Functions:
- FingerprintAdmin

`condottieri_profiles/admin.py` (13 lines)
Functions:
- CondottieriProfileAdmin
- SpokenLanguageInline

`machiavelli/admin.py` (181 lines)
Functions:
- AFTokenInline
- AreaAdmin
- AssassinAdmin
- AssassinationAdmin
- CityIncomeInline
- ConfigurationInline
- ControlTokenInline
- CountryAdmin
- DisabledAreaInline
- ExpenseAdmin
- GTokenInline
- GameAdmin
- GameAreaAdmin
- HomeInline
- InvitationAdmin
- LoanAdmin
- OrderAdmin
- PlayerAdmin
- RebellionAdmin
- RetreatOrderAdmin
- RevolutionAdmin
- ScenarioAdmin
- ScoreAdmin
- SetupAdmin
- SetupInline
- SpecialUnitAdmin
- TreasuryInline
- TurnLogAdmin
- UnitAdmin
- WhisperAdmin
- check_finished_phase
- make_map
- player_info
- player_list
- redraw_map

`condottieri_events/admin.py` (101 lines)
Functions:
- BaseEventAdmin
- ControlEventAdmin
- ConversionEventAdmin
- CountryEventAdmin
- DisasterEventAdmin
- DisbandEventAdmin
- ExpenseEventAdmin
- IncomeEventAdmin
- MovementEventAdmin
- NewUnitEventAdmin
- OrderEventAdmin
- RetreatEventAdmin
- StandoffEventAdmin
- UnitEventAdmin

`condottieri_common/management/commands/backupdb.py` (70 lines)
Functions:
- Command
- do_mysql_backup
- do_postgresql_backup
- handle

`condottieri_profiles/management/base.py` (16 lines)
Functions:
- create_notice_types

`machiavelli/management/base.py` (40 lines)
Functions:
- create_notice_types

`machiavelli/management/commands/check_turns.py` (38 lines)
Functions:
- Command
- handle_noargs

`condottieri_events/management/commands/clean_events.py` (24 lines)
Functions:
- Command
- handle_noargs

`machiavelli/management/commands/clean_logs.py` (21 lines)
Functions:
- Command
- handle_noargs

`machiavelli/management/commands/clean_notices.py` (21 lines)
Functions:
- Command
- handle_noargs

`machiavelli/dice.py` (33 lines)
Functions:
- check_one_six
- roll_1d6
- roll_2d6

`machiavelli/disasters.py` (122 lines)
Functions:
- get_column
- get_famine
- get_plague
- get_provinces
- get_row
- get_storms
- get_year

`condottieri_messages/exceptions.py` (29 lines)
Functions:
- Error
- LetterError

`machiavelli/exceptions.py` (30 lines)
Functions:
- Error
- WrongUnitCount

`machiavelli/fields.py` (43 lines)
Functions:
- AutoTranslateField
- to_python

`machiavelli/finances.py` (54 lines)
Functions:
- get_ducats

`condottieri_messages/forms.py` (36 lines)
Functions:
- LetterForm
- Meta

`condottieri_profiles/forms.py` (8 lines)
Functions:
- Meta
- ProfileForm

`machiavelli/forms.py` (523 lines)
Functions:
- AssassinationForm
- BaseReinforceFormSet
- BorrowForm
- ConfigurationForm
- DisbandForm
- ExpenseForm
- GameForm
- InvitationForm
- LendForm
- Media
- Meta
- OrderForm
- ReinforceForm
- RepayForm
- RetreatForm
- UnitForm
- UnitPaymentForm
- UnitPaymentMultipleChoiceField
- WhisperForm
- as_td
- clean
- get_valid_destinations
- get_valid_support_destinations
- label_from_instance
- make_assassination_form
- make_disband_form
- make_ducats_list
- make_expense_form
- make_order_form
- make_reinforce_form
- make_retreat_form
- make_unit_payment_form

`machiavelli/templatetags/game_icons.py` (36 lines)
Functions:
- rule_icons

`machiavelli/graphics.py` (186 lines)
Functions:
- make_map
- make_scenario_map
- make_thumb

`condottieri_profiles/management/commands/heal_karma.py` (32 lines)
Functions:
- Command
- handle_noargs

`load_fixtures.py` (54 lines)
Functions:
- load_areas
- load_other_fixtures

`local_settings.py` (49 lines)
Functions:
- create_connection

`machiavelli/logging.py` (59 lines)
Functions:
- save_snapshot

`condottieri_messages/management.py` (13 lines)
Functions:
- create_notice_types

`machiavelli/middleware.py` (71 lines)
Functions:
- DatabaseConnectionMiddleware
- TimezoneFixMiddleware
- _cursor
- convert_timezone
- new_get_db_prep_save
- process_exception
- process_request
- process_response

`condottieri_messages/models.py` (64 lines)
Functions:
- Letter
- get_absolute_url
- notify_new_letter
- update_letter_users

`clones/models.py` (44 lines)
Functions:
- Clone
- Fingerprint
- Meta

`condottieri_common/models.py` (56 lines)
Functions:
- Server
- outdate_ranking

`condottieri_profiles/models.py` (132 lines)
Functions:
- CondottieriProfile
- Meta
- SpokenLanguage
- add_overthrow
- adjust_karma
- average_score
- create_profile
- get_absolute_url
- has_languages
- overthrow

`machiavelli/models.py` (3420 lines)
Functions:
- AFToken
- Area
- Assassin
- Assassination
- CityIncome
- Configuration
- ControlToken
- Country
- DisabledArea
- Expense
- GToken
- Game
- GameArea
- Home
- Invasion
- Invitation
- Loan
- Meta
- Order
- Player
- Rebellion
- RetreatOrder
- Revolution
- Scenario
- Score
- Setup
- SpecialUnit
- Treasury
- TurnLog
- Unit
- UnitManager
- Whisper
- _next_season
- abbr
- accepts_type
- add_ducats
- adjust_units
- all_players_done
- announce_retreats
- as_dict
- as_li
- assassinate
- assign_incomes
- assign_initial_income
- assign_scores
- can_excommunicate
- can_forgive
- cancel_orders
- change_player
- check_assassination_rebellion
- check_bonus_time
- check_conquerings
- check_eliminated
- check_finished_phase
- check_loans
- check_min_karma
- check_next_phase
- check_rebellion
- check_winner
- checks
- clean_useless_data
- clear_phase_cache
- confirm
- controlled_home_cities
- controlled_home_country
- convert
- copy_country_data
- create_assassins
- create_configuration
- create_game_board
- delete
- delete_order
- describe
- describe_with_cost
- eliminate
- end_phase
- explain
- filter_convoys
- filter_supports
- filter_unreachable_attacks
- find_convoy_line
- force_phase_change
- format
- format_suborder
- game_over
- get_absolute_url
- get_adjacent_areas
- get_all_gameareas
- get_all_units
- get_areas_for_new_units
- get_attacked_area
- get_autonomous_setups
- get_average_karma
- get_average_score
- get_bonus_deadline
- get_conflict_areas
- get_control_income
- get_countries
- get_credit
- get_defender
- get_disabled_areas
- get_enabled_rules
- get_enemies
- get_expense_cost
- get_garrisons_income
- get_highest_karma
- get_income
- get_language
- get_map_url
- get_occupation_income
- get_order
- get_possible_retreats
- get_rebellions
- get_rivals
- get_setups
- get_slots
- get_time_status
- get_variable_income
- get_with_strength
- has_rebellion
- has_special_unit
- highest_score
- home_control_markers
- home_country
- in_last_seconds
- invade_area
- is_adjacent
- is_allowed
- is_bribe
- is_possible
- isinstance
- keys
- kill_plague_units
- list_with_strength
- log_event
- make_map
- map_changed
- map_saved
- mark_as_standoff
- mark_famine_areas
- mark_storm_areas
- new_phase
- next_phase_change
- notify_new_invitation
- notify_overthrow_attempt
- notify_players
- number_of_cities
- number_of_units
- place
- place_initial_garrisons
- place_initial_units
- placed_units_count
- player_joined
- player_list_ordered_by_cities
- possible_reinforcements
- preprocess_orders
- process_assassinations
- process_expenses
- process_orders
- process_retreats
- province_is_empty
- reset_players_cache
- resolve_auto_garrisons
- resolve_conflicts
- resolve_sieges
- retreat
- save
- set_conqueror
- set_excommunication
- shuffle_countries
- supportable_order
- time_exceeded
- time_is_exceeded
- time_to_limit
- to_autonomous
- tweet_message
- tweet_new_game
- tweet_new_scenario
- tweet_results
- undo
- units_to_place
- unread_count
- unset_excommunication
- update_controls
- whisper_order

`condottieri_events/models.py` (756 lines)
Functions:
- BaseEvent
- ControlEvent
- ConversionEvent
- CountryEvent
- DisasterEvent
- DisbandEvent
- ExpenseEvent
- IncomeEvent
- Meta
- MovementEvent
- NewUnitEvent
- OrderEvent
- RetreatEvent
- StandoffEvent
- UnitEvent
- color_output
- country_class
- event_class
- get_concrete
- get_message
- log_assassination
- log_broken_support
- log_change_country
- log_conquering
- log_control
- log_conversion
- log_disband
- log_elimination
- log_event
- log_excommunication
- log_expense
- log_famine_marker
- log_forced_retreat
- log_income
- log_lifted_excommunication
- log_movement
- log_new_unit
- log_order
- log_overthrow
- log_plague
- log_rebellion
- log_retreat
- log_siege_start
- log_standoff
- log_storm_marker
- log_to_autonomous
- log_unit_surrender
- season_class
- unit_string

`condottieri_events/paginator.py` (168 lines)
Functions:
- EmptyPage
- InvalidPage
- Page
- SeasonNotAnInteger
- SeasonOutOfRange
- SeasonPaginator
- YearNotAnInteger
- _get_newest_season
- _get_newest_year
- _get_oldest_season
- _get_oldest_year
- has_next
- has_other_pages
- has_previous
- next_date
- page
- previous_date
- validate_date

`settings.py` (362 lines)
Functions:
- convert_timezone
- create_connection
- escape_timezone

`machiavelli/templatetags/stars.py` (39 lines)
Functions:
- karma_stars
- score_stars

`condottieri_messages/tests.py` (23 lines)
Functions:
- SimpleTest
- test_basic_addition

`condottieri_help/tests.py` (23 lines)
Functions:
- SimpleTest
- test_basic_addition

`clones/tests.py` (23 lines)
Functions:
- SimpleTest
- test_basic_addition

`condottieri_profiles/tests.py` (23 lines)
Functions:
- SimpleTest
- test_basic_addition

`condottieri_events/tests.py` (23 lines)
Functions:
- SimpleTest
- test_basic_addition

`timezone_fix_middleware.py` (53 lines)
Functions:
- TimezoneFixMiddleware
- _cursor
- convert_timezone
- new_get_db_prep_save
- process_request

`condottieri_common/management/commands/update_weighted_scores.py` (64 lines)
Functions:
- Command
- handle_noargs

`condottieri_help/urls.py` (17 lines)
Functions:
- get_extra_context

`urls.py` (88 lines)
Functions:
- debug_serve
- homepage

`condottieri_messages/views.py` (258 lines)
Functions:
- check_errors
- compose
- delete
- inbox
- is_valid
- outbox
- undelete
- view

`condottieri_profiles/views.py` (55 lines)
Functions:
- languages_edit
- profile_detail
- profile_edit

`machiavelli/views.py` (1570 lines)
Functions:
- assassination
- base_context
- borrow_money
- confirm_orders
- create_game
- delete_order
- excommunicate
- finished_games
- forgive_excommunication
- game_results
- get_area_info
- get_supportable_units
- get_supportable_units_query
- get_valid_adjacent_areas
- get_valid_destinations
- get_valid_support_destinations
- give_money
- hall_of_fame
- in_last_seconds
- invite_users
- is_ajax
- is_authenticated
- is_valid
- isinstance
- iteritems
- join_game
- joinable_games
- js_play_game
- leave_game
- logs_by_game
- make_public
- my_active_games
- new_whisper
- other_active_games
- overthrow
- pending_games
- play_expenses
- play_finance_reinforcements
- play_game
- play_orders
- play_reinforcements
- play_retreats
- ranking
- scenario_list
- show_scenario
- sidebar_context
- summary
- turn_log_list
- undo_actions
- undo_expense
- whisper_list

# 📊 Project Overview
**Files:** 80  |  **Lines:** 9,697

## 📁 File Distribution
- .py: 80 files (9,697 lines)

*Updated: March 23, 2025 at 05:31 PM*