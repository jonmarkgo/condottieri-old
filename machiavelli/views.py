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

""" Django views definitions for machiavelli application. """

## stdlib
from datetime import datetime
from math import ceil

## django
from django.http import HttpResponseRedirect, Http404, HttpResponse, JsonResponse # Added JsonResponse
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from django.forms.formsets import formset_factory
from django.forms.models import modelformset_factory
from django.db.models import Q, F, Sum
from django.db.models.query import QuerySet
from django.core.cache import cache
from django.views.decorators.cache import never_cache, cache_page
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
# from django.utils import simplejson # Deprecated in Django 1.7+, use json
import json # Use standard json library
from django.contrib import messages

## machiavelli
from machiavelli.models import *
import machiavelli.forms as forms

## condottieri_common
from condottieri_common.models import Server

## condottieri_profiles
from condottieri_profiles.models import CondottieriProfile

## condottieri_events
import condottieri_events.paginator as events_paginator

## clones detection
if 'clones' in settings.INSTALLED_APPS:
	from clones import models as clones
else:
	clones = None

if "jogging" in settings.INSTALLED_APPS:
	from jogging import logging
else:
	logging = None

if "notification" in settings.INSTALLED_APPS:
	from notification import models as notification
else:
	notification = None


# from machiavelli.models import Unit # Already imported via *

# --- Helper Functions ---

def sidebar_context(request):
	# ... (sidebar_context function remains largely the same) ...
	context = {}
	activity = cache.get('sidebar_activity')
	if not activity:
		activity = Player.objects.values("user").distinct().count()
		cache.set('sidebar_activity', activity)
	top_users = cache.get('sidebar_top_users')
	if not top_users:
		top_users = CondottieriProfile.objects.all().order_by('-weighted_score').select_related('user')[:5]
		cache.set('sidebar_top_users', top_users)
	if request.user.is_authenticated():
		user_profile = request.user.get_profile()
		if user_profile and not user_profile in top_users:
			my_score = user_profile.weighted_score
			my_position = CondottieriProfile.objects.filter(weighted_score__gt=my_score).count() + 1
			context.update({'my_position': my_position,})
	latest_gossip = cache.get('latest_gossip')
	if not latest_gossip:
		latest_gossip = Whisper.objects.all()[:5]
		cache.set('latest_gossip', latest_gossip)

	try:
		server = Server.objects.get()
		ranking_last_update = server.ranking_last_update
	except Server.DoesNotExist:
		ranking_last_update = None # Handle case where Server object doesn't exist

	context.update({ 'activity': activity,
				'top_users': top_users,
				'whispers': latest_gossip,
				'ranking_last_update': ranking_last_update,})
	return context


# --- View Functions ---

def summary(request):
	# ... (summary view remains largely the same) ...
	context = sidebar_context(request)
	context.update( {'forum': 'forum' in settings.INSTALLED_APPS} )
	if request.user.is_authenticated():
		joinable = Game.objects.exclude(player__user=request.user).filter(slots__gt=0, private=False).order_by('slots').select_related('scenario', 'configuration', 'player__user')
		my_games_ids = Game.objects.filter(player__user=request.user).values_list('id', flat=True) # Use values_list
		context.update( {'revolutions': Revolution.objects.filter(opposition__isnull=True).exclude(government__game__id__in=my_games_ids).select_related('government__game', 'government__country')} ) # Correct related name
		context.update( {'actions': Player.objects.filter(user=request.user, game__slots=0, done=False).select_related('game')} )
		## show unseen notices
		if notification:
			new_notices = notification.Notice.objects.notices_for(request.user, unseen=True, on_site=True)
			context.update({'new_notices': new_notices,})
	else:
		joinable = Game.objects.filter(slots__gt=0, private=False).order_by('slots').select_related('scenario', 'configuration', 'player__user')
		context.update( {'revolutions': Revolution.objects.filter(opposition__isnull=True).select_related('government__game', 'government__country')} ) # Correct related name
	if joinable:
		context.update( {'joinable_game': joinable.first()} ) # Use first() instead of index

	return render_to_response('machiavelli/summary.html',
							context,
							context_instance=RequestContext(request))

# --- Game List Views (largely unchanged, ensure templates use updated context if needed) ---
@never_cache
def my_active_games(request):
	# ... (remains same) ...
	context = sidebar_context(request)
	if request.user.is_authenticated():
		my_players = Player.objects.filter(user=request.user, game__slots=0).select_related("country", "game__scenario", "game__configuration")
	else:
		my_players = Player.objects.none()
	paginator = Paginator(my_players, 10)
	try:
		page = int(request.GET.get('page', '1'))
	except ValueError:
		page = 1
	try:
		player_list = paginator.page(page)
	except (EmptyPage, InvalidPage):
		player_list = paginator.page(paginator.num_pages)
	context.update( {
		'player_list': player_list,
		})

	return render_to_response('machiavelli/game_list_my_active.html',
							context,
							context_instance=RequestContext(request))

@never_cache
def other_active_games(request):
	# ... (remains same) ...
	context = sidebar_context(request)
	if request.user.is_authenticated():
		games = Game.objects.exclude(phase=PHINACTIVE).exclude(player__user=request.user)
	else:
		games = Game.objects.exclude(phase=PHINACTIVE)
	paginator = Paginator(games, 10)
	try:
		page = int(request.GET.get('page', '1'))
	except ValueError:
		page = 1
	try:
		game_list = paginator.page(page)
	except (EmptyPage, InvalidPage):
		game_list = paginator.page(paginator.num_pages)
	context.update( {
		'game_list': game_list,
		})

	return render_to_response('machiavelli/game_list_active.html',
							context,
							context_instance=RequestContext(request))

@never_cache
def finished_games(request, only_user=False):
	# ... (remains same) ...
	context = sidebar_context(request)
	games = Game.objects.filter(slots=0, phase=PHINACTIVE).order_by("-finished")
	if only_user and request.user.is_authenticated(): # Check authentication for user filter
		games = games.filter(score__user=request.user)
	paginator = Paginator(games, 10)
	try:
		page = int(request.GET.get('page', '1'))
	except ValueError:
		page = 1
	try:
		game_list = paginator.page(page)
	except (EmptyPage, InvalidPage):
		game_list = paginator.page(paginator.num_pages)
	context.update( {
		'game_list': game_list,
		'only_user': only_user,
		})

	return render_to_response('machiavelli/game_list_finished.html',
							context,
							context_instance=RequestContext(request))

@never_cache
def joinable_games(request):
	# ... (remains same) ...
	context = sidebar_context(request)
	if request.user.is_authenticated():
		games = Game.objects.filter(slots__gt=0).exclude(player__user=request.user)
	else:
		games = Game.objects.filter(slots__gt=0)
	paginator = Paginator(games, 10)
	try:
		page = int(request.GET.get('page', '1'))
	except ValueError:
		page = 1
	try:
		game_list = paginator.page(page)
	except (EmptyPage, InvalidPage):
		game_list = paginator.page(paginator.num_pages)
	context.update( {
		'game_list': game_list,
		'joinable': True,
		})

	return render_to_response('machiavelli/game_list_pending.html',
							context,
							context_instance=RequestContext(request))

@never_cache
@login_required
def pending_games(request):
	# ... (remains same) ...
	context = sidebar_context(request)
	games = Game.objects.filter(slots__gt=0, player__user=request.user)
	paginator = Paginator(games, 10)
	try:
		page = int(request.GET.get('page', '1'))
	except ValueError:
		page = 1
	try:
		game_list = paginator.page(page)
	except (EmptyPage, InvalidPage):
		game_list = paginator.page(paginator.num_pages)
	context.update( {
		'game_list': game_list,
		'joinable': False,
		})

	return render_to_response('machiavelli/game_list_pending.html',
							context,
							context_instance=RequestContext(request))

def base_context(request, game, player):
	# ... (base_context function remains largely the same) ...
	# Ensure player object is valid before accessing attributes
	context = {
		'user': request.user,
		'game': game,
		'map' : game.get_map_url(),
		'player': player if player and player.pk else None, # Pass None if player is invalid/None
		'player_list': game.player_list_ordered_by_cities(),
		'show_users': game.visible,
		}
	if game.slots > 0:
		context['player_list'] = game.player_set.filter(user__isnull=False)

	# Safely access player attributes
	if player and player.pk:
		context['done'] = player.done
		if game.configuration.finances:
			context['ducats'] = player.ducats
		context['can_excommunicate'] = player.can_excommunicate()
		context['can_forgive'] = player.can_forgive()
		if game.slots == 0:
			context['time_exceeded'] = player.time_exceeded()
		if game.phase == PHORDERS:
			# Check if undo is allowed (done, but not in last seconds)
			if player.done and not player.in_last_seconds():
				context.update({'undoable': True,})

	# Log fetching logic seems okay, but ensure BaseEvent model exists if used
	# log = game.baseevent_set.all()
	# if player:
	# 	log = log.exclude(season__exact=game.season,
	# 							phase__exact=game.phase)
	# if len(log) > 0:
	# 	last_year = log[0].year
	# 	last_season = log[0].season
	# 	last_phase = log[0].phase
	# 	context['log'] = log.filter(year__exact=last_year,
	# 							season__exact=last_season,
	# 							phase__exact=last_phase)
	# else:
	# 	context['log'] = log # this will always be an empty queryset

	rules = game.configuration.get_enabled_rules()
	if len(rules) > 0:
		context['rules'] = rules

	if game.configuration.gossip:
		whispers = game.whisper_set.all()[:10]
		context.update({'whispers': whispers, })
		if player and player.pk:
			context.update({'whisper_form': forms.WhisperForm(request.user, game),})

	return context

