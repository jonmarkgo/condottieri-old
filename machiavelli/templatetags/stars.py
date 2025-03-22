from math import ceil

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

from condottieri_profiles.models import CondottieriProfile

register = template.Library()

@register.filter
def karma_stars(value):
	""" Integer between 0 and 10 to represent the average karma with stars """
	highest = settings.KARMA_MAXIMUM
	if highest == 0:
		return mark_safe("<img src=\"%smachiavelli/img/0-blue.png\" alt=\"0 stars\" />" % settings.STATIC_URL)
	stars = int(ceil(10. * value / highest))
	img = "<img src=\"%(static_url)smachiavelli/img/%(stars)s-blue.png\" alt=\"%(stars)s stars\" />" % {
		'static_url': settings.STATIC_URL,
		'stars': stars,
		}
	return mark_safe(img)

@register.filter
def score_stars(value):
	""" Integer between 0 and 10 to represent the average score with stars """
	try:
		highest = CondottieriProfile.objects.order_by('-total_score')[0].total_score
		if highest == 0:
			return mark_safe("<img src=\"%smachiavelli/img/0-red.png\" alt=\"0 stars\" />" % settings.STATIC_URL)
		stars = int(ceil(10. * value / highest))
		img = "<img src=\"%(static_url)smachiavelli/img/%(stars)s-red.png\" alt=\"%(stars)s stars\" />" % {
			'static_url': settings.STATIC_URL,
			'stars': stars,
			}
		return mark_safe(img)
	except IndexError:
		return mark_safe("<img src=\"%smachiavelli/img/0-red.png\" alt=\"0 stars\" />" % settings.STATIC_URL)

