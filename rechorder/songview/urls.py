from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^song/$', views.songs, name='songs'),
    url(r'^song/(?P<song_id>[0-9]+)$', views.song, name='song'),
    url(r'^song/transpose$', views.song_transpose, name='song_transpose'),
    url(r'^set/addsong/(?P<song_id>[0-9]+)$', views.set_add_song, name='set.add_song'),
    url(r'^set/$', views.set, name='set'),
    url(r'^set/clear/$', views.set_clear, name='set.clear'),
    url(r'^set/song/(?P<song_index>[0-9]+)$', views.set_show_song, name='set.song'),
    url(r'^slave/$', views.get_beam_masters, name='slave'),
    url(r'^slave/(?P<master_id>[0-9]+)$', views.slave_to_master, name='slave_to'),
    url(r'^slave/(?P<master_id>[0-9]+)/key$', views.slave_get_update_key, name='slave_key'),
]