#@never_cache
#def js_play_game(request, slug=''):
#	game = get_object_or_404(Game, slug=slug)
#	try:
#		player = Player.objects.get(game=game, user=request.user)
#	except:
#		player = Player.objects.none()
#	units = Unit.objects.filter(player__game=game)
#	player_list = game.player_list_ordered_by_cities()
#	context = {
#		'game': game,
#		'player': player,
#		'map': 'base-map.png',
#		'units': units,
#		'player_list': player_list,
#	}
#	return render_to_response('machiavelli/js_game.html',
#						context,
#						context_instance=RequestContext(request))
#

# --- Utility Views (unchanged) ---
@login_required
def undo_actions(request, slug=''):
	# ... (remains same) ...
	game = get_object_or_404(Game, slug=slug)
	player = get_object_or_404(Player, game=game, user=request.user)
	profile = request.user.get_profile()
	if request.method == 'POST':
		# Allow undo only during specific phases and if player is done but time allows
		allowed_phases = [PHORDERS] # Example: Only allow undoing orders
		if game.phase in allowed_phases and player.done and not player.in_last_seconds():
			player.done = False
			# Unconfirm orders, expenses, assassinations
			player.order_set.update(confirmed=False)
			player.expense_set.update(confirmed=False)
			# Assassinations don't have confirmed flag, maybe delete them? Or require re-entry?
			# Let's assume they need re-entry if actions are undone.
			# Player needs to re-spend ducats and re-use token.
			pending_assassinations = player.assassination_attempts.all()
			for attempt in pending_assassinations:
			    # Refund ducats
			    Player.objects.filter(id=player.id).update(ducats=F('ducats') + attempt.ducats)
			    # Restore assassin token
			    Assassin.objects.get_or_create(owner=player, target=attempt.target.country) # Assumes target player still exists
			    attempt.delete()


			if game.check_bonus_time(): # Check if bonus was applied
				if profile: profile.adjust_karma( -1 ) # Remove karma bonus
			player.save(update_fields=['done'])
			messages.success(request, _("Your actions are now unconfirmed. You'll have to confirm them again."))
		else:
		    messages.error(request, _("Cannot undo actions at this time."))

	return redirect('show-game', slug=slug)
@never_cache
@login_required # Added decorator, playing requires login
def play_game(request, slug='', **kwargs):
	game = get_object_or_404(Game, slug=slug)
	if game.slots == 0 and game.phase == PHINACTIVE:
		return redirect('game-results', slug=game.slug)
	try:
		# Ensure player is not eliminated if game has started
		player = Player.objects.get(game=game, user=request.user)
		if game.slots == 0 and player.eliminated:
		    player = None # Treat eliminated player as spectator
	except Player.DoesNotExist:
		player = None # User is not in this game

	if player:
		# --- IP Tracking ---
		if clones and request.method == 'POST' and not request.is_ajax():
			try:
				# Ensure IP_HEADER is correctly configured in settings
				ip_address = request.META.get(settings.IP_HEADER, request.META.get('REMOTE_ADDR'))
				if ip_address:
					fp = clones.Fingerprint(user=request.user, game=game, ip=ip_address)
					fp.save()
			except Exception as e: # Catch potential errors during fingerprinting
				if logging: logging.error(f"Fingerprint save error for game {game.id}, user {request.user.id}: {e}")
				pass
		# --- End IP Tracking ---

        # Phase Dispatching
        phase_handlers = {
            PHINACTIVE: lambda: render_to_response('machiavelli/inactive_actions.html', base_context(request, game, player), context_instance=RequestContext(request)),
            PHREINFORCE: lambda: play_finance_reinforcements(request, game, player) if game.configuration.finances else play_reinforcements(request, game, player),
            PHORDERS: lambda: play_expenses(request, game, player) if 'extra' in kwargs and kwargs['extra'] == 'expenses' and game.configuration.finances else play_orders(request, game, player),
            PHRETREATS: lambda: play_retreats(request, game, player),
            # Add handlers for new phases if implemented as distinct states
            PHFAMINE: lambda: play_orders(request, game, player),
            PHPLAGUE: lambda: play_orders(request, game, player),
            PHNEGOTIATION: lambda: play_orders(request, game, player),
            PHLENDERS: lambda: play_orders(request, game, player),
            PHEXPENSES: lambda: play_orders(request, game, player),
            PHASSASSINATION: lambda: play_orders(request, game, player),
            PHSTORMS: lambda: play_orders(request, game, player),
        }

		handler = phase_handlers.get(game.phase)
		if handler:
		    return handler()
		else:
		    # Fallback or error for unhandled phases
		    if logging: logging.warning(f"Unhandled phase {game.phase} in game {game.id}")
		    # Default to showing orders or inactive screen
		    return play_orders(request, game, player)

    else: # Spectator or eliminated
        context = base_context(request, game, None)
        return render_to_response('machiavelli/inactive_actions.html',
                            context,
                            context_instance=RequestContext(request))

def play_reinforcements(request, game, player):
    context = base_context(request, game, player)
    is_first_spring = (game.year == game.scenario.start_year and game.season == 1)

    if is_first_spring and not player.done:
        # ... (first spring logic - unchanged) ...
        player.unit_set.update(paid=True)
        player.end_phase()
        messages.info(request, _("Initial setup complete. Proceeding to orders."))
        return HttpResponseRedirect(request.path)

    if player.done:
        # ... (display summary logic - unchanged) ...
        context['to_place'] = player.unit_set.filter(placed=False)
        context['to_disband'] = player.unit_set.filter(placed=True, paid=False)
        context['to_keep'] = player.unit_set.filter(placed=True, paid=True)
    else:
        units_to_place = player.units_to_place()
        context['cities_qty'] = player.number_of_cities()
        context['cur_units'] = player.unit_set.count()

        if units_to_place > 0:
            context['units_to_place'] = units_to_place
            ReinforceForm = forms.make_reinforce_form(player, finances=False, special_units=False)
            ReinforceFormSet = formset_factory(ReinforceForm,
                                formset=forms.BaseReinforceFormSet,
                                extra=units_to_place, max_num=units_to_place)
            if request.method == 'POST':
                # *** ADD form_kwargs HERE ***
                reinforce_formset = ReinforceFormSet(request.POST, prefix='reinforce', form_kwargs={'player': player})
                if reinforce_formset.is_valid():
                    # ... (form processing logic - unchanged) ...
                    units_to_create = []
                    for form in reinforce_formset:
                        if form.has_changed() and form.is_valid():
                            area = form.cleaned_data.get('area')
                            type_ = form.cleaned_data.get('type')
                            coast = form.cleaned_data.get('coast')
                            if area and type_:
                                units_to_create.append(
                                    Unit(type=type_, area=area, player=player,
                                         coast=coast, placed=False, paid=True)
                                )
                    if units_to_create:
                        Unit.objects.bulk_create(units_to_create)
                    player.end_phase()
                    messages.success(request, _("You have successfully made your reinforcements."))
                    return HttpResponseRedirect(request.path)
                else:
                    messages.error(request, _("Please correct the errors in the reinforcement form."))
            else: # GET request
                # *** ADD form_kwargs HERE ***
                reinforce_formset = ReinforceFormSet(prefix='reinforce', form_kwargs={'player': player})
            context['reinforce_formset'] = reinforce_formset
        elif units_to_place < 0:
            # ... (disband logic - unchanged) ...
            context['units_to_disband'] = -units_to_place
            DisbandForm = forms.make_disband_form(player)
            if request.method == 'POST':
                disband_form = DisbandForm(request.POST)
                if disband_form.is_valid():
                    selected_units = disband_form.cleaned_data['units']
                    if len(selected_units) == -units_to_place:
                        selected_units.update(paid=False, placed=True)
                        player.unit_set.filter(placed=True).exclude(id__in=selected_units.values_list('id', flat=True)).update(paid=True)
                        player.end_phase()
                        messages.success(request, _("You have successfully selected units for disbandment."))
                        return HttpResponseRedirect(request.path)
                    else:
                        messages.error(request, _("Please select exactly %(num)s units to disband.") % {'num': -units_to_place})
            else:
                disband_form = DisbandForm()
            context['disband_form'] = disband_form
        else: # units_to_place == 0
            player.unit_set.update(paid=True)
            player.end_phase()
            messages.info(request, _("No unit adjustments needed this turn."))
            return HttpResponseRedirect(request.path)

    return render_to_response('machiavelli/reinforcements_actions.html',
                            context,
                            context_instance=RequestContext(request))

