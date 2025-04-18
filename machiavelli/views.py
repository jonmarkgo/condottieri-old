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
from django.http import HttpResponseRedirect, Http404, HttpResponse
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
from django.utils import simplejson
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


from machiavelli.models import Unit


def sidebar_context(request):
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
		if not request.user.get_profile() in top_users:
			my_score = request.user.get_profile().weighted_score
			my_position = CondottieriProfile.objects.filter(weighted_score__gt=my_score).count() + 1
			context.update({'my_position': my_position,})
	latest_gossip = cache.get('latest_gossip')
	if not latest_gossip:
		latest_gossip = Whisper.objects.all()[:5]
		cache.set('latest_gossip', latest_gossip)
	server = Server.objects.get()
	ranking_last_update = server.ranking_last_update
	context.update({ 'activity': activity,
				'top_users': top_users,
				'whispers': latest_gossip,
				'ranking_last_update': ranking_last_update,})
	return context

def summary(request):
	context = sidebar_context(request)
	context.update( {'forum': 'forum' in settings.INSTALLED_APPS} )
	if request.user.is_authenticated():
		joinable = Game.objects.exclude(player__user=request.user).filter(slots__gt=0, private=False).order_by('slots').select_related('scenario', 'configuration', 'player__user')
		my_games_ids = Game.objects.filter(player__user=request.user).values('id')
		context.update( {'revolutions': Revolution.objects.filter(opposition__isnull=True).exclude(government__game__id__in=my_games_ids).select_related('gorvernment__game__country')} )
		context.update( {'actions': Player.objects.filter(user=request.user, game__slots=0, done=False).select_related('game')} )
		## show unseen notices
		if notification:
			new_notices = notification.Notice.objects.notices_for(request.user, unseen=True, on_site=True)
			context.update({'new_notices': new_notices,})
	else:
		joinable = Game.objects.filter(slots__gt=0, private=False).order_by('slots').select_related('scenario', 'configuration', 'player__user')
		context.update( {'revolutions': Revolution.objects.filter(opposition__isnull=True).select_related('government__game__country')} )
	if joinable:
		context.update( {'joinable_game': joinable[0]} )

	return render_to_response('machiavelli/summary.html',
							context,
							context_instance=RequestContext(request))

@never_cache
def my_active_games(request):
	""" Gets a paginated list of all the ongoing games in which the user is a player. """
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
	""" Gets a paginated list of all the ongoing games in which the user is not a player """
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
	""" Gets a paginated list of the games that are finished """
	context = sidebar_context(request)
	games = Game.objects.filter(slots=0, phase=PHINACTIVE).order_by("-finished")
	if only_user:
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
	""" Gets a paginated list of all the games that the user can join """
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
	""" Gets a paginated list of all the games of the player that have not yet
	started """
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
	context = {
		'user': request.user,
		'game': game,
		'map' : game.get_map_url(),
		'player': player,
		'player_list': game.player_list_ordered_by_cities(),
		'show_users': game.visible,
		}
	if game.slots > 0:
		context['player_list'] = game.player_set.filter(user__isnull=False)
	log = game.baseevent_set.all()
	if player:
		context['done'] = player.done
		if game.configuration.finances:
			context['ducats'] = player.ducats
		context['can_excommunicate'] = player.can_excommunicate()
		context['can_forgive'] = player.can_forgive()
		if game.slots == 0:
			context['time_exceeded'] = player.time_exceeded()
		if game.phase == PHORDERS:
			if player.done and not player.in_last_seconds():
				context.update({'undoable': True,})
	log = log.exclude(season__exact=game.season,
							phase__exact=game.phase)
	if len(log) > 0:
		last_year = log[0].year
		last_season = log[0].season
		last_phase = log[0].phase
		context['log'] = log.filter(year__exact=last_year,
								season__exact=last_season,
								phase__exact=last_phase)
	else:
		context['log'] = log # this will always be an empty queryset
	#context['log'] = log[:10]
	rules = game.configuration.get_enabled_rules()
	if len(rules) > 0:
		context['rules'] = rules
	
	if game.configuration.gossip:
		whispers = game.whisper_set.all()[:10]
		context.update({'whispers': whispers, })
		if player:
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

@login_required
def undo_actions(request, slug=''):
	game = get_object_or_404(Game, slug=slug)
	player = get_object_or_404(Player, game=game, user=request.user)
	profile = request.user.get_profile()
	if request.method == 'POST':
		if game.phase == PHORDERS:
			if player.done and not player.in_last_seconds():
				player.done = False
				player.order_set.update(confirmed=False)
				player.expense_set.update(confirmed=False)
				if game.check_bonus_time():
					profile.adjust_karma( -1 )
				player.save()
				messages.success(request, _("Your actions are now unconfirmed. You'll have to confirm then again."))

	return redirect('show-game', slug=slug)

