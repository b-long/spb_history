from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()
from viewhistory.views import index, recent_builds, jobs, job, jid, overall_build_status

urlpatterns = [
    # Examples:
    # url(r'^$', 'spb_history.views.home', name='home'),
    # url(r'^spb_history/', include('spb_history.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', admin.site.urls),
    url(r'^$', index, name='index'),
    url(r'^recent_builds', recent_builds, name='recent_builds'),
    url(r'^jobs/(?P<package_id>\d+)/$', jobs, name='jobs'),
    url(r'^job/(?P<job_id>\d+)/$', job, name='job'),
    url(r'^jid/(?P<jid>.+)/$', jid, name='jid'),
    url(r'^overall_build_status/(?P<job_id>\d+)/$', overall_build_status, name='overall_build_status')
]

urlpatterns += staticfiles_urlpatterns()