def play_finance_reinforcements(request, game, player):
    # ... (context setup, step 0 logic - unchanged) ...

    # --- Step 1: Placement Step ---
    elif step == 1:
        # ... (calculate max_units_possible, check if placement possible - unchanged) ...
        can_buy = int(player.ducats / 3)
        can_place = player.get_areas_for_new_units(finances=True).count()
        max_units_possible = min(can_buy, can_place)
        can_afford_any = player.ducats >= 3
        can_place_any = can_place > 0
        has_special_option = game.configuration.special_units and not player.has_special_unit()

        if not can_afford_any and not can_place_any and not has_special_option:
            player.end_phase()
            messages.info(request, _("No new units can be placed this turn (insufficient funds or space)."))
            return HttpResponseRedirect(request.path)

        ReinforceForm = forms.make_reinforce_form(player, finances=True,
                                            special_units=game.configuration.special_units)
        extra_forms = max(1, max_units_possible if max_units_possible > 0 else (1 if has_special_option else 0))
        max_forms = can_place if can_place > 0 else (1 if has_special_option else 0)

        ReinforceFormSet = formset_factory(ReinforceForm,
                            formset=forms.BaseReinforceFormSet,
                            extra=extra_forms,
                            max_num=max_forms) # Use max_forms here

        if request.method == 'POST':
            # *** ADD form_kwargs HERE ***
            formset = ReinforceFormSet(request.POST, prefix='reinforce', form_kwargs={'player': player})
            if formset.is_valid():
                # ... (form processing logic - unchanged) ...
                total_cost = 0
                units_to_create = []
                cost_from_forms = 0
                for form in formset:
                     if form.has_changed() and form.is_valid() and form.cleaned_data.get('area') and form.cleaned_data.get('type'):
                          cost_from_forms += form.cleaned_data.get('cost', 3)

                if cost_from_forms > player.ducats:
                     messages.error(request, _("Cannot build all selected units: Insufficient ducats."))
                     context['formset'] = formset
                     context['max_units_possible'] = max_units_possible
                     template_name = 'machiavelli/finance_reinforcements_1.html'
                     return render_to_response(template_name, context, context_instance=RequestContext(request))
                else:
                     total_cost = cost_from_forms
                     for form in formset:
                          if form.has_changed() and form.is_valid():
                               area = form.cleaned_data.get('area')
                               type_ = form.cleaned_data.get('type')
                               coast = form.cleaned_data.get('coast')
                               unit_class = form.cleaned_data.get('unit_class')
                               cost = form.cleaned_data.get('cost', 3)
                               power = 1; loyalty = 1
                               if unit_class:
                                    power = unit_class.power
                                    loyalty = unit_class.loyalty
                               if area and type_:
                                    units_to_create.append(
                                         Unit(type=type_, area=area, player=player,
                                              coast=coast, placed=False, cost=cost, power=power, loyalty=loyalty)
                                    )
                     if units_to_create:
                          Unit.objects.bulk_create(units_to_create)
                          Player.objects.filter(id=player.id).update(ducats=F('ducats') - total_cost)
                          player.refresh_from_db()
                     player.end_phase()
                     messages.success(request, _("You have successfully made your reinforcements."))
                     return HttpResponseRedirect(request.path)
            else:
                messages.error(request, _("Please correct the errors in the reinforcement formset."))
        else: # GET request
            # *** ADD form_kwargs HERE ***
            formset = ReinforceFormSet(prefix='reinforce', form_kwargs={'player': player})

        context['formset'] = formset
        context['max_units_possible'] = max_units_possible
        template_name = 'machiavelli/finance_reinforcements_1.html'

    # ... (rest of view) ...
    return render_to_response(template_name, context,
                            context_instance=RequestContext(request))

def play_orders(request, game, player):
    context = base_context(request, game, player)
    # ... (context setup for orders, expenses, assassinations, loans) ...
    sent_orders = player.order_set.all().select_related('unit__area__board_area', 'destination__board_area', 'subunit__area__board_area', 'subdestination__board_area')
    context.update({'sent_orders': sent_orders})
    if game.configuration.finances: context['current_expenses'] = player.expense_set.all()
    if game.configuration.assassinations: context['assassinations'] = player.assassination_attempts.all()
    if game.configuration.lenders:
        try: loan = player.loan
        except Loan.DoesNotExist: loan = None
        context.update({'loan': loan})

    if not player.done:
        OrderForm = forms.make_order_form(player)
        if request.method == 'POST':
            order_form = OrderForm(player, data=request.POST)
            if request.is_ajax():
                if order_form.is_valid():
                    # Save includes coast fields now
                    new_order = order_form.save()
                    response_dict = {'bad': 'false', 'pk': new_order.pk, 'new_order': new_order.explain()}
                else:
                    response_dict = {'bad': 'true', 'errs': order_form.errors}
                return JsonResponse(response_dict)
            else: # Not AJAX
                if order_form.is_valid():
                    # Save includes coast fields now
                    order_form.save()
                    messages.success(request, _("Order successfully saved."))
                    return HttpResponseRedirect(request.path)
                else:
                    messages.error(request, _("Invalid order. Please check the details."))
        else: # GET request
            order_form = OrderForm(player)
        context.update({'order_form': order_form})

    return render_to_response('machiavelli/orders_actions.html',
                            context,
                            context_instance=RequestContext(request))
@login_required # At least require login
def handle_player_quit(request, slug, player_id):
    """
    Handles the process of removing a player from an active game,
    placing autonomous garrisons according to Rule VII.
    Requires appropriate permissions (e.g., game creator or staff).
    """
    game = get_object_or_404(Game, slug=slug)
    quitting_player = get_object_or_404(Player, pk=player_id, game=game)

    # --- Permission Check ---
    # Allow game creator or superuser/staff to remove players
    if not (request.user == game.created_by or request.user.is_staff):
        messages.error(request, _("You do not have permission to remove players from this game."))
        return redirect('show-game', slug=game.slug)
    # --- End Permission Check ---

    # --- Validation ---
    if not quitting_player.user:
        messages.error(request, _("Cannot remove the autonomous player."))
        return redirect('show-game', slug=game.slug)

    if game.phase == PHINACTIVE:
         messages.error(request, _("Cannot remove player from a finished game."))
         return redirect('show-game', slug=game.slug)

    if quitting_player.eliminated:
         messages.warning(request, _("Player is already marked as eliminated."))
         # Allow proceeding to ensure cleanup, or redirect? Let's proceed.
    # --- End Validation ---

    if logging: logging.warning(f"Game {game.id}: Player {quitting_player} ({quitting_player.user}) is being removed (quit/kicked).")

    # --- Core Logic (adapted from conceptual code) ---
    try:
        # 1. Get Autonomous Player
        try:
            autonomous_player = Player.objects.get(game=game, user__isnull=True)
        except Player.DoesNotExist:
            # Create autonomous player if it doesn't exist (should have been created at game start)
            logging.error(f"Game {game.id}: Autonomous player not found! Creating one.")
            autonomous_player = Player(game=game, done=True)
            autonomous_player.save()

        # 2. Store controlled fortified areas BEFORE removing control
        controlled_fortified_areas = list(
            GameArea.objects.filter(game=game, player=quitting_player, board_area__is_fortified=True)
        )

        # 3. Mark player as eliminated/quit
        quitting_player.eliminated = True
        quitting_player.done = True # Mark as done for current phase processing
        quitting_player.ducats = 0
        # Clear other flags if necessary
        quitting_player.save(update_fields=['eliminated', 'done', 'ducats'])

        # 4. Remove Units
        units_removed_count = quitting_player.unit_set.all().delete()
        if logging: logging.info(f"Removed {units_removed_count} units for quitting player {quitting_player}.")

        # 5. Remove Control from all areas
        areas_updated = quitting_player.gamearea_set.all().update(player=None)
        if logging: logging.info(f"Removed control from {areas_updated} areas for quitting player {quitting_player}.")

        # 6. Remove Orders, Expenses, etc.
        quitting_player.order_set.all().delete()
        # Refund pending expenses? Rule doesn't say. Let's just delete.
        quitting_player.expense_set.all().delete()
        quitting_player.assassination_attempts.all().delete()
        Assassin.objects.filter(owner=quitting_player).delete()
        Loan.objects.filter(player=quitting_player).delete()
        # Remove pending revolutions *against* this player? Or let them resolve? Let's remove.
        Rebellion.objects.filter(player=quitting_player).delete()

        # 7. Place Autonomous Garrisons (Rule VII)
        garrisons_placed = 0
        for area in controlled_fortified_areas:
            # Refresh area from DB to ensure it's actually empty now
            area.refresh_from_db()
            if not Unit.objects.filter(area=area, type='G').exists():
                Unit.objects.create(
                    type='G',
                    area=area,
                    player=autonomous_player,
                    placed=True,
                    paid=True # Autonomous units don't use payment system
                )
                garrisons_placed += 1
                if logging: logging.info(f"Placed autonomous garrison in {area} for quitting player {quitting_player}.")

        # 8. Update Game State
        game.reset_players_cache()
        # Check if removing the player finishes the current phase or game
        game.check_finished_phase()

        messages.success(request, _("Player %(user)s (%(country)s) removed from game. %(num)s autonomous garrisons placed.") % {
            'user': quitting_player.user.username,
            'country': quitting_player.country if quitting_player.country else 'N/A',
            'num': garrisons_placed
        })

    except Exception as e:
        # Catch unexpected errors during the process
        if logging: logging.error(f"Error removing player {player_id} from game {game.id}: {e}", exc_info=True)
        messages.error(request, _("An unexpected error occurred while removing the player."))

    return redirect('show-game', slug=game.slug) # Redirect back to game view

@login_required
def delete_order(request, slug='', order_id=''):
	# ... (remains same, but use JsonResponse) ...
	game = get_object_or_404(Game, slug=slug)
	player = get_object_or_404(Player, game=game, user=request.user)
	order = get_object_or_404(Order, id=order_id, player=player, confirmed=False) # Check player owns order
	response_dict = {'bad': 'false', 'order_id': order.id}
	try:
		order.delete()
		messages.success(request, _("Order deleted.")) # Add user feedback
	except Exception as e: # Catch specific exceptions if possible
		response_dict.update({'bad': 'true', 'error': str(e)})
		messages.error(request, _("Failed to delete order."))
		if logging: logging.error(f"Error deleting order {order_id} for player {player.id}: {e}")

	if request.is_ajax():
		return JsonResponse(response_dict)
		# return HttpResponse(json.dumps(response_dict, ensure_ascii=False), content_type='application/json')

	return redirect(game) # Redirect back to game view