@never_cache
#@login_required
def play_game(request, slug='', **kwargs):
	game = get_object_or_404(Game, slug=slug)
	if game.slots == 0 and game.phase == PHINACTIVE:
		return redirect('game-results', slug=game.slug)
	try:
		player = Player.objects.get(game=game, user=request.user)
	except:
		player = Player.objects.none()
	if player:
		##################################
		## IP TRACKING FOR CLONES DETECTION
		if clones:
			if request.method == 'POST' and not request.is_ajax():
				try:
					fp = clones.Fingerprint(user=request.user,
											game=game,
											ip=request.META[settings.IP_HEADER])
					fp.save()
				except:
					pass
		##################################
		#if game.slots == 0:
		#	game.check_time_limit()
		if game.phase == PHINACTIVE:
			context = base_context(request, game, player)
			return render_to_response('machiavelli/inactive_actions.html',
							context,
							context_instance=RequestContext(request))
		elif game.phase == PHREINFORCE:
			if game.configuration.finances:
				return play_finance_reinforcements(request, game, player)
			else:
				return play_reinforcements(request, game, player)
		elif game.phase == PHORDERS:
			if 'extra' in kwargs and kwargs['extra'] == 'expenses':
				if game.configuration.finances:
					return play_expenses(request, game, player)
			return play_orders(request, game, player)
		elif game.phase == PHRETREATS:
			return play_retreats(request, game, player)
		else:
			raise Http404
	## no player
	else:
		context = base_context(request, game, player)
		return render_to_response('machiavelli/inactive_actions.html',
							context,
							context_instance=RequestContext(request))

def play_reinforcements(request, game, player):
	context = base_context(request, game, player)
	if player.done:
		context['to_place'] = player.unit_set.filter(placed=False)
		context['to_disband'] = player.unit_set.filter(placed=True, paid=False)
		context['to_keep'] = player.unit_set.filter(placed=True, paid=True)
	else:
		units_to_place = player.units_to_place()
		context['cities_qty'] = player.number_of_cities()
		context['cur_units'] = len(player.unit_set.all())
		if units_to_place > 0:
			## place units
			context['units_to_place'] = units_to_place
			ReinforceForm = forms.make_reinforce_form(player)
			ReinforceFormSet = formset_factory(ReinforceForm,
								formset=forms.BaseReinforceFormSet,
								extra=units_to_place)
			if request.method == 'POST':
				reinforce_form = ReinforceFormSet(request.POST)
				if reinforce_form.is_valid():
					for f in reinforce_form.forms:
						new_unit = Unit(type=f.cleaned_data['type'],
								area=f.cleaned_data['area'],
								player=player,
								placed=False)
						new_unit.save()
						#new_unit.place()
					#game.map_changed()
					## not sure, but i think i could remove the fol. line
					player = Player.objects.get(id=player.pk) ## see below
					player.end_phase()
					messages.success(request, _("You have successfully made your reinforcements."))
					return HttpResponseRedirect(request.path)
			else:
				reinforce_form = ReinforceFormSet()
			context['reinforce_form'] = reinforce_form
		elif units_to_place < 0:
			## remove units
			DisbandForm = forms.make_disband_form(player)
			#choices = []
			context['units_to_disband'] = -units_to_place
			#for unit in player.unit_set.all():
			#	choices.append((unit.pk, unit))
			if request.method == 'POST':
				disband_form = DisbandForm(request.POST)
				if disband_form.is_valid():
					if len(disband_form.cleaned_data['units']) == -units_to_place:
						for u in disband_form.cleaned_data['units']:
							#u.delete()
							u.paid = False
							u.save()
						#game.map_changed()
						## odd: the player object needs to be reloaded or
						## the it doesn't know the change in game.map_outdated
						## this hack needs to be done in some other places
						player = Player.objects.get(id=player.pk)
						## --
						player.end_phase()
						messages.success(request, _("You have successfully made your reinforcements."))
						return HttpResponseRedirect(request.path)
			else:
				disband_form = DisbandForm()
			context['disband_form'] = disband_form
	return render_to_response('machiavelli/reinforcements_actions.html',
							context,
							context_instance=RequestContext(request))

