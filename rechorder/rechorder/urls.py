from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^$', views.index, name='index'),
    re_path(r'^song/$', views.songs, name='songs'),
    re_path(r'^song/(?P<song_id>[0-9]+)$', views.song, name='song'),
    re_path(r'^song/(?P<song_id>[0-9]+)/update$', views.song_update, name='song.update'),
    re_path(r'^song/(?P<song_id>[0-9]+)/delete$', views.song_delete, name='song.delete'),
    re_path(r'^song/(?P<song_id>[0-9]+)/print$', views.song_print, name='song.print'),
    re_path(r'^song/(?P<song_id>[0-9]+)/xml', views.song_xml, name='song.xml'),
    re_path(r'^song/(?P<song_id>[0-9]+)/verse_order_errors$', views.song_get_verse_order_errors, name='song.verse_order_errors'),
    re_path(r'^song/create', views.song_create, name='song.create'),
    re_path(r'^song/transpose$', views.song_transpose, name='song.transpose'),
    re_path(r'^song/downloadxml$', views.download_xml, name='songs.download_xml'),
    re_path(r'^set/$', views.sets, name='sets'),
    re_path(r'^set/mine$', views.sets_mine, name='sets_mine'),
    re_path(r'^set/others$', views.sets_others, name='sets_others'),
    re_path(r'^set/new$', views.set_new, name='set.new'),
    re_path(r'^set/(?P<set_id>[0-9]+)$', views.set, name='set'),
    re_path(r'^set/(?P<set_id>[0-9]+)/addsong$', views.set_add_song, name='set.add_song'),
    re_path(r'^set/(?P<set_id>[0-9]+)/removesong$', views.set_remove_song, name='set.remove_song'),
    re_path(r'^set/(?P<set_id>[0-9]+)/duplicate', views.set_duplicate, name='set.duplicate'),
    re_path(r'^set/(?P<set_id>[0-9]+)/update$', views.set_update, name='set.update'),
    re_path(r'^set/(?P<set_id>[0-9]+)/delete$', views.set_delete, name='set.delete'),
    re_path(r'^set/(?P<set_id>[0-9]+)/clear$', views.set_clear, name='set.clear'),
    re_path(r'^set/(?P<set_id>[0-9]+)/rename$', views.set_rename, name='set.rename'),
    re_path(r'^set/(?P<set_id>[0-9]+)/print$', views.set_print, name='set.print'),
    re_path(r'^set/(?P<set_id>[0-9]+)/song/(?P<song_index>[0-9]+)$', views.set_show_song, name='set.song'),
    re_path(r'^beaming/toggle', views.beaming_toggle, name='beaming.toggle'),
    re_path(r'^beaming/status', views.beaming_status, name='beaming.status'),
    re_path(r'^slave/$', views.get_beams, name='slave'),
    re_path(r'^slave/(?P<beam_id>[0-9]+)$', views.slave_to_master, name='slave_to'),
    re_path(r'^slave/(?P<beam_id>[0-9]+)/token$', views.slave_get_update_token, name='slave_token'),
    re_path(r'^settings$', views.settings, name='settings'),
    re_path(r'^settings/set$', views.settings_set, name='settings.set'),

    # These aren't so user facing...
    re_path(r'^upload$', views.upload, name='_upload'),
    re_path(r'^set/deleteallold$', views.set_delete_all_old, name='set._deleteallold'),
    re_path(r'^download', views.download, name='_download'),
]