@login_required
def confirm_orders(request, slug=''):
	# ... (Logic largely okay, relies on updated order.is_possible) ...
	game = get_object_or_404(Game, slug=slug)
	player = get_object_or_404(Player, game=game, user=request.user, done=False)
	if request.method == 'POST':
		msg = u"Confirming orders for player %s (%s, %s) in game %s (%s):\n" % (player.id,
			player.static_name, player.user.username, game.id, game.slug)
		possible_orders = 0
		impossible_orders = 0
		sent_orders = player.order_set.all() # Get orders issued by this player

		for order in sent_orders:
			msg += u"%s => " % order.format()
			# Re-validate possibility at confirmation time
			if order.is_possible():
				order.confirm() # Mark as confirmed
				possible_orders += 1
				msg += u"OK\n"
			else:
				# Delete impossible orders instead of confirming them? Or let game logic handle?
				# Current logic seems to keep them, game logic might ignore them.
				# Let's delete them here for clarity.
				msg += u"Invalid - DELETED\n"
				order.delete()
				impossible_orders += 1

		# Confirm expenses
		player.expense_set.all().update(confirmed=True)
		# Confirm assassinations (already saved, just log?)
		# player.assassination_attempts.all().update(confirmed=True) # No confirmed flag

		if logging: logging.info(msg)
		player.end_phase()
		if impossible_orders > 0:
		     messages.warning(request, _("%(num)s invalid orders were deleted.") % {'num': impossible_orders})
		messages.success(request, _("You have successfully confirmed your actions (%(num)s orders).") % {'num': possible_orders})

		# Check if this is the final player to confirm orders
		remaining_players = game.player_set.filter(done=False).count()
		if remaining_players == 0:
			try:
				from django.core.management import call_command
				# Consider running this asynchronously (e.g., with Celery)
				# to avoid blocking the user request.
				call_command('check_turns', game_id=game.id) # Pass game_id if command supports it
			except Exception as e:
			    if logging: logging.error(f"Error calling check_turns after confirm_orders for game {game.id}: {e}")
			    messages.error(request, _("Error triggering game phase advance."))


	return redirect(game)

def 
def play_retreats(request, game, player):
    context = base_context(request, game, player)
    if not player.done:
        units_to_retreat = Unit.objects.filter(player=player).exclude(must_retreat__exact='')
        retreat_forms = []
        if request.method == 'POST':
            valid_forms = True
            retreat_orders_to_save = []
            for u in units_to_retreat:
                RetreatForm = forms.make_retreat_form(u)
                # Use unit ID as prefix for uniqueness
                form = RetreatForm(request.POST, prefix=str(u.id))
                retreat_forms.append(form)
                if form.is_valid():
                    area = form.cleaned_data.get('area')
                    coast = form.cleaned_data.get('coast') # Get coast value
                    # Create RetreatOrder object with coast
                    retreat_orders_to_save.append(RetreatOrder(unit=u, area=area, coast=coast))
                else:
                    valid_forms = False

            if valid_forms:
                RetreatOrder.objects.filter(unit__player=player).delete()
                RetreatOrder.objects.bulk_create(retreat_orders_to_save)
                player.end_phase()
                messages.success(request, _("You have successfully retreated your units."))
                return HttpResponseRedirect(request.path)
            else:
                messages.error(request, _("Please correct the errors in the retreat form."))
                context['retreat_forms'] = retreat_forms # Pass forms with errors back
        else: # GET request
            if not units_to_retreat.exists():
                player.end_phase()
                messages.info(request, _("No retreats required this turn."))
                return HttpResponseRedirect(request.path)
            else:
                for u in units_to_retreat:
                    RetreatForm = forms.make_retreat_form(u)
                    retreat_forms.append(RetreatForm(prefix=str(u.id))) # Use prefix
                context['retreat_forms'] = retreat_forms
	else: # Player is done
	    # Optionally show summary of retreats made, or just wait message
	    pass

	return render_to_response('machiavelli/retreats_actions.html',
							context,
							context_instance=RequestContext(request))


def play_expenses(request, game, player):
	# ... (Logic okay, uses updated ExpenseForm) ...
	context = base_context(request, game, player)
	context['current_expenses'] = player.expense_set.all()
	ExpenseForm = forms.make_expense_form(player) # Uses updated form maker

	if not player.done: # Allow adding expenses only if not done
		if request.method == 'POST':
			form = ExpenseForm(player, data=request.POST)
			if form.is_valid():
				expense = form.save(commit=False)
				# Deduct ducats immediately upon saving the expense form
				try:
				    ducats_to_spend = int(form.cleaned_data['ducats'])
				    if player.ducats >= ducats_to_spend:
				        expense.save() # Save the expense object
				        # Use F expression to prevent race conditions
				        Player.objects.filter(id=player.id).update(ducats=F('ducats') - ducats_to_spend)
				        player.refresh_from_db() # Update player object in view context
				        messages.success(request, _("Expense successfully saved."))
				        # Redirect to same page to show updated list and clear form
				        return HttpResponseRedirect(request.path)
				    else:
				        messages.error(request, _("Insufficient ducats for this expense."))
				        # Re-render form with error (or add non-field error)
				        form.add_error(None, _("Insufficient ducats."))
				except (ValueError, TypeError):
				     messages.error(request, _("Invalid ducat amount selected."))
				     form.add_error('ducats', _("Invalid amount."))

			else: # Form is invalid
			    messages.error(request, _("Please correct the errors below."))
		else: # GET request
			form = ExpenseForm(player)
		context['form'] = form
	else: # Player is done
	    messages.info(request, _("You have already confirmed your actions for this phase."))

	return render_to_response('machiavelli/expenses_actions.html',
							context,
							context_instance=RequestContext(request))

@login_required
def undo_expense(request, slug='', expense_id=''):
	# ... (Logic okay, but ensure player is not done) ...
	game = get_object_or_404(Game, slug=slug)
	player = get_object_or_404(Player, game=game, user=request.user)
	expense = get_object_or_404(Expense, id=expense_id, player=player)

	if player.done:
	    messages.error(request, _("Cannot undo expense after confirming actions."))
	    return redirect(game)

	if expense.confirmed:
	    messages.error(request, _("Cannot undo a confirmed expense."))
	    return redirect('expenses', slug=game.slug) # Redirect back to expenses page

	try:
		expense.undo() # Model method handles refund and deletion
		messages.success(request, _("Expense successfully undone."))
	except Exception as e: # Catch potential errors during undo
		messages.error(request, _("Expense could not be undone."))
		if logging: logging.error(f"Error undoing expense {expense_id} for player {player.id}: {e}")

	return redirect('expenses', slug=game.slug) # Redirect back to expenses page

# --- Other Views (Game Results, Logs, Ranking, Scenario - largely unchanged) ---
@never_cache
def game_results(request, slug=''):
	# ... (remains same) ...
	game = get_object_or_404(Game, slug=slug)
	if game.phase != PHINACTIVE:
		# Redirect active games back to the game view
		return redirect('show-game', slug=game.slug)
	scores = game.score_set.filter(user__isnull=False).order_by('-points')
	context = {'game': game,
				'map' : game.get_map_url(),
				'players': scores,
				'show_log': False,}
	# Check if TurnLog exists instead of BaseEvent
	if game.turnlog_set.exists():
		context['show_log'] = True
	return render_to_response('machiavelli/game_results.html',
							context,
							context_instance=RequestContext(request))

@never_cache
@login_required # Require login to view logs? Or make public?
def logs_by_game(request, slug=''):
    game = get_object_or_404(Game, slug=slug)
    try:
        player = Player.objects.get(game=game, user=request.user)
    except Player.DoesNotExist:
        player = None # Allow viewing logs even if not playing?

    context = base_context(request, game, player)
    # Use TurnLog instead of BaseEvent
    log_list = game.turnlog_set.all().order_by('-year', '-season', '-phase', '-timestamp') # Order chronologically

    # Paginator for TurnLog might need custom logic if paginating by turn/season
    paginator = Paginator(log_list, 10) # Simple pagination for now
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        log_page = paginator.page(page)
    except (EmptyPage, InvalidPage):
        log_page = paginator.page(paginator.num_pages) # Show last page on error

    context['log_page'] = log_page # Pass paginated list

    return render_to_response('machiavelli/log_list.html', # Adjust template if needed
                            context,
                            context_instance=RequestContext(request))

# --- Game Play Views ---

@login_required
def create_game(request):
	context = sidebar_context(request)
	context.update( {'user': request.user,})
	if request.method == 'POST':
		# Pass user to GameForm constructor
		game_form = forms.GameForm(user=request.user, data=request.POST)
		config_form = forms.ConfigurationForm(request.POST)
		if game_form.is_valid() and config_form.is_valid(): # Validate both forms
			new_game = game_form.save(commit=False)
			# Calculate initial slots based on scenario
			new_game.slots = new_game.scenario.get_slots() # Get actual player count
			if new_game.slots > 0:
			    new_game.slots -= 1 # Decrement for the creator
			else:
			    # Handle scenarios with 0 or 1 player? Or assume always > 1
			    messages.error(request, _("Scenario requires more players."))
			    # Redirect or show error without saving
			    return render_to_response('machiavelli/game_form.html', {
			        'game_form': game_form, 'config_form': config_form, **context
			    }, context_instance=RequestContext(request))

			new_game.save() # Save game first to get PK

			# Save configuration linked to the new game
			config = config_form.save(commit=False)
			config.game = new_game
			config.save()

			# Create player entry for the creator
			new_player = Player(user=request.user, game=new_game)
			new_player.save()

			cache.delete('sidebar_activity')
			messages.success(request, _("Game successfully created."))
			if new_game.private:
				return redirect('invite-users', slug=new_game.slug)
			else:
				return redirect('summary')
		else:
		    # Forms are invalid, pass them back to the template with errors
		    messages.error(request, _("Please correct the errors below."))
	else:
		game_form = forms.GameForm(user=request.user) # Pass user here too
		config_form = forms.ConfigurationForm()

	context['scenarios'] = Scenario.objects.filter(enabled=True)
	context['game_form'] = game_form
	context['config_form'] = config_form
	return render_to_response('machiavelli/game_form.html',
							context,
							context_instance=RequestContext(request))