def play_finance_reinforcements(request, game, player):
	context = base_context(request, game, player)
	# Check if any players are not done
	any_not_done = game.player_set.filter(done=False).exists()
	if player.done and any_not_done:
		context['to_place'] = player.unit_set.filter(placed=False)
		context['to_disband'] = player.unit_set.filter(placed=True, paid=False)
		context['to_keep'] = player.unit_set.filter(placed=True, paid=True)
		template_name = 'machiavelli/reinforcements_actions.html'
	else:
		step = player.step
		if game.configuration.lenders:
			try:
				loan = player.loan
			except ObjectDoesNotExist:
				pass
			else:
				context.update({'loan': loan})
		if game.configuration.special_units:
			context.update({'special_units': True})
		if step == 0:
			## the player must select the units that he wants to pay and keep
			UnitPaymentForm = forms.make_unit_payment_form(player)
			if request.method == 'POST':
				form = UnitPaymentForm(request.POST)
				if form.is_valid():
					cost = sum(u.cost for u in form.cleaned_data['units'])
					# We know we have enough ducats due to form validation
					for u in form.cleaned_data['units']:
						u.paid = True
						u.save()
					player.ducats = player.ducats - cost
					step = 1
					player.step = step
					player.save()
					messages.success(request, _("You have successfully paid your units."))
					return HttpResponseRedirect(request.path)
				else:
					messages.error(request, _("There was an error with your unit payment."))
			else:
				form = UnitPaymentForm()
			context['form'] = form
		elif step == 1:
			## the player can create new units if he has money and areas
			can_buy = player.ducats / 3
			can_place = player.get_areas_for_new_units(finances=True).count()
			max_units = min(can_buy, can_place)
			print("Max no of units is %s" % max_units)
			ReinforceForm = forms.make_reinforce_form(player, finances=True,
												special_units=game.configuration.special_units)
			ReinforceFormSet = formset_factory(ReinforceForm,
								formset=forms.BaseReinforceFormSet,
								extra=max_units)
			if request.method == 'POST':
				try:
					formset = ReinforceFormSet(request.POST)
				except ValidationError:
					formset = None
				if formset and formset.is_valid():
					total_cost = 0
					for f in formset.forms:
						if 'area' in f.cleaned_data:
							new_unit = Unit(type=f.cleaned_data['type'],
									area=f.cleaned_data['area'],
									player=player,
									placed=False)
							if 'unit_class' in f.cleaned_data:
								if not f.cleaned_data['unit_class'] is None:
									unit_class = f.cleaned_data['unit_class']
									## it's a special unit
									new_unit.cost = unit_class.cost
									new_unit.power = unit_class.power
									new_unit.loyalty = unit_class.loyalty
							new_unit.save()
							total_cost += new_unit.cost
					player.ducats = player.ducats - total_cost
					player.save()
					player.end_phase()
					messages.success(request, _("You have successfully made your reinforcements."))
					return HttpResponseRedirect(request.path)
			else:
				formset = ReinforceFormSet()
			context['formset'] = formset
			context['max_units'] = max_units
		else:
			raise Http404
		template_name = 'machiavelli/finance_reinforcements_%s.html' % step
	return render_to_response(template_name, context,
							context_instance=RequestContext(request))


def play_orders(request, game, player):
	context = base_context(request, game, player)
	#sent_orders = Order.objects.filter(unit__in=player.unit_set.all())
	sent_orders = player.order_set.all()
	context.update({'sent_orders': sent_orders})
	if game.configuration.finances:
		context['current_expenses'] = player.expense_set.all()
	if game.configuration.assassinations:
		context['assassinations'] = player.assassination_attempts.all()
	if game.configuration.lenders:
		try:
			loan = player.loan
		except ObjectDoesNotExist:
			pass
		else:
			context.update({'loan': loan})
	if not player.done:
		OrderForm = forms.make_order_form(player)
		if request.method == 'POST':
			order_form = OrderForm(player, data=request.POST)
			if request.is_ajax():
				## validate the form
				clean = order_form.is_valid()
				response_dict = {'bad': 'false'}
				if not clean:
					response_dict.update({'bad': 'true'})
					d = {}
					for e in order_form.errors.iteritems():
						d.update({e[0] : unicode(e[1])})
					response_dict.update({'errs': d})
				else:
					#new_order = Order(**order_form.cleaned_data)
					#new_order.save()
					new_order = order_form.save()
					response_dict.update({'pk': new_order.pk ,
										'new_order': new_order.explain()})
				response_json = simplejson.dumps(response_dict, ensure_ascii=False)

				return HttpResponse(response_json, mimetype='application/javascript')
			## not ajax
			else:
				if order_form.is_valid():
					#new_order = Order(**order_form.cleaned_data)
					#new_order.save()
					new_order = order_form.save()
					return HttpResponseRedirect(request.path)
		else:
			order_form = OrderForm(player)
		context.update({'order_form': order_form})
	return render_to_response('machiavelli/orders_actions.html',
							context,
							context_instance=RequestContext(request))

@login_required
def delete_order(request, slug='', order_id=''):
	game = get_object_or_404(Game, slug=slug)
	player = get_object_or_404(Player, game=game, user=request.user)
	#order = get_object_or_404(Order, id=order_id, unit__player=player, confirmed=False)
	order = get_object_or_404(Order, id=order_id, player=player, confirmed=False)
	response_dict = {'bad': 'false',
					'order_id': order.id}
	try:
		order.delete()
	except:
		response_dict.update({'bad': 'true'})
	if request.is_ajax():
		response_json = simplejson.dumps(response_dict, ensure_ascii=False)
		return HttpResponse(response_json, mimetype='application/javascript')
		
	return redirect(game)

