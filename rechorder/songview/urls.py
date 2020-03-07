from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^songs/$', views.songs, name='songs'),
    url(r'^songs/(?P<song_id>[0-9]+)$', views.song, name='song'),

]