@login_required
def invite_users(request, slug=''):
	g = get_object_or_404(Game, slug=slug)
	## check that the game is open
	if g.slots == 0:
		raise Http404
	## check that the current user is the creator of the game
	if g.created_by != request.user:
		raise Http404
	context = sidebar_context(request)
	context.update({'game': g,})
	context.update({'players': g.player_set.exclude(user__isnull=True)})
	invitations = Invitation.objects.filter(game=g)
	context.update({'invitations': invitations})
	if request.method == 'POST':
		form = forms.InvitationForm(request.POST)
		if form.is_valid():
			message = form.cleaned_data['message']
			user_list = form.cleaned_data['user_list']
			user_names = user_list.split(',')
			for u in user_names:
				name = u.strip()
				try:
					user = User.objects.get(username=name)
				except ObjectDoesNotExist:
					continue
				else:
					## check that the user is not already in the game
					try:
						Player.objects.get(game=g, user=user)
					except ObjectDoesNotExist:
						## check for existing invitation
						try:
							Invitation.objects.get(game=g, user=user)
						except ObjectDoesNotExist:
							i = Invitation()
							i.game = g
							i.user = user
							i.message = message
							i.save()
	else:
		form = forms.InvitationForm()
	context.update({'form': form})
	return render_to_response('machiavelli/invitation_form.html',
							context,
							context_instance=RequestContext(request))

@login_required
def join_game(request, slug=''):
	g = get_object_or_404(Game, slug=slug)
	invitation = None
	## check if the user has defined his languages
	if not request.user.get_profile().has_languages():
		messages.error(request, _("You must define at least one known language before joining a game."))
		messages.info(request, _("Define your languages and then, try again."))
		return redirect("profile_languages_edit")
	if g.private:
		## check if user has been invited
		try:
			invitation = Invitation.objects.get(game=g, user=request.user)
		except ObjectDoesNotExist:
			messages.error(request, _("This game is private and you have not been invited."))
			return redirect("games-joinable")
	else:
		karma = request.user.get_profile().karma
		if karma < settings.KARMA_TO_JOIN:
			err = _("You need a minimum karma of %s to join a game.") % settings.KARMA_TO_JOIN
			messages.error(request, err)
			return redirect("summary")
		if g.fast and karma < settings.KARMA_TO_FAST:
			err = _("You need a minimum karma of %s to join a fast game.") % settings.KARMA_TO_FAST
			messages.error(request, err)
			return redirect("games-joinable")
	if g.slots > 0:
		try:
			Player.objects.get(user=request.user, game=g)
		except:
			## the user is not in the game
			new_player = Player(user=request.user, game=g)
			new_player.save()
			if invitation:
				invitation.delete()
			g.player_joined()
			messages.success(request, _("You have successfully joined the game."))
			cache.delete('sidebar_activity')
		else:
			messages.error(request, _("You had already joined this game."))
	return redirect('summary')

@login_required
def leave_game(request, slug=''):
	g = get_object_or_404(Game, slug=slug, slots__gt=0)
	try:
		player = Player.objects.get(user=request.user, game=g)
	except:
		## the user is not in the game
		messages.error(request, _("You had not joined this game."))
	else:
		player.delete()
		g.slots += 1
		g.save()
		cache.delete('sidebar_activity')
		messages.success(request, _("You have left the game."))
		## if the game has no players, delete the game
		if g.player_set.count() == 0:
			g.delete()
			messages.info(request, _("The game has been deleted."))
	return redirect('summary')

@login_required
def make_public(request, slug=''):
	g = get_object_or_404(Game, slug=slug, slots__gt=0,
						private=True, created_by=request.user)
	g.private = False
	g.save()
	g.invitation_set.all().delete()
	messages.success(request, _("The game is now open to all users."))
	return redirect('games-pending')

@login_required
def overthrow(request, revolution_id):
	revolution = get_object_or_404(Revolution, pk=revolution_id)
	g = revolution.government.game
	try:
		## check that overthrowing user is not a player
		Player.objects.get(user=request.user, game=g)
	except ObjectDoesNotExist:
		try:
			## check that there is not another revolution with the same player
			Revolution.objects.get(government__game=g, opposition=request.user)
		except ObjectDoesNotExist:
			karma = request.user.get_profile().karma
			if karma < settings.KARMA_TO_JOIN:
				err = _("You need a minimum karma of %s to join a game.") % settings.KARMA_TO_JOIN
				messages.error(request, err)
				return redirect("summary")
			revolution.opposition = request.user
			revolution.save()
			messages.success(request, _("Your overthrow attempt has been saved."))
		else:
			messages.error(request, _("You are already attempting an overthrow on another player in the same game."))
	else:
		messages.error(request, _("You are already playing this game."))
	return redirect("summary")

@login_required

# --- Excommunication Views (unchanged logic, rely on model methods) ---
@login_required
def excommunicate(request, slug, player_id):
	# ... (remains same) ...
	game = get_object_or_404(Game, slug=slug)
	if game.phase == PHINACTIVE or not game.configuration.excommunication:
		messages.error(request, _("You cannot excommunicate in this game or phase."))
		return redirect(game)
	papacy = get_object_or_404(Player, user=request.user, game=game, may_excommunicate=True)
	if not papacy.can_excommunicate():
		messages.error(request, _("You cannot excommunicate in the current season or have already acted."))
		return redirect(game)
	try:
		player = Player.objects.get(game=game, id=player_id, eliminated=False, conqueror__isnull=True, may_excommunicate=False)
	except Player.DoesNotExist:
		messages.error(request, _("You cannot excommunicate this country (perhaps already eliminated or is the Papacy?)."))
	else:
		player.set_excommunication(by_pope=True)
		papacy.has_sentenced = True
		papacy.save(update_fields=['has_sentenced'])
		messages.success(request, _("%(country)s has been excommunicated.") % {'country': player.country})
	return redirect(game)

@login_required
def forgive_excommunication(request, slug, player_id):
	# ... (remains same) ...
	game = get_object_or_404(Game, slug=slug)
	if game.phase == PHINACTIVE or not game.configuration.excommunication:
		messages.error(request, _("You cannot forgive excommunications in this game or phase."))
		return redirect(game)
	papacy = get_object_or_404(Player, user=request.user, game=game, may_excommunicate=True)
	if not papacy.can_forgive():
		messages.error(request, _("You cannot forgive excommunications in the current season or have already acted."))
		return redirect(game)
	try:
		player = Player.objects.get(game=game, id=player_id, eliminated=False, conqueror__isnull=True, is_excommunicated=True)
	except Player.DoesNotExist:
		messages.error(request, _("This country is not currently excommunicated or cannot be forgiven."))
	else:
		player.unset_excommunication()
		papacy.has_sentenced = True
		papacy.save(update_fields=['has_sentenced'])
		messages.success(request, _("%(country)s has been forgiven.") % {'country': player.country})
	return redirect(game)

#@cache_page(60 * 60)
def scenario_list(request):
	""" Gets a list of all the enabled scenarios. """
	context = sidebar_context(request)	
	scenarios = Scenario.objects.filter(enabled=True)
	context.update( {'scenarios': scenarios, })

	return render_to_response('machiavelli/scenario_list.html',
							context,
							context_instance = RequestContext(request))

@never_cache
def show_scenario(request, scenario_id):
	scenario = get_object_or_404(Scenario, id=scenario_id, enabled=True)

	countries = Country.objects.filter(home__scenario=scenario).distinct()
	autonomous = Setup.objects.filter(scenario=scenario, country__isnull=True)
	major_cities = scenario.cityincome_set.all()
	disabled_areas = Area.objects.filter(disabledarea__scenario=scenario).values_list('name', flat=True)

	countries_dict = {}

	for c in countries:
		data = {}
		data['name'] = c.name
		data['homes'] = c.home_set.select_related().filter(scenario=scenario)
		data['setups'] = c.setup_set.select_related().filter(scenario=scenario)
		try:
			treasury = c.treasury_set.get(scenario=scenario)
			data['ducats'] = treasury.ducats
			data['double'] = treasury.double
		except Treasury.DoesNotExist:
			# Create a default treasury for this country
			treasury = Treasury.objects.create(scenario=scenario, country=c, ducats=0, double=False)
			data['ducats'] = 0
			data['double'] = False
		countries_dict[c.static_name] = data

	return render_to_response('machiavelli/scenario_detail.html',
							{'scenario': scenario,
							'countries': countries_dict,
							'autonomous': autonomous,
							'major_cities': major_cities,
							'disabled_areas': disabled_areas,
							},
							context_instance=RequestContext(request))


#@login_required
#@cache_page(30 * 60)
def hall_of_fame(request):
	profiles_list = CondottieriProfile.objects.all().order_by('-weighted_score')
	paginator = Paginator(profiles_list, 10)
	try:
		page = int(request.GET.get('page', '1'))
	except ValueError:
		page = 1
	try:
		profiles = paginator.page(page)
	except (EmptyPage, InvalidPage):
		profiles = paginator.page(paginator.num_pages)
	context = {'profiles': profiles}
	return render_to_response('machiavelli/hall_of_fame.html',
							context,
							context_instance=RequestContext(request))