@login_required
def confirm_orders(request, slug=''):
	""" Confirms orders and expenses in Order Writing phase """
	game = get_object_or_404(Game, slug=slug)
	player = get_object_or_404(Player, game=game, user=request.user, done=False)
	if request.method == 'POST':
		msg = u"Confirming orders for player %s (%s, %s) in game %s (%s):\n" % (player.id,
			player.static_name,
			player.user.username,
			game.id,
			game.slug) 
		sent_orders = player.order_set.all()
		for order in sent_orders:
			msg += u"%s => " % order.format()
			if order.is_possible():
				order.confirm()
				msg += u"OK\n"
			else:
				msg += u"Invalid\n"
		## confirm expenses
		player.expense_set.all().update(confirmed=True)
		if logging:
			logging.info(msg)
		player.end_phase()
		messages.success(request, _("You have successfully confirmed your actions."))
		
		# Check if this is the final player to confirm orders
		# If so, directly trigger the check_turns command
		remaining_players = game.player_set.filter(done=False).count()
		if remaining_players == 0:
			from django.core.management import call_command
			call_command('check_turns')
			
	return redirect(game)		
	
def play_retreats(request, game, player):
	context = base_context(request, game, player)
	if not player.done:
		units = Unit.objects.filter(player=player).exclude(must_retreat__exact='')
		retreat_forms = []
		if request.method == 'POST':
			data = request.POST
			for u in units:
				unitid_key = "%s-unitid" % u.id
				area_key = "%s-area" % u.id
				unit_data = {unitid_key: data[unitid_key], area_key: data[area_key]}
				RetreatForm = forms.make_retreat_form(u)
				retreat_forms.append(RetreatForm(data, prefix=u.id))
			for f in retreat_forms:
				if f.is_valid():
					unitid = f.cleaned_data['unitid']
					area= f.cleaned_data['area']
					unit = Unit.objects.get(id=unitid)
					if isinstance(area, GameArea):
						print("%s will retreat to %s" % (unit, area))
						retreat = RetreatOrder(unit=unit, area=area)
					else:
						print("%s will disband" % unit)
						retreat = RetreatOrder(unit=unit)
					retreat.save()
			player.end_phase()
			messages.success(request, _("You have successfully retreated your units."))
			return HttpResponseRedirect(request.path)
		else:
			for u in units:
				RetreatForm = forms.make_retreat_form(u)
				retreat_forms.append(RetreatForm(prefix=u.id))
		if len(retreat_forms) > 0:
			context['retreat_forms'] = retreat_forms
	return render_to_response('machiavelli/retreats_actions.html',
							context,
							context_instance=RequestContext(request))

def play_expenses(request, game, player):
	context = base_context(request, game, player)
	context['current_expenses'] = player.expense_set.all()
	ExpenseForm = forms.make_expense_form(player)
	if request.method == 'POST':
		form = ExpenseForm(player, data=request.POST)
		if form.is_valid():
			expense = form.save()
			player.ducats = F('ducats') - expense.ducats
			player.save()
			messages.success(request, _("Expense successfully saved."))
			return HttpResponseRedirect(request.path)
	else:
		form = ExpenseForm(player)

	context['form'] = form

	return render_to_response('machiavelli/expenses_actions.html',
							context,
							context_instance=RequestContext(request))

@login_required
def undo_expense(request, slug='', expense_id=''):
	game = get_object_or_404(Game, slug=slug)
	player = get_object_or_404(Player, game=game, user=request.user)
	expense = get_object_or_404(Expense, id=expense_id, player=player)
	try:
		expense.undo()
	except:
		messages.error(request, _("Expense could not be undone."))
	else:
		messages.success(request, _("Expense successfully undone."))
		
	return redirect(game)

#@login_required
#@cache_page(60 * 60)
def game_results(request, slug=''):
	game = get_object_or_404(Game, slug=slug)
	if game.phase != PHINACTIVE:
		raise Http404
	scores = game.score_set.filter(user__isnull=False).order_by('-points')
	context = {'game': game,
				'map' : game.get_map_url(),
				'players': scores,
				'show_log': False,}
	log = game.baseevent_set.all()
	if len(log) > 0:
		context['show_log'] = True
	return render_to_response('machiavelli/game_results.html',
							context,
							context_instance=RequestContext(request))

@never_cache
#@login_required
def logs_by_game(request, slug=''):
	game = get_object_or_404(Game, slug=slug)
	try:
		player = Player.objects.get(game=game, user=request.user)
	except:
		player = Player.objects.none()
	context = base_context(request, game, player)
	log_list = game.baseevent_set.exclude(year__exact=game.year,
										season__exact=game.season,
										phase__exact=game.phase)
	paginator = events_paginator.SeasonPaginator(log_list)
	try:
		year = int(request.GET.get('year'))
	except TypeError:
		year = None
	try:
		season = int(request.GET.get('season'))
	except TypeError:
		season = None
	try:
		log = paginator.page(year, season)
	except (events_paginator.EmptyPage, events_paginator.InvalidPage):
		raise Http404

	context['log'] = log

	return render_to_response('machiavelli/log_list.html',
							context,
							context_instance=RequestContext(request))

