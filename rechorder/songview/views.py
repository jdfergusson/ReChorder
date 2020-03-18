from django.shortcuts import render, redirect
from django.http import HttpResponseNotFound
from django.urls import reverse

from songview.music_handler.song import Song as MhSong
from songview.music_handler.interpret import KEYS


from .models import Song

def _get_or_create_service(request):
    d = request.session.get('service')
    if d is None:
        request.session['service'] = {
            'songs': [],
        }

    return request.session['service']


def _get_song_key_index(request, song):
    return request.session.get('keys', {}).get(str(song.pk), MhSong(song.raw).original_key.index)


def service_add_song(request, song_id):
    song = Song.objects.get(pk=song_id)

    service = _get_or_create_service(request)

    song_in_service = {
        'id': song_id,
        'key_index': _get_song_key_index(request, song),
    }

    service['songs'].append(song_in_service)
    song_in_service['title'] = song.title

    request.session.modified = True
    return render(request, 'songview/service_added_song.html', {'song': song_in_service})


def service_clear(request):
    service = _get_or_create_service(request)
    service['songs'] = []
    request.session.modified = True

    return redirect(reverse('service'), permanent=True)


def service(request):
    service = _get_or_create_service(request)
    service_songs = []
    print(service)

    for song in service['songs']:
        s = Song.objects.get(pk=song['id'])
        service_song = {
            'id': s.pk,
            'key_index': song['key_index'],
            'title': s.title,
        }
        service_songs.append(service_song)

    return render(request, 'songview/service.html', {'service_songs': service_songs})


def service_show_song(request, song_index):
    service = _get_or_create_service(request)
    try:
        song_index = int(song_index)
        song_in_service = service['songs'][song_index]
    except (ValueError, IndexError):
        return HttpResponseNotFound('<h1>Error: Page not found</h1>')

    song = MhSong(Song.objects.get(pk=song_in_service['id']).raw)

    song.transpose(song_in_service['key_index'])

    context = {
        'song': song,
        'song_id': song_in_service['id'],
        'current_index': song_index,
        'max_index': len(service['songs']) - 1,
    }
    return render(request, 'songview/service_song.html', context)


def songs(request):
    songs = Song.objects.all()
    return render(request, 'songview/songs.html', {'songs': songs})


def song(request, song_id):
    song = MhSong(Song.objects.get(pk=song_id).raw)

    # This gets the user's personal list of keys, or creates it if it doesn't exist
    keys = request.session.get('keys')
    if keys is None:
        keys = request.session['keys'] = {}

    # This is for if we've had a request to change the key
    target_key = request.GET.get('target_key')
    if target_key is not None:
        keys[song_id] = target_key
    request.session.modified = True

    key = keys.get(song_id, song.original_key.index)
    song.transpose(key)

    context = {
        'song': song,
        'keys': KEYS,
        'song_id': song_id
    }
    return render(request, 'songview/song.html', context)