def ranking(request, key='', val=''):
	""" Gets the qualification, ordered by scores, for a given parameter. """
	
	scores = Score.objects.all().order_by('-points')
	if key == 'user': # by user
		user = get_object_or_404(User, username=val)
		scores = scores.filter(user=user)
		title = _("Ranking for the user") + ' ' + val
	elif key == 'scenario': # by scenario
		scenario = get_object_or_404(Scenario, name=val)
		scores = scores.filter(game__scenario=scenario)
		title = _("Ranking for the scenario") + ' ' + val
	elif key == 'country': # by country
		country = get_object_or_404(Country, css_class=val)
		scores = scores.filter(country=country)
		title = _("Ranking for the country") + ' ' + country.name
	else:
		raise Http404

	paginator = Paginator(scores, 10)
	try:
		page = int(request.GET.get('page', '1'))
	except ValueError:
		page = 1
	try:
		qualification = paginator.page(page)
	except (EmptyPage, InvalidPage):
		qualification = paginator.page(paginator.num_pages)
	context = {
		'qualification': qualification,
		'key': key,
		'val': val,
		'title': title,
		}
	return render_to_response('machiavelli/ranking.html',
							context,
							context_instance=RequestContext(request))

@login_required
#@cache_page(60 * 60) # cache 1 hour
def turn_log_list(request, slug=''):
	game = get_object_or_404(Game, slug=slug)
	log_list = game.turnlog_set.all()
	paginator = Paginator(log_list, 1)
	try:
		page = int(request.GET.get('page', '1'))
	except ValueError:
		page = 1
	try:
		log = paginator.page(page)
	except (EmptyPage, InvalidPage):
		log = paginator.page(paginator.num_pages)
	context = {
		'game': game,
		'log': log,
		}

	return render_to_response('machiavelli/turn_log_list.html',
							context,
							context_instance=RequestContext(request))

# --- Financial/Political Actions ---
@login_required
def give_money(request, slug, player_id):
	# ... (Logic okay, uses LendForm) ...
	game = get_object_or_404(Game, slug=slug)
	if game.phase == PHINACTIVE or not game.configuration.finances: # Check phase and finances
		messages.error(request, _("You cannot give money in this game or phase."))
		return redirect(game)
	borrower = get_object_or_404(Player, id=player_id, game=game)
	lender = get_object_or_404(Player, user=request.user, game=game)

	if lender == borrower:
	    messages.error(request, _("You cannot give money to yourself."))
	    return redirect(game)
	if lender.done:
	    messages.error(request, _("You cannot give money after confirming actions."))
	    return redirect(game)

	context = base_context(request, game, lender)

	if request.method == 'POST':
		form = forms.LendForm(request.POST)
		if form.is_valid():
			ducats = form.cleaned_data['ducats']
			if ducats > lender.ducats:
				messages.error(request, _("You cannot give more money than you have."))
				# Re-render form with error
				context['form'] = form
				context['borrower'] = borrower
				return render_to_response('machiavelli/give_money.html', context, context_instance=RequestContext(request))

			# Use F expressions for atomic update
			Player.objects.filter(id=lender.id).update(ducats=F('ducats') - ducats)
			Player.objects.filter(id=borrower.id).update(ducats=F('ducats') + ducats)

			messages.success(request, _("Successfully sent %(ducats)s ducats to %(country)s.") % {'ducats': ducats, 'country': borrower.country})
			if notification:
				extra_context = {'game': lender.game, 'ducats': ducats, 'country': lender.country, 'STATIC_URL': settings.STATIC_URL}
				notice_users = [borrower.user] if borrower.user else []
				if notice_users:
				    if lender.game.fast: notification.send_now(notice_users, "received_ducats", extra_context)
				    else: notification.send(notice_users, "received_ducats", extra_context)
			return redirect(game)
		else:
		    messages.error(request, _("Invalid amount entered."))
	else:
		form = forms.LendForm()
	context['form'] = form
	context['borrower'] = borrower

	return render_to_response('machiavelli/give_money.html',
							context,
							context_instance=RequestContext(request))

@login_required
def borrow_money(request, slug):
	# ... (Logic okay, uses updated BorrowForm with validation) ...
	game = get_object_or_404(Game, slug=slug)
	player = get_object_or_404(Player, user=request.user, game=game)
	# Allow borrowing only during specific phases (e.g., before Order Writing)
	# Rule X implies during Ducat Borrowing Phase - map this to a game phase like PHLENDERS or before PHORDERS
	allowed_phases = [PHLENDERS, PHNEGOTIATION] # Example: Allow during Negotiation or specific Lender phase
	if game.phase not in allowed_phases or not game.configuration.lenders or player.done:
		messages.error(request, _("You cannot borrow money at this moment."))
		return redirect(game)

	context = base_context(request, game, player)
	credit = player.get_credit()
	try: loan = player.loan
	except Loan.DoesNotExist: loan = None

	if loan: # Player must repay existing loan
		context.update({'loan': loan})
		if request.method == 'POST':
			form = forms.RepayForm(request.POST) # Use RepayForm for confirmation
			if form.is_valid(): # Simple validation for POST
			    if player.ducats >= loan.debt:
			        Player.objects.filter(id=player.id).update(ducats=F('ducats') - loan.debt)
			        loan.delete()
			        messages.success(request, _("You have repaid the loan."))
			    else:
			        messages.error(request, _("You don't have enough money to repay the loan."))
			    return redirect(game)
		else:
			form = forms.RepayForm()
	else: # Player may ask for a new loan
		if player.defaulted: # Rule X.B
		    messages.error(request, _("You cannot borrow money after defaulting on a previous loan."))
		    return redirect(game)
		if credit <= 0:
		     messages.info(request, _("You currently have no credit available to borrow."))
		     # Optionally disable form or show message clearly

		if request.method == 'POST':
			form = forms.BorrowForm(player=player, data=request.POST) # Pass player to form
			if form.is_valid():
				ducats = form.cleaned_data['ducats']
				term = int(form.cleaned_data['term'])
				# Calculate debt based on interest (Rule X.A.3)
				interest_rate = 0.20 if term == 1 else 0.50
				interest = ceil(ducats * interest_rate)
				debt_amount = ducats + int(interest)

				new_loan = Loan(player=player, debt=debt_amount, season=game.season)
				new_loan.year = game.year + term
				new_loan.save()

				Player.objects.filter(id=player.id).update(ducats=F('ducats') + ducats)
				messages.success(request, _("You have borrowed %(ducats)s ducats. You must repay %(debt)s by %(season)s, %(year)s.") % {
				    'ducats': ducats, 'debt': debt_amount, 'season': new_loan.get_season_display(), 'year': new_loan.year
				})
				return redirect(game)
			else:
			    messages.error(request, _("Please correct the errors below."))
		else:
			form = forms.BorrowForm(player=player) # Pass player to form

	context.update({'credit': credit, 'form': form,})
	return render_to_response('machiavelli/borrow_money.html',
							context,
							context_instance=RequestContext(request))

@login_required
def assassination(request, slug):
	# ... (Logic okay, uses updated AssassinationForm) ...
	game = get_object_or_404(Game, slug=slug)
	player = get_object_or_404(Player, user=request.user, game=game)
	# Allow assassination attempts during specific phase (e.g., before Order Writing)
	allowed_phases = [PHORDERS, PHNEGOTIATION] # Example
	if game.phase not in allowed_phases or not game.configuration.assassinations or player.done:
		messages.error(request, _("You cannot attempt an assassination at this moment."))
		return redirect(game)

	context = base_context(request, game, player)
	AssassinationForm = forms.make_assassination_form(player) # Uses updated form maker

	if request.method == 'POST':
		form = AssassinationForm(request.POST)
		if form.is_valid():
			ducats = form.cleaned_data['ducats'] # Already validated as int in [12, 24, 36]
			target_country = form.cleaned_data['target']
			try:
			    target_player = Player.objects.get(game=game, country=target_country)
			except Player.DoesNotExist:
			     messages.error(request, _("Target player not found in this game."))
			     return redirect(game) # Or re-render form

			# Check if player has the assassin token (Model method handles this check implicitly via queryset)
			try:
				assassin_token = Assassin.objects.get(owner=player, target=target_country)
			except Assassin.DoesNotExist:
				messages.error(request, _("You do not have an assassin token for %(country)s.") % {'country': target_country})
				return redirect(game) # Or re-render form

			# Save the attempt, remove token, deduct ducats
			assassination_attempt = Assassination(killer=player, target=target_player, ducats=ducats)
			assassination_attempt.save()
			assassin_token.delete()
			Player.objects.filter(id=player.id).update(ducats=F('ducats') - ducats)

			messages.success(request, _("Assassination attempt against %(country)s recorded.") % {'country': target_country})
			return redirect(game)
		else:
		    messages.error(request, _("Please correct the errors below."))
	else:
		form = AssassinationForm()

	context.update({'form': form,})
	# Check if player can afford *any* attempt
	context['can_afford'] = player.ducats >= 12 and player.assassin_set.exists()
	return render_to_response('machiavelli/assassination.html',
							context,
							context_instance=RequestContext(request))

# --- Whisper Views (unchanged) ---
@login_required
def new_whisper(request, slug):
	# ... (remains same) ...
	game = get_object_or_404(Game, slug=slug)
	try:
		player = Player.objects.get(user=request.user, game=game)
	except ObjectDoesNotExist:
		messages.error(request, _("You cannot write messages in this game"))
		return redirect(game)
	if request.method == 'POST':
		form = forms.WhisperForm(request.user, game, data=request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, _("Whisper sent.")) # Add feedback
		else:
		    messages.error(request, _("Whisper could not be sent.")) # Add feedback
	# Redirect back to game view regardless of success/failure or method
	return redirect(game)


@login_required
def whisper_list(request, slug):
	# ... (remains same) ...
	game = get_object_or_404(Game, slug=slug)
	whisper_list = game.whisper_set.all() # Consider pagination for long lists
	context = {
		'game': game,
		'whisper_list': whisper_list,
		}
	return render_to_response('machiavelli/whisper_list.html',
							context,
							context_instance=RequestContext(request))

# --- AJAX Views ---