@login_required
#@cache_page(60 * 60)
def create_game(request):
	context = sidebar_context(request)
	context.update( {'user': request.user,})
	if request.method == 'POST':
		game_form = forms.GameForm(request.user, data=request.POST)
		config_form = forms.ConfigurationForm(request.POST)
		if game_form.is_valid():
			new_game = game_form.save(commit=False)
			new_game.slots = new_game.scenario.get_slots() - 1
			new_game.save()
			new_player = Player()
			new_player.user = request.user
			new_player.game = new_game
			new_player.save()
			config_form = forms.ConfigurationForm(request.POST,
												instance=new_game.configuration)
			config_form.save()
			cache.delete('sidebar_activity')
			messages.success(request, _("Game successfully created."))
			if new_game.private:
				return redirect('invite-users', slug=new_game.slug)
			else:
				return redirect('summary')
	else:
		game_form = forms.GameForm(request.user)
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
def excommunicate(request, slug, player_id):
	game = get_object_or_404(Game, slug=slug)
	if game.phase == 0 or not game.configuration.excommunication:
		messages.error(request, _("You cannot excommunicate in this game."))
		return redirect(game)
	papacy = get_object_or_404(Player, user=request.user,
								game=game,
								may_excommunicate=True)
	if not papacy.can_excommunicate():
		messages.error(request, _("You cannot excommunicate in the current season."))
		return redirect(game)
	try:
		player = Player.objects.get(game=game, id=player_id, eliminated=False,
									conqueror__isnull=True, may_excommunicate=False)
	except ObjectDoesNotExist:
		messages.error(request, _("You cannot excommunicate this country."))
	else:
		player.set_excommunication(by_pope=True)
		papacy.has_sentenced = True
		papacy.save()
		messages.success(request, _("The country has been excommunicated."))
	return redirect(game)

@login_required
def forgive_excommunication(request, slug, player_id):
	game = get_object_or_404(Game, slug=slug)
	if game.phase == 0 or not game.configuration.excommunication:
		messages.error(request, _("You cannot forgive excommunications in this game."))
		return redirect(game)
	papacy = get_object_or_404(Player, user=request.user,
								game=game,
								may_excommunicate=True)
	if not papacy.can_forgive():
		messages.error(request, _("You cannot forgive excommunications in the current season."))
		return redirect(game)
	try:
		player = Player.objects.get(game=game, id=player_id, eliminated=False,
									conqueror__isnull=True, is_excommunicated=True)
	except ObjectDoesNotExist:
		messages.error(request, _("You cannot forgive this country."))
	else:
		player.unset_excommunication()
		papacy.has_sentenced = True
		papacy.save()
		messages.success(request, _("The country has been forgiven."))
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

@login_required
def give_money(request, slug, player_id):
	game = get_object_or_404(Game, slug=slug)
	if game.phase == 0 or not game.configuration.finances:
		messages.error(request, _("You cannot give money in this game."))
		return redirect(game)
	borrower = get_object_or_404(Player, id=player_id, game=game)
	lender = get_object_or_404(Player, user=request.user, game=game)
	context = base_context(request, game, lender)

	if request.method == 'POST':
		form = forms.LendForm(request.POST)
		if form.is_valid():
			ducats = form.cleaned_data['ducats']
			if ducats > lender.ducats:
				##TODO Move this to form validation
				messages.error(request, _("You cannot give more money than you have"))
				return redirect(game)
			lender.ducats = F('ducats') - ducats
			borrower.ducats = F('ducats') + ducats
			lender.save()
			borrower.save()
			messages.success(request, _("The money has been successfully sent."))
			if notification:
				extra_context = {'game': lender.game,
								'ducats': ducats,
								'country': lender.country,
								'STATIC_URL': settings.STATIC_URL}
				if lender.game.fast:
					notification.send_now([borrower.user,], "received_ducats", extra_context)
				else:
					notification.send([borrower.user,], "received_ducats", extra_context)
			return redirect(game)
	else:
		form = forms.LendForm()
	context['form'] = form
	context['borrower'] = borrower

	return render_to_response('machiavelli/give_money.html',
							context,
							context_instance=RequestContext(request))

