from django.conf.urls.defaults import *
from django.conf import settings
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.views.decorators.cache import cache_page
from django.views.generic.simple import direct_to_template
from django.views.static import serve
import os
import logging
import pinax

from django.contrib import admin
admin.autodiscover()

#from account.openid_consumer import PinaxConsumer
from waitinglist.forms import WaitingListEntryForm

handler500 = "pinax.views.server_error"

# Set up logging
logger = logging.getLogger(__name__)

def debug_serve(request, path, document_root):
    logger.info("Requested path: %s", path)
    logger.info("Document root: %s", document_root)
    logger.info("Full path: %s", os.path.join(document_root, path))
    logger.info("File exists: %s", os.path.exists(os.path.join(document_root, path)))
    logger.info("Directory exists: %s", os.path.exists(document_root))
    logger.info("Directory contents: %s", os.listdir(document_root) if os.path.exists(document_root) else "Directory not found")
    return serve(request, path, document_root)

# @@@ turn into template tag
#def homepage(request):
#    if request.method == "POST":
#        form = WaitingListEntryForm(request.POST)
#        if form.is_valid():
#            form.save()
#            return HttpResponseRedirect(reverse("waitinglist_sucess"))
#    else:
#        form = WaitingListEntryForm()
#    return direct_to_template(request, "homepage.html", {
#        "form": form,
#    })


if settings.ACCOUNT_OPEN_SIGNUP:
    signup_view = "account.views.signup"
else:
    signup_view = "signup_codes.views.signup"


urlpatterns = patterns('',
    # Static file serving patterns - moved outside DEBUG block
    (r'^site_media/static/machiavelli/css/game\.css$', debug_serve, {'path': 'game.css', 'document_root': os.path.join(settings.PROJECT_ROOT, 'machiavelli', 'media', 'machiavelli', 'css')}),
    (r'^site_media/static/machiavelli/css/(?P<path>.*)$', debug_serve, {'document_root': os.path.join(settings.PROJECT_ROOT, 'machiavelli', 'media', 'machiavelli', 'css')}),
    (r'^site_media/static/machiavelli/img/(?P<path>.*)$', debug_serve, {'document_root': os.path.join(settings.PROJECT_ROOT, 'machiavelli', 'media', 'machiavelli', 'img')}),
    (r'^site_media/static/machiavelli/(?P<path>.*)$', debug_serve, {'document_root': os.path.join(settings.PROJECT_ROOT, 'machiavelli', 'media', 'machiavelli')}),
    (r'^site_media/static/pinax/(?P<path>.*)$', debug_serve, {'document_root': os.path.join(pinax.__path__[0], 'media', 'default', 'pinax')}),
    (r'^site_media/static/uni_form/(?P<path>.*)$', debug_serve, {'document_root': os.path.join(pinax.__path__[0], '..', 'uni_form', 'media', 'uni_form')}),
    (r'^site_media/static/img/(?P<path>.*)$', debug_serve, {'document_root': os.path.join(settings.PROJECT_ROOT, 'media', 'images')}),
    (r'^site_media/static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    (r'^site_media/media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    
    url(r'^$', 'machiavelli.views.summary', name='home'),
    url(r'^robots\.txt$', direct_to_template, {"template": "robots.txt", "mimetype": "text/plain"}),
    url(r'^success/$', direct_to_template, {"template": "waitinglist/success.html"}, name="waitinglist_sucess"),
    
    url(r'^admin/invite_user/$', 'signup_codes.views.admin_invite_user', name="admin_invite_user"),
    url(r'^account/signup/$', signup_view, name="acct_signup"),
    
    (r'^account/', include('account.urls')),
    #(r'^openid/(.*)', PinaxConsumer()),
    #(r'^profiles/', include('basic_profiles.urls')),
    (r'^notices/', include('notification.urls')),
    #(r'^announcements/', include('announcements.urls')),
    
    (r'^admin/(.*)', admin.site.root),
        
    ## machiavelli urls
    (r'^machiavelli/', include('machiavelli.urls')),
    (r'^profiles/', include('condottieri_profiles.urls')),
    
    ## avatar urls
    (r'^avatar/', include('avatar.urls')),
    ## django-messages
    (r'^mail/', include('condottieri_messages.urls')),
    (r'^help/', include('condottieri_help.urls')),
)
