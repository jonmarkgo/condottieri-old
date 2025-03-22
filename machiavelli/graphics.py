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

""" This module defines functions to generate the map. """

from PIL import Image, ImageDraw
import os

from django.conf import settings

BASEDIR=os.path.join(settings.PROJECT_ROOT, 'machiavelli/media/machiavelli/tokens')
BASEMAP='base-map.png'
if settings.DEBUG:
	MAPSDIR = os.path.join(settings.MEDIA_ROOT, 'machiavelli/maps')
else:
	MAPSDIR = os.path.join(settings.MEDIA_ROOT, 'machiavelli/maps')

def make_map(game):
	""" Generates the map for a game. It opens the base map and adds the control markers,
	flags and units. The map is saved with a filename based on the game's primary key.
	"""
	from machiavelli.models import Unit  # Import here to avoid circular import

	## open the base map
	base = Image.open(os.path.join(BASEDIR, BASEMAP))
	draw = ImageDraw.Draw(base)

	## draw control markers
	for player in game.player_set.all():
		if player.country:  # Only process players with a country assigned
			## draw control markers
			for ga in game.gamearea_set.filter(player=player):
				marker = Image.open("%s/control-%s.png" % (BASEDIR, player.country.css_class))
				base.paste(marker, (ga.board_area.controltoken.x, ga.board_area.controltoken.y), marker)
			## draw units
			for unit in Unit.objects.filter(player=player):
				if unit.type == 'G':
					garrison = Image.open("%s/G-%s.png" % (BASEDIR, player.country.css_class))
					base.paste(garrison, (unit.area.board_area.gtoken.x, unit.area.board_area.gtoken.y), garrison)
				elif unit.type == 'A':
					army = Image.open("%s/A-%s.png" % (BASEDIR, player.country.css_class))
					base.paste(army, (unit.area.board_area.aftoken.x, unit.area.board_area.aftoken.y), army)
				elif unit.type == 'F':
					fleet = Image.open("%s/F-%s.png" % (BASEDIR, player.country.css_class))
					base.paste(fleet, (unit.area.board_area.aftoken.x, unit.area.board_area.aftoken.y), fleet)

	## save the map
	base.save(os.path.join(MAPSDIR, "map-%s.png" % game.id))
	## save the thumbnail
	thumb = base.copy()
	thumb.thumbnail((200, 200))
	thumb.save(os.path.join(MAPSDIR, "thumbnails/map-%s.png" % game.id))

def make_scenario_map(s):
	""" Makes the initial map for an scenario.
	"""
	base_map = Image.open(os.path.join(BASEDIR, BASEMAP))
	## if there are disabled areas, mark them
	try:
		marker = Image.open("%s/disabled.png" % BASEDIR)
		for d in  s.disabledarea_set.all():
			base_map.paste(marker, (d.area.aftoken.x, d.area.aftoken.y), marker)
	except IOError:
		pass
	## mark special city incomes
	try:
		marker = Image.open("%s/chest.png" % BASEDIR)
		for i in s.cityincome_set.all():
			base_map.paste(marker, (i.city.gtoken.x + 48, i.city.gtoken.y), marker)
	except IOError:
		pass
	##
	for c in s.get_countries():
		try:
			## paste control markers and flags
			controls = s.home_set.filter(country=c, is_home=True)
			marker = Image.open("%s/control-%s.png" % (BASEDIR, c.css_class))
			flag = Image.open("%s/flag-%s.png" % (BASEDIR, c.css_class))
			for h in controls:
				base_map.paste(marker, (h.area.controltoken.x, h.area.controltoken.y), marker)
				base_map.paste(flag, (h.area.controltoken.x, h.area.controltoken.y - 15), flag)
			## paste units
			army = Image.open("%s/A-%s.png" % (BASEDIR, c.css_class))
			fleet = Image.open("%s/F-%s.png" % (BASEDIR, c.css_class))
			garrison = Image.open("%s/G-%s.png" % (BASEDIR, c.css_class))
			for setup in c.setup_set.filter(scenario=s):
				if setup.unit_type == 'G':
					coords = (setup.area.gtoken.x, setup.area.gtoken.y)
					base_map.paste(garrison, coords, garrison)
				elif setup.unit_type == 'A':
					coords = (setup.area.aftoken.x, setup.area.aftoken.y)
					base_map.paste(army, coords, army)
				elif setup.unit_type == 'F':
					coords = (setup.area.aftoken.x, setup.area.aftoken.y)
					base_map.paste(fleet, coords, fleet)
				else:
					pass
		except IOError as e:
			print "Error loading images for country %s: %s" % (c.css_class, str(e))
			continue
	## paste autonomous garrisons
	try:
		garrison = Image.open("%s/G-autonomous.png" % BASEDIR)
		for g in s.setup_set.filter(country__isnull=True, unit_type='G'):
			coords = (g.area.gtoken.x, g.area.gtoken.y)
			base_map.paste(garrison, coords, garrison)
	except IOError:
		pass
	## save the map
	result = base_map #.resize((1250, 1780), Image.ANTIALIAS)
	filename = os.path.join(MAPSDIR, "scenario-%s.png" % s.pk)
	result.save(filename)
	make_thumb(filename, 187, 267, "thumbnails")
	make_thumb(filename, 625, 890, "625x890")
	return True

def make_thumb(fd, w, h, dirname):
	""" Make a thumbnail of the map image """
	size = w, h
	filename = os.path.split(fd)[1]
	outfile = os.path.join(MAPSDIR, dirname, filename)
	im = Image.open(fd)
	im.thumbnail(size, Image.ANTIALIAS)
	im.save(outfile, "PNG")