@login_required
def borrow_money(request, slug):
	game = get_object_or_404(Game, slug=slug)
	player = get_object_or_404(Player, user=request.user, game=game)
	if game.phase != PHORDERS or not game.configuration.lenders or player.done:
		messages.error(request, _("You cannot borrow money in this moment."))
		return redirect(game)
	context = base_context(request, game, player)
	credit = player.get_credit()
	try:
		loan = player.loan
	except ObjectDoesNotExist:
		## the player may ask for a loan
		if request.method == 'POST':
			form = forms.BorrowForm(request.POST)
			if form.is_valid():
				ducats = form.cleaned_data['ducats']
				term = int(form.cleaned_data['term'])
				if ducats > credit:
					messages.error(request, _("You cannot borrow so much money."))
					return redirect("borrow-money", slug=slug)
				loan = Loan(player=player, season=game.season)
				if term == 1:
					loan.debt = int(ceil(ducats * 1.2))
				elif term == 2:
					loan.debt = int(ceil(ducats * 1.5))
				else:
					messages.error(request, _("The chosen term is not valid."))
					return redirect("borrow-money", slug=slug)
				loan.year = game.year + term
				loan.save()
				player.ducats = F('ducats') + ducats
				player.save()
				messages.success(request, _("You have got the loan."))
				return redirect(game)
		else:
			form = forms.BorrowForm()
	else:
		## the player must repay a loan
		context.update({'loan': loan})
		if request.method == 'POST':
			if player.ducats >= loan.debt:
				player.ducats = F('ducats') - loan.debt
				player.save()
				loan.delete()
				messages.success(request, _("You have repaid the loan."))
			else:
				messages.error(request, _("You don't have enough money to repay the loan."))
			return redirect(game)
		else:
			form = forms.RepayForm()
	context.update({'credit': credit,
					'form': form,})

	return render_to_response('machiavelli/borrow_money.html',
							context,
							context_instance=RequestContext(request))

@login_required
def assassination(request, slug):
	game = get_object_or_404(Game, slug=slug)
	player = get_object_or_404(Player, user=request.user, game=game)
	if game.phase != PHORDERS or not game.configuration.assassinations or player.done:
		messages.error(request, _("You cannot buy an assassination in this moment."))
		return redirect(game)
	context = base_context(request, game, player)
	AssassinationForm = forms.make_assassination_form(player)
	if request.method == 'POST':
		form = AssassinationForm(request.POST)
		if form.is_valid():
			ducats = int(form.cleaned_data['ducats'])
			country = form.cleaned_data['target']
			target = Player.objects.get(game=game, country=country)
			if ducats > player.ducats:
				messages.error(request, _("You don't have enough ducats for the assassination."))
				return redirect(game)
			if target.eliminated:
				messages.error(request, _("You cannot kill an eliminated player."))
				return redirect(game)
			if target == player:
				messages.error(request, _("You cannot kill yourself."))
				return redirect(game)
			try:
				assassin = Assassin.objects.get(owner=player, target=country)
			except ObjectDoesNotExist:
				messages.error(request, _("You don't have any assassins to kill this leader."))
				return redirect(game)
			except MultipleObjectsReturned:
				assassin = Assassin.objects.filter(owner=player, target=country)[0]
			## everything is ok and we should have an assassin token
			assassination = Assassination(killer=player, target=target, ducats=ducats)
			assassination.save()
			assassin.delete()
			player.ducats = F('ducats') - ducats
			player.save()
			messages.success(request, _("The assassination attempt has been saved."))

			return redirect(game)
	else:
		form = AssassinationForm()
	context.update({'form': form,})
	return render_to_response('machiavelli/assassination.html',
							context,
							context_instance=RequestContext(request))

@login_required
def new_whisper(request, slug):
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
	return redirect(game)

@login_required
def whisper_list(request, slug):
	game = get_object_or_404(Game, slug=slug)
	whisper_list = game.whisper_set.all()
	context = {
		'game': game,
		'whisper_list': whisper_list,
		}
	return render_to_response('machiavelli/whisper_list.html',
							context,
							context_instance=RequestContext(request))

