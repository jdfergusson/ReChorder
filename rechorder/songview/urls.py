from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^songs/$', views.songs, name='songs'),
    url(r'^songs/(?P<song_id>[0-9]+)$', views.song, name='song'),
    url(r'^service/addsong/(?P<song_id>[0-9]+)$', views.service_add_song, name='service.add_song'),
    url(r'^service/$', views.service, name='service'),
    url(r'^service/clear/$', views.service_clear, name='service.clear'),
    url(r'^service/song/(?P<song_index>[0-9]+)$', views.service_show_song, name='service.song'),
]