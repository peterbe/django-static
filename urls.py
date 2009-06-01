from django.conf.urls.defaults import *

from settings import MEDIA_ROOT


urlpatterns = patterns('',
    # Example:
    (r'^exampleapp/', include('exampleapp.urls')),

    # medi
    url(r'^images/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': MEDIA_ROOT + '/images'}),
    url(r'^css/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': MEDIA_ROOT + '/css'}),
    url(r'^javascript/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': MEDIA_ROOT + '/javascript'}),
                       
)
