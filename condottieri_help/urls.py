from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.views.decorators.cache import cache_page
from django.conf import settings
from django.utils.functional import lazy

def get_extra_context():
	return {
		'contact_email': getattr(settings, 'CONTACT_EMAIL', ''),
		'forum_url': '/forum',
	}

urlpatterns = patterns('condottieri_help.views',
	url(r'^$', direct_to_template, {'template': 'condottieri_help/index.html', 'extra_context': lazy(get_extra_context, dict)()}, name='help-index'),
	url(r'^contribute$', direct_to_template, {'template': 'condottieri_help/contribute.html', 'extra_context': lazy(get_extra_context, dict)()}, name='help-contribute'),
)