@login_required
def get_valid_destinations(request, slug):
	"""AJAX view to get valid destinations for a unit based on order type"""
	game = get_object_or_404(Game, slug=slug)
	unit_id = request.GET.get('unit_id')
	order_type = request.GET.get('order_type')
	
	try:
		unit = Unit.objects.get(id=unit_id)
		# Verify unit belongs to this game
		if unit.player.game != game:
			return HttpResponse(simplejson.dumps({'destinations': []}), mimetype='application/json')
		# Verify the user owns the unit or can give it orders
		if request.user != unit.player.user:
			if not game.configuration.finances:
				return HttpResponse(simplejson.dumps({'destinations': []}), mimetype='application/json')
			# Check if user has bought the unit
			if not Expense.objects.filter(player__user=request.user, type__in=(6,9), unit=unit).exists():
				return HttpResponse(simplejson.dumps({'destinations': []}), mimetype='application/json')
	except Unit.DoesNotExist:
		return HttpResponse(simplejson.dumps({'destinations': []}), mimetype='application/json')

	form = forms.make_order_form(unit.player)(unit.player)
	destinations = []
	
	if order_type == '=':  # Conversion
		# For any unit type converting, they can only convert in their current location
		valid_types = []
		
		# Check if unit is besieged by looking for a besiege order
		if Order.objects.filter(unit=unit, code='B').exists():
			return HttpResponse(simplejson.dumps({'destinations': []}), mimetype='application/json')
		
		# Get valid conversion types based on unit type and area
		if unit.type == 'G':
			# Garrison can convert to Army always, and Fleet if in port
			valid_types.append('A')
			if unit.area.board_area.has_port:
				valid_types.append('F')
		else:
			# Army/Fleet can convert to Garrison if in a city
			if unit.area.board_area.has_city:
				valid_types.append('G')
			
			# Army can convert to Fleet if in port
			if unit.type == 'A' and unit.area.board_area.has_port:
				valid_types.append('F')
			
			# Fleet can convert to Army if in coastal area
			if unit.type == 'F' and unit.area.board_area.is_coast:
				valid_types.append('A')
		
		destinations = [{
			'id': unit.area.id,
			'name': unit.area.board_area.name,
			'code': unit.area.board_area.code,
			'valid_types': valid_types
		}]
	elif order_type == '-':  # Advance
		valid_areas = form.get_valid_destinations(unit, via_convoy=True)
		for area in valid_areas:
			if isinstance(area, tuple):  # Convoy destination
				area, convoy = area
				destinations.append({
					'id': area.id,
					'name': area.board_area.name,
					'code': area.board_area.code,
					'convoy_only': True
				})
			else:
				destinations.append({
					'id': area.id,
					'name': area.board_area.name,
					'code': area.board_area.code,
					'convoy_only': False
				})

	return HttpResponse(simplejson.dumps({'destinations': destinations}), mimetype='application/json')

@login_required
def get_valid_support_destinations(request, slug):

    """AJAX view to get valid destinations for support orders and convoy destinations"""
    game = get_object_or_404(Game, slug=slug)
    unit_id = request.GET.get('unit_id')
    supported_unit_id = request.GET.get('supported_unit_id')
    for_convoy = request.GET.get('for_convoy') == 'true'
    
    if logging:
        logging.info("get_valid_support_destinations called for game %s, unit %s, supported unit %s, for_convoy=%s" % (
            slug, unit_id, supported_unit_id, for_convoy))
    
    try:
        unit = Unit.objects.get(id=unit_id)
        supported_unit = Unit.objects.get(id=supported_unit_id)
        
        if logging:
            logging.info("Supporting unit: %s type=%s in area=%s" % (unit, unit.type, unit.area))
            logging.info("Supported unit: %s type=%s in area=%s" % (supported_unit, supported_unit.type, supported_unit.area))
        
        # Verify units belong to this game
        if unit.player.game != game or supported_unit.player.game != game:
            if logging:
                logging.warning("Units do not belong to this game")
            return HttpResponse(simplejson.dumps({'destinations': []}), mimetype='application/json')
        
        # Verify the user owns the supporting unit
        if request.user != unit.player.user:
            if logging:
                logging.warning("User %s does not own supporting unit" % request.user)
            return HttpResponse(simplejson.dumps({'destinations': []}), mimetype='application/json')
    except (Unit.DoesNotExist, AttributeError):
        if logging:
            logging.warning("Unit %s or %s does not exist" % (unit_id, supported_unit_id))
        return HttpResponse(simplejson.dumps({'destinations': []}), mimetype='application/json')

    if for_convoy:
        # For convoy orders, only show coastal territories as destinations
        destinations = GameArea.objects.filter(
            game=game,
            board_area__is_coast=True  # Must be a coastal territory
        ).exclude(
            id=supported_unit.area.id  # Exclude current location
        )
        
        if logging:
            logging.info("Found %d coastal destinations for convoy" % destinations.count())
            for d in destinations:
                logging.info("Convoy destination: %s" % d)
    else:
        # For garrison units, only allow supporting into their own province
        if unit.type == 'G':
            if logging:
                logging.info("Processing garrison support destinations")
                logging.info("Garrison area: %s" % unit.area)
            
            # For garrisons, always include their own area as a valid support destination
            destinations = GameArea.objects.filter(id=unit.area.id)
            
            if logging:
                logging.info("Garrison destinations: %s" % destinations)
        else:
            if logging:
                logging.info("Processing non-garrison support destinations")
            
            # Get adjacent areas based on supporting unit type
            destinations = GameArea.objects.filter(
                game=game,
                board_area__in=unit.area.board_area.borders.all()
            )

            # Filter based on supporting unit type
            if unit.type == 'F':  # Fleet
                destinations = destinations.filter(
                    Q(board_area__is_sea=True) | Q(board_area__is_coast=True)
                )
                # Check if areas are actually adjacent for fleets
                destinations = [d for d in destinations 
                              if unit.area.board_area.is_adjacent(d.board_area, fleet=True)]
                
                # Filter based on supported unit type
                if supported_unit.type == 'A':  # Army
                    # Fleets can only support armies moving to coastal territories
                    destinations = [d for d in destinations if d.board_area.is_coast]
                elif supported_unit.type == 'F':  # Fleet
                    # Fleets can only support fleets moving to seas or coasts
                    destinations = [d for d in destinations 
                                  if d.board_area.is_sea or d.board_area.is_coast]
            else:  # Army
                # Armies cannot support moves into seas
                destinations = destinations.exclude(board_area__is_sea=True)
                
                # If supporting a fleet, only allow supporting into coastal areas
                if supported_unit.type == 'F':
                    destinations = destinations.filter(board_area__is_coast=True)
            
            # Convert back to queryset if needed
            if not isinstance(destinations, QuerySet):
                destinations = GameArea.objects.filter(id__in=[d.id for d in destinations])
            
            # Always exclude the supported unit's current location for advances
            destinations = destinations.exclude(id=supported_unit.area.id)
            
            if logging:
                logging.info("Non-garrison destinations: %s" % destinations)

    # Build response data
    response_data = {
        'destinations': [{
            'id': area.id,
            'name': area.board_area.name,
            'code': area.board_area.code
        } for area in destinations]
    }

    return HttpResponse(simplejson.dumps(response_data), mimetype='application/json')

