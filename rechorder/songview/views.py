from django.http import HttpResponseNotFound, JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
)
from django.template.loader import render_to_string

import json

from songview.music_handler.song import Song as MhSong
from songview.music_handler.interpret import KEYS


from .models import Song, Set


def _get_key_dict_key(song_id, set_id=-1):
    return "{}:{}".format(set_id, song_id)


def _get_song_key_index(request, song_id, fallback, set_id=-1):
    key_dict_key = _get_key_dict_key(song_id, set_id)
    return request.session.get('keys', {}).get(key_dict_key, fallback)


def _get_or_create_my_set(request):
    set = None
    set_id = request.session.get('my_set_id')

    if set_id is not None:
        try:
            set = Set.objects.get(pk=set_id)
        except ObjectDoesNotExist:
            set = None

    if set is None:
        set = Set()
        set.song_list = []
        set.save()
        request.session['my_set_id'] = set.pk
        request.session.modified = True
    return set


###########################
# VIEWS
###########################

def index(request):
    return render(request, 'songview/index.html')


def set_add_song(request, song_id):
    song = Song.objects.get(pk=song_id)

    set = _get_or_create_my_set(request)

    song_in_set = {
        'id': song_id,
        'key_index': _get_song_key_index(request, song.pk, MhSong(song.raw).original_key.index),
    }

    if request.GET.get('golive'):
        if set.beamed_song_index is None:
            song_in_set_index = len(set.song_list)
        else:
            song_in_set_index = set.beamed_song_index + 1

        set.song_list.insert(song_in_set_index, song_in_set)
        set.save()

        return redirect('set.song', song_index=song_in_set_index)
    else:
        set.song_list.append(song_in_set)
        set.save()

        return render(request, 'songview/set_added_song.html', {'song': song_in_set})


def set_clear(request):
    set = _get_or_create_my_set(request)
    set.song_list = []
    set.beamed_song_index = -1
    set.save()
    return JsonResponse({'result': True})


def set(request):
    set = _get_or_create_my_set(request)
    set_songs = []

    for song in set.song_list:
        s = Song.objects.get(pk=song['id'])
        set_song = {
            'id': s.pk,
            'key_index': song['key_index'],
            'title': s.title,
        }
        set_songs.append(set_song)

    return render(request, 'songview/set.html', {
        'set_songs': set_songs,
        'keys': KEYS,
    })


def set_update(request):
    set = _get_or_create_my_set(request)
    set.song_list = json.loads(request.POST.get('new_set'))
    set.save()
    return JsonResponse({'result': True})


def set_show_song(request, song_index):
    set = _get_or_create_my_set(request)

    try:
        # We'll never get negative numbers if the URL doesn't allow it
        song_index = int(song_index)
        song_in_set = set.song_list[song_index]
    except (ValueError, IndexError):
        return HttpResponseNotFound('<h1>Error: Page not found</h1>')

    song_database_object = Song.objects.get(pk=song_in_set['id'])

    # Set service view in database
    set.beamed_song_index = song_index
    set.save()

    song = MhSong(song_database_object.raw)

    key_index = _get_song_key_index(
        request,
        song_in_set['id'],
        fallback=song_in_set['key_index'],
        set_id=set.pk,
    )
    song.transpose(key_index)

    context = {
        'song': song,
        'song_id': song_in_set['id'],
        'am_i_master': True,
        'current_index': song_index,
        'max_index': len(set.song_list) - 1,
        'set_id': set.pk,
        'keys': KEYS,
    }
    return render(request, 'songview/song_in_set.html', context)


def get_beam_masters(request):
    context = {
        # Will get all sets that have a beamed song index
        'beam_masters': Set.objects.filter(beamed_song_index__gte=0)
    }
    return render(request, 'songview/beam_masters.html', context)


def slave_to_master(request, set_id):
    set = get_object_or_404(Set, pk=set_id)

    context_base = {
        'set_id': set_id,
        'keys': KEYS,
        'am_i_master': False,
    }

    if set.beamed_song_index is not None and \
            0 <= set.beamed_song_index < len(set.song_list):
        song_in_set = set.song_list[set.beamed_song_index]
        db_song = get_object_or_404(Song, pk=song_in_set['id'])
        song = MhSong(db_song.raw)

        key_index = _get_song_key_index(
            request,
            db_song.pk,
            fallback=song_in_set['key_index'],
            set_id=set_id
        )
        song.transpose(key_index)

        context = {
            **context_base,
            'song': song,
            'song_id': db_song.pk,
            'update_key': set.has_changed_count,
        }
    else:
        context = {
            **context_base,
            'song': None,
            'song_id': None,
            'update_key': -1,
        }

    return render(request, 'songview/song_in_set.html', context)


def slave_get_update_key(request, set_id):
    set = get_object_or_404(Set, pk=set_id)
    return JsonResponse({'update_key': set.has_changed_count})


def song_transpose(request):
    # These may raise an exception but that's fine - the data is invalid anyway
    target_key_index = int(request.GET['target_key_index'])
    song_id = int(request.GET['song_id'])
    db_song = get_object_or_404(Song, pk=song_id)
    master_id = int(request.GET.get('master_id', -1))

    dict_key = _get_key_dict_key(song_id, master_id)

    users_keys = request.session.get('keys')
    if users_keys is None:
        users_keys = request.session['keys'] = {}

    if 0 <= target_key_index < 12:
        users_keys[dict_key] = target_key_index
    else:
        try:
            users_keys.pop(dict_key)
        except KeyError:
            pass
    request.session.modified = True

    song = MhSong(db_song.raw)
    key = _get_song_key_index(request, song_id, song.original_key, master_id)
    song.transpose(key)

    json_data = {
        'song_html': render_to_string('songview/_print_song.html', {'song': song}),
        'key_index': song.key.index,
    }
    return JsonResponse(json_data)


def songs(request):
    songs = Song.objects.all()
    return render(request, 'songview/songs.html', {'songs': songs})


def song(request, song_id):
    song = MhSong(Song.objects.get(pk=song_id).raw)

    # This gets the user's personal list of keys, or creates it if it doesn't exist
    users_keys = request.session.get('keys')
    if users_keys is None:
        users_keys = request.session['keys'] = {}

    key_dict_key = _get_key_dict_key(song_id)

    # This is for if we've had a request to change the key
    target_key = request.GET.get('target_key')
    if target_key is not None:
        users_keys[key_dict_key] = target_key
    request.session.modified = True

    key = users_keys.get(key_dict_key, song.original_key.index)
    song.transpose(key)

    context = {
        'song': song,
        'keys': KEYS,
        'song_id': song_id
    }
    return render(request, 'songview/song.html', context)
