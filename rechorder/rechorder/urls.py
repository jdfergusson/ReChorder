from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^song/$', views.songs, name='songs'),
    url(r'^song/(?P<song_id>[0-9]+)$', views.song, name='song'),
    url(r'^song/(?P<song_id>[0-9]+)/update$', views.song_update, name='song.update'),
    url(r'^song/(?P<song_id>[0-9]+)/delete$', views.song_delete, name='song.delete'),
    url(r'^song/(?P<song_id>[0-9]+)/print$', views.song_print, name='song.print'),
    url(r'^song/(?P<song_id>[0-9]+)/xml', views.song_xml, name='song.xml'),
    url(r'^song/create', views.song_create, name='song.create'),
    url(r'^song/transpose$', views.song_transpose, name='song.transpose'),
    url(r'^song/downloadxml$', views.download_xml, name='songs.download_xml'),
    url(r'^set/$', views.sets, name='sets'),
    url(r'^set/mine$', views.sets_mine, name='sets_mine'),
    url(r'^set/others$', views.sets_others, name='sets_others'),
    url(r'^set/new$', views.set_new, name='set.new'),
    url(r'^set/(?P<set_id>[0-9]+)$', views.set, name='set'),
    url(r'^set/(?P<set_id>[0-9]+)/addsong$', views.set_add_song, name='set.add_song'),
    url(r'^set/(?P<set_id>[0-9]+)/duplicate', views.set_duplicate, name='set.duplicate'),
    url(r'^set/(?P<set_id>[0-9]+)/update$', views.set_update, name='set.update'),
    url(r'^set/(?P<set_id>[0-9]+)/delete$', views.set_delete, name='set.delete'),
    url(r'^set/(?P<set_id>[0-9]+)/clear$', views.set_clear, name='set.clear'),
    url(r'^set/(?P<set_id>[0-9]+)/rename$', views.set_rename, name='set.rename'),
    url(r'^set/(?P<set_id>[0-9]+)/print$', views.set_print, name='set.print'),
    url(r'^set/(?P<set_id>[0-9]+)/song/(?P<song_index>[0-9]+)$', views.set_show_song, name='set.song'),
    url(r'^beaming/toggle', views.beaming_toggle, name='beaming.toggle'),
    url(r'^beaming/status', views.beaming_status, name='beaming.status'),
    url(r'^slave/$', views.get_beams, name='slave'),
    url(r'^slave/(?P<beam_id>[0-9]+)$', views.slave_to_master, name='slave_to'),
    url(r'^slave/(?P<beam_id>[0-9]+)/token$', views.slave_get_update_token, name='slave_token'),
    url(r'^settings$', views.settings, name='settings'),
    url(r'^settings/set$', views.settings_set, name='settings.set'),

    # These aren't so user facing...
    url(r'^upload$', views.upload, name='_upload'),
    url(r'^set/deleteallold$', views.set_delete_all_old, name='set._deleteallold'),
    url(r'^download', views.download, name='_download'),
]