@login_required
def get_valid_destinations(request, slug):
    """
    AJAX view to get valid destinations for Advance ('-') or Conversion ('=').
    Includes coast information.
    """
    game = get_object_or_404(Game, slug=slug)
    unit_id = request.GET.get('unit_id')
    order_code = request.GET.get('order_code') # Renamed from order_type for clarity

    response_data = {'destinations': []} # Default empty

    try:
        unit = Unit.objects.select_related('area__board_area', 'player').get(id=unit_id, player__game=game)
        player = Player.objects.get(user=request.user, game=game)

        # --- Permission Check ---
        # Basic check: Player owns the unit
        can_order = (unit.player == player)
        # Advanced: Allow ordering if bought via bribe (requires tracking confirmed bribes)
        # if not can_order and game.configuration.finances:
        #     can_order = Expense.objects.filter(player=player, type=10, unit=unit, confirmed=True).exists() # Check confirmed 'Buy A/F'

        if not can_order:
             if logging: logging.warning(f"User {request.user} cannot order unit {unit_id}")
             return JsonResponse(response_data)

        # --- Process Order Code ---
        destinations_list = []

        if order_code == '-': # Advance (Rule VII.B.1)
            # 1. Check Preconditions
            if unit.siege_stage > 0: # Rule VII.B.4
                if logging: logging.info(f"Unit {unit_id} cannot advance, siege_stage > 0")
                return JsonResponse(response_data) # Cannot advance if besieging

            # 2. Find Directly Adjacent Valid Destinations
            bordering_areas = unit.area.board_area.borders.all() # Get Area objects
            bordering_game_areas = GameArea.objects.filter(
                game=game, board_area__in=bordering_areas
            ).select_related('board_area') # Get relevant GameAreas efficiently

            for dest_ga in bordering_game_areas:
                # Check adjacency using the unit's current coast
                if unit.area.board_area.is_adjacent(
                    dest_ga.board_area,
                    fleet=(unit.type == 'F'),
                    source_unit_coast=unit.coast # Pass current coast
                ) and dest_ga.board_area.accepts_type(unit.type):
                    destinations_list.append({
                        'id': dest_ga.id,
                        'name': dest_ga.board_area.name,
                        'code': dest_ga.board_area.code,
                        'coasts': dest_ga.board_area.get_coast_list(), # Add coasts info ['nc', 'sc']
                        'convoy_only': False
                    })

            # 3. Find Potential Convoy Destinations (Army on Coast only) (Rule VII.B.6)
            if unit.type == 'A' and unit.area.board_area.is_coast:
                direct_move_ids = {d['id'] for d in destinations_list} # Set of direct move IDs
                # Find all coastal areas in the game, excluding current area and direct moves
                potential_convoy_gareas = GameArea.objects.filter(
                    game=game, board_area__is_coast=True
                ).exclude(
                    id__in=direct_move_ids | {unit.area.id} # Exclude current and direct using set union
                ).select_related('board_area')

                for dest_ga in potential_convoy_gareas:
                    # No complex path check here, just offer all other coastal areas as options
                    destinations_list.append({
                        'id': dest_ga.id,
                        'name': dest_ga.board_area.name,
                        'code': dest_ga.board_area.code,
                        'coasts': dest_ga.board_area.get_coast_list(), # Add coasts info
                        'convoy_only': True # Mark as needing convoy
                    })

            response_data['destinations'] = destinations_list

        elif order_code == '=': # Conversion (Rule VII.B.7)
            valid_types = []
            # 1. Check Preconditions
            if not unit.area.board_area.is_fortified: # Rule VII.B.7.a
                 return JsonResponse(response_data)
            # Rule VII.B.7.h: Besieged Garrison may not convert
            if unit.type == 'G' and Unit.objects.filter(area=unit.area, siege_stage__gt=0).exclude(id=unit.id).exists():
                 return JsonResponse(response_data)

            # 2. Determine Valid Conversion Types
            board_area = unit.area.board_area
            if unit.type == 'G': # G -> A or F
                valid_types.append('A')
                if board_area.has_port: valid_types.append('F') # Rule VII.B.7.c
            elif unit.type in ['A', 'F']: # A/F -> G
                # Check if city is empty of *other* Garrisons (Rule VII.B.1.b)
                if not Unit.objects.filter(area=unit.area, type='G').exclude(id=unit.id).exists():
                     # Fleet needs port to convert to G? Rule VII.B.7.b implies yes.
                     if unit.type == 'A' or (unit.type == 'F' and board_area.has_port):
                          valid_types.append('G')
            # Direct A<->F disallowed (Rule VII.B.7.d)

            # 3. Build Response (Only includes current area, but lists valid types)
            if valid_types:
                 destinations_list = [{
                     'id': unit.area.id, # Target is always the current area for conversion itself
                     'name': unit.area.board_area.name,
                     'code': unit.area.board_area.code,
                     'valid_types': valid_types, # Pass valid types to JS
                     'coasts': [] # Coasts not relevant for conversion target itself
                 }]
            response_data['destinations'] = destinations_list

        # --- Handle other order codes (L, 0, B, S, C) ---
        # These generally don't need a primary destination list from this view.
        # Support ('S') and Convoy ('C') use get_valid_support_destinations / get_supportable_units.
        # Lift Siege ('L'), Disband ('0'), Besiege ('B') don't target another area.
        else:
            if logging: logging.debug(f"Order code '{order_code}' does not require destinations from this view.")
            # response_data remains {'destinations': []}

    except (Unit.DoesNotExist, Player.DoesNotExist, GameArea.DoesNotExist) as e:
        if logging: logging.error(f"Error in get_valid_destinations for game {slug}: {e}")
        # Return default empty list on error, don't expose internal errors
        response_data = {'destinations': []}
    except Exception as e: # Catch unexpected errors
         if logging: logging.error(f"Unexpected error in get_valid_destinations for game {slug}: {e}")
         response_data = {'destinations': []}


    return JsonResponse(response_data)


@login_required
def get_valid_support_destinations(request, slug):
    """
    AJAX view: Given a SUPPORTING unit, find AREAS it can support into.
    Rule VII.B.5.a: Supporter must be able to advance into the target area.
    """
    game = get_object_or_404(Game, slug=slug)
    unit_id = request.GET.get('unit_id') # The SUPPORTING unit

    response_data = {'destinations': []}

    try:
        unit = Unit.objects.select_related('area__board_area', 'player').get(id=unit_id, player__game=game)
        player = Player.objects.get(user=request.user, game=game)

        if unit.player != player: # Basic ownership check
            return JsonResponse(response_data)

        supportable_target_areas = []
        # Rule VII.B.5.c: Garrison supports own province
        if unit.type == 'G':
            supportable_target_areas = [unit.area]
        else:
            # Rule VII.B.5.a: Must be able to advance into the supported area (without transport)
            possible_advances = unit.area.board_area.borders.all()
            for area_board in possible_advances:
                 try:
                    game_area = GameArea.objects.get(game=game, board_area=area_board)
                    # Check direct adjacency (no convoy allowed for support reach)
                    if unit.area.board_area.is_adjacent(area_board,
                                                        fleet=(unit.type == 'F'),
                                                        source_unit_coast=unit.coast):
                         # Check unit type compatibility with target area
                         # Army cannot support into sea, Fleet cannot support into non-coast/non-sea
                         if unit.type == 'A' and game_area.board_area.is_sea: continue
                         if unit.type == 'F' and not game_area.board_area.is_sea and not game_area.board_area.is_coast: continue

                         supportable_target_areas.append(game_area)
                 except GameArea.DoesNotExist:
                     continue
            # Also include unit's own area (for supporting Hold)
            if unit.area not in supportable_target_areas:
                 supportable_target_areas.append(unit.area)

        # Format response including coast info for target areas
        destinations = [{
            'id': area.id,
            'name': area.board_area.name,
            'code': area.board_area.code,
            'coasts': area.board_area.get_coast_list() # Include coasts of potential target areas
        } for area in supportable_target_areas]

        response_data['destinations'] = destinations

    except (Unit.DoesNotExist, Player.DoesNotExist, GameArea.DoesNotExist) as e:
        if logging: logging.error(f"Error in get_valid_support_destinations for game {slug}: {e}")
        response_data = {'destinations': []}
    except Exception as e:
         if logging: logging.error(f"Unexpected error in get_valid_support_destinations for game {slug}: {e}")
         response_data = {'destinations': []}

    return JsonResponse(response_data)