@login_required
def get_area_info(request, slug):

	"""AJAX view to get area information for a unit"""
	game = get_object_or_404(Game, slug=slug)
	unit_id = request.GET.get('unit_id')
	
	try:
		unit = Unit.objects.get(id=unit_id)
		# Verify unit belongs to this game
		if unit.player.game != game:
			return HttpResponse(simplejson.dumps({'has_city': False}), mimetype='application/json')
		# Verify the user owns the unit or can give it orders
		if request.user != unit.player.user:
			if not game.configuration.finances:
				return HttpResponse(simplejson.dumps({'has_city': False}), mimetype='application/json')
			# Check if user has bought the unit
			if not Expense.objects.filter(player__user=request.user, type__in=(6,9), unit=unit).exists():
				return HttpResponse(simplejson.dumps({'has_city': False}), mimetype='application/json')
	except Unit.DoesNotExist:
		return HttpResponse(simplejson.dumps({'has_city': False}), mimetype='application/json')

	area_info = {
		'has_city': unit.area.board_area.has_city,
		'is_fortified': unit.area.board_area.is_fortified,
		'has_port': unit.area.board_area.has_port
	}
	
	return HttpResponse(simplejson.dumps(area_info), mimetype='application/json')

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

    """AJAX view to get valid units that can be supported by a unit"""
    game = get_object_or_404(Game, slug=slug)
    unit_id = request.GET.get('unit_id')
    for_convoy = request.GET.get('for_convoy') == 'true'
    
    if logging:
        logging.info("get_supportable_units called for game %s, unit %s, for_convoy=%s" % (
            slug, unit_id, for_convoy))
    
    try:
        unit = Unit.objects.get(id=unit_id)
        if logging:
            logging.info("Found unit: %s type=%s in area=%s" % (unit, unit.type, unit.area))
            logging.info("Unit owner: %s" % unit.player)
        
        # Verify unit belongs to this game
        if unit.player.game != game:
            if logging:
                logging.warning("Unit does not belong to this game")
            return HttpResponse(simplejson.dumps({'units': []}), mimetype='application/json')
        
        # Verify the user owns the unit
        if request.user != unit.player.user:
            if logging:
                logging.warning("User %s does not own unit (owned by %s)" % (request.user, unit.player.user))
            return HttpResponse(simplejson.dumps({'units': []}), mimetype='application/json')
    except Unit.DoesNotExist:
        if logging:
            logging.warning("Unit %s does not exist" % unit_id)
        return HttpResponse(simplejson.dumps({'units': []}), mimetype='application/json')

    if for_convoy:
        # For convoy orders, only show army units in coastal territories
        units = Unit.objects.filter(
            player__game=game,
            type='A',  # Must be an army
            area__board_area__is_coast=True  # Must be in a coastal territory
        ).exclude(
            id=unit.id  # Exclude self
        ).select_related('area', 'area__board_area', 'player')
    else:
        # Get valid adjacent areas based on unit type
        valid_areas = get_valid_adjacent_areas(game, unit.area, for_fleet=(unit.type == 'F'))
        
        # Get supportable units using shared logic
        units = get_supportable_units_query(game, unit, valid_areas)
    
    if logging:
        logging.info("%s unit query: %s" % (
            "Convoy" if for_convoy else "Support",
            units.query))
        logging.info("Found %s potential units" % units.count())
        for u in units:
            logging.info("Found unit: %s type=%s in area=%s" % (
                u, u.type, u.area))
    
    # Build response data
    supportable_units = []
    for u in units:
        desc = u.supportable_order()
        if logging:
            logging.info("Adding unit %s with description %s" % (u.id, desc))
        supportable_units.append({
            'id': u.id,
            'description': desc
        })

    response_data = {'units': supportable_units}
    if logging:
        logging.info("Returning response: %s" % response_data)
    
    return HttpResponse(simplejson.dumps(response_data), mimetype='application/json')