@login_required
def get_supportable_units(request, slug):
    """
    AJAX view: Given a SUPPORTING unit and a TARGET AREA, find units
    in that area (or potentially moving to it) that can be supported.
    """
    game = get_object_or_404(Game, slug=slug)
    unit_id = request.GET.get('unit_id') # The SUPPORTING unit
    target_area_id = request.GET.get('target_area_id') # The AREA being supported INTO

    response_data = {'units': []}

    try:
        unit = Unit.objects.select_related('area__board_area', 'player').get(id=unit_id, player__game=game)
        target_area = GameArea.objects.select_related('board_area').get(id=target_area_id, game=game)
        player = Player.objects.get(user=request.user, game=game)

        if unit.player != player:
            return JsonResponse(response_data)

        # --- Check if supporter can actually support into target_area ---
        can_support_target = False
        if unit.type == 'G':
             can_support_target = (unit.area == target_area) # Rule VII.B.5.c
        else:
             # Rule VII.B.5.a: Must be able to advance into target_area (no transport)
             can_support_target = unit.area.board_area.is_adjacent(target_area.board_area,
                                                                    fleet=(unit.type == 'F'),
                                                                    source_unit_coast=unit.coast)
             # Check type compatibility
             if unit.type == 'A' and target_area.board_area.is_sea: can_support_target = False
             if unit.type == 'F' and not target_area.board_area.is_sea and not target_area.board_area.is_coast: can_support_target = False

        if not can_support_target:
             if logging: logging.warning(f"Unit {unit_id} cannot support into area {target_area_id}")
             return JsonResponse(response_data)

        # --- Find units to be supported in the target area ---
        # 1. Units HOLDING in the target area
        holding_units = Unit.objects.filter(
            player__game=game, area=target_area
        ).exclude(id=unit.id).select_related('area__board_area', 'player__country') # Exclude self

        # 2. Units attempting to MOVE INTO the target area
        # Find areas adjacent to target_area from which a unit could move in
        possible_origins = GameArea.objects.filter(
             game=game, board_area__borders=target_area.board_area
        ).select_related('board_area')

        moving_units_qs = Unit.objects.none()
        for origin_ga in possible_origins:
             # Check if units in origin_ga could move to target_area
             units_in_origin = Unit.objects.filter(player__game=game, area=origin_ga)
             for u_origin in units_in_origin:
                  if u_origin.area.board_area.is_adjacent(target_area.board_area,
                                                          fleet=(u_origin.type == 'F'),
                                                          source_unit_coast=u_origin.coast):
                       # Check if this unit has an order to move to target_area
                       # This requires looking at unconfirmed orders, potentially complex.
                       # Simplification: List all units that *could* move into the target area.
                       # The user selects the intended supported unit/move in the form.
                       moving_units_qs |= Q(id=u_origin.id)


        # Combine holding and potentially moving units
        supportable_units = (holding_units | Unit.objects.filter(moving_units_qs)) \
                            .distinct().order_by('player__country__name', 'type', 'area__board_area__code')

        # Format response
        units_data = [{'id': u.id, 'description': u.supportable_order()} for u in supportable_units]
        response_data['units'] = units_data

    except (Unit.DoesNotExist, Player.DoesNotExist, GameArea.DoesNotExist) as e:
        if logging: logging.error(f"Error in get_supportable_units for game {slug}: {e}")
        response_data = {'units': []}
    except Exception as e:
         if logging: logging.error(f"Unexpected error in get_supportable_units for game {slug}: {e}")
         response_data = {'units': []}

    return JsonResponse(response_data)


@login_required
def get_area_info(request, slug):
    """AJAX view to get area information, including coasts."""
    game = get_object_or_404(Game, slug=slug)
    area_id = request.GET.get('area_id')
    area_info = {'has_city': False, 'is_fortified': False, 'has_port': False, 'coasts': []} # Default

    try:
        game_area = GameArea.objects.select_related('board_area').get(id=area_id, game=game)
        board_area = game_area.board_area

        area_info = {
            'has_city': board_area.has_city,
            'is_fortified': board_area.is_fortified,
            'has_port': board_area.has_port,
            'coasts': board_area.get_coast_list() # Get list of coast names ['nc', 'sc']
        }
    except GameArea.DoesNotExist:
        pass # Return default info
    except Exception as e: # Catch unexpected errors
         if logging: logging.error(f"Unexpected error in get_area_info for game {slug}, area {area_id}: {e}")
         pass

    return JsonResponse(area_info)

def get_valid_adjacent_areas(game, area, for_fleet=False):

    """Helper function to get valid adjacent areas that units could move from or support into"""
    # Get all areas that border this area's board area
    adjacent_areas = GameArea.objects.filter(
        game=game,
        board_area__in=area.board_area.borders.all()
    )

    if logging:
        logging.info("Found adjacent areas: {}".format(
            [a.board_area.code for a in adjacent_areas]))

    # Filter based on unit type
    if for_fleet:
        adjacent_areas = adjacent_areas.filter(
            Q(board_area__is_sea=True) | Q(board_area__is_coast=True)
        )
        # Check if areas are actually adjacent for fleets
        adjacent_areas = [a for a in adjacent_areas 
                        if area.board_area.is_adjacent(a.board_area, fleet=True)]
    else:
        # For armies: exclude seas and Venice
        adjacent_areas = adjacent_areas.exclude(
            Q(board_area__is_sea=True) | Q(board_area__code='VEN')
        )

    return adjacent_areas

def get_supportable_units_query(game, unit, valid_areas=None):
    """Helper function to build the query for finding supportable units."""
    query = Q(player__game=game)
    
    # For convoy orders, we only want Army units in coastal territories
    if unit.type == 'F' and unit.area.board_area.is_sea:
        query &= Q(
            type='A',  # Must be an army
            area__board_area__is_coast=True  # Must be in a coastal territory
        )
    # For fleets providing support
    elif unit.type == 'F': #Fleet
        # Get adjacent areas that are valid for fleet support
        valid_areas = GameArea.objects.filter(
            game=game,
            board_area__in=unit.area.board_area.borders.all()
        ).filter(
            Q(board_area__is_sea=True) | Q(board_area__is_coast=True) #Sea or Coast
        )
        # Check if areas are actually adjacent for fleets
        valid_areas = [a for a in valid_areas 
                      if unit.area.board_area.is_adjacent(a.board_area, fleet=True)]
        
        # Convert back to queryset
        valid_areas = GameArea.objects.filter(id__in=[a.id for a in valid_areas])
        
        fleet_support = Q(area__in=valid_areas, type='F')
        direct_army_support = Q(area__in=valid_areas.filter(board_area__is_coast=True), type='A')
        
        #Armies that could be convoyed to adjacent coastal territories
        convoy_army_support = Q(
            type='A',
            area__board_area__is_coast=True,
        )
        
        query &= (
            fleet_support |
            direct_army_support |
            convoy_army_support
        )

    # For armies supporting fleets, we need to include fleets in adjacent seas
    elif unit.type == 'A': #Army
        # Get territories the army could support into
        supportable_areas = get_valid_adjacent_areas(game, unit.area, for_fleet=False)

        
        # For fleets, we need to check if they can actually move to any of our supportable areas
        fleet_areas = []
        for area in supportable_areas:
            # Find seas adjacent to this supportable area
            adjacent_seas = GameArea.objects.filter(
                game=game,
                board_area__is_sea=True,
                board_area__borders=area.board_area
            )
            # Only include seas that are actually adjacent for fleets
            fleet_areas.extend([s for s in adjacent_seas 
                              if s.board_area.is_adjacent(area.board_area, fleet=True)])
        
        # Convert to unique list
        fleet_areas = list(set(fleet_areas))
        
        # Include units in current area, supportable areas, and valid fleet areas
        area_conditions = ( #Units in same area
            Q(area=unit.area) |
            Q(area__in=supportable_areas, type='A') | #Armies in supportable areas
            Q(area__in=fleet_areas, type='F') #Fleets that can move to supportable areas
        )
        query &= area_conditions

    else:  # Garrison - For garrisons, use normal adjacent area logic
        area_conditions = Q(area=unit.area)
        if valid_areas is not None:
            area_conditions |= Q(area__in=valid_areas)
        query &= area_conditions
    
    # Exclude self and garrisons (except when supporting into their own province)
    exclude_conditions = Q(id=unit.id)
    if unit.type != 'G':
        if valid_areas:
            exclude_conditions |= Q(
                type='G',
                area__in=valid_areas.exclude(id=unit.area.id)
            )
    
    # Get the units
    supportable_units = Unit.objects.filter(query).exclude(exclude_conditions).select_related('area', 'area__board_area', 'player')
    
    if logging:
        logging.info("Found %d supportable units" % supportable_units.count())
        for u in supportable_units:
            logging.info("Supportable unit: %s in %s" % (u, u.area))
            
    return supportable_units

@login_required
def get_supportable_units(request, slug):
    # ... (Needs careful review based on rules VII.B.5) ...
    game = get_object_or_404(Game, slug=slug)
    unit_id = request.GET.get('unit_id')
    # for_convoy = request.GET.get('for_convoy') == 'true' # Handled separately?

    response_data = {'units': []}

    try:
        unit = Unit.objects.get(id=unit_id, player__game=game)
        player = Player.objects.get(user=request.user, game=game)

        if unit.player != player:
            return JsonResponse(response_data)

        # Find units that this unit *could* potentially support
        # Rule VII.B.5.a: Support into adjacent areas unit could move to.
        supportable_target_areas_q = Q()
        if unit.type == 'G':
             supportable_target_areas_q = Q(id=unit.area.id)
        else:
            possible_advances = unit.area.board_area.borders.all()
            valid_area_ids = [unit.area.id] # Can always support hold in own area
            for area_board in possible_advances:
                 try:
                    game_area = GameArea.objects.get(game=game, board_area=area_board)
                    if unit.area.board_area.is_adjacent(area_board, fleet=(unit.type == 'F')) and \
                       game_area.board_area.accepts_type(unit.type):
                        valid_area_ids.append(game_area.id)
                 except GameArea.DoesNotExist:
                     continue
            supportable_target_areas_q = Q(id__in=valid_area_ids)

        # Find units located in those areas (or potentially moving into them)
        # This is complex as it depends on the *other* units' orders which aren't known yet.
        # Simplification: List units currently *in* the areas the supporting unit can reach.
        target_units = Unit.objects.filter(
            player__game=game,
            area__in=GameArea.objects.filter(supportable_target_areas_q)
        ).exclude(id=unit.id).select_related('area', 'area__board_area', 'player') # Exclude self

        # Filter out units that cannot be supported based on type? (e.g. Army supporting Fleet?)
        # Rule doesn't explicitly forbid this, only that supporter must be able to reach target area.

        units_data = [{'id': u.id, 'description': u.supportable_order()} for u in target_units]
        response_data['units'] = units_data

    except (Unit.DoesNotExist, Player.DoesNotExist):
        pass

    return JsonResponse(response_data)
    # return HttpResponse(json.dumps(response_data, ensure_ascii=False), content_type='application/json')

