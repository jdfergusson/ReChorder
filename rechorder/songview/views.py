from django.http import HttpResponseNotFound, JsonResponse
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from songview.music_handler.song import Song as MhSong
from songview.music_handler.interpret import KEYS


from .models import Song, BeamMaster

def _get_or_create_set(request):
    d = request.session.get('set')
    if d is None:
        request.session['set'] = {
            'songs': [],
        }

    return request.session['set']


def _get_song_key_index(request, song):
    return request.session.get('keys', {}).get(str(song.pk), MhSong(song.raw).original_key.index)


def _get_beam_master(request):
    bm = None
    bm_id = request.session.get('beam_master_my_id')

    if bm_id is not None:
        try:
            bm = BeamMaster.objects.get(pk=bm_id)
        except ObjectDoesNotExist:
            bm = None

    if bm is None:
        bm = BeamMaster()
        bm.save()
        request.session['beam_master_my_id'] = bm.pk
    return bm


###########################
# VIEWS
###########################

def index(request):
    return render(request, 'songview/index.html')


def set_add_song(request, song_id):
    song = Song.objects.get(pk=song_id)

    set = _get_or_create_set(request)

    song_in_set = {
        'id': song_id,
        'key_index': _get_song_key_index(request, song),
    }

    set['songs'].append(song_in_set)
    song_in_set['title'] = song.title

    request.session.modified = True
    return render(request, 'songview/set_added_song.html', {'song': song_in_set})


def set_clear(request):
    set = _get_or_create_set(request)
    set['songs'] = []
    request.session.modified = True

    return redirect(reverse('set'), permanent=True)


def set(request):
    set = _get_or_create_set(request)
    set_songs = []

    for song in set['songs']:
        s = Song.objects.get(pk=song['id'])
        set_song = {
            'id': s.pk,
            'key_index': song['key_index'],
            'title': s.title,
        }
        set_songs.append(set_song)

    return render(request, 'songview/set.html', {'set_songs': set_songs})


def set_show_song(request, song_index):
    set = _get_or_create_set(request)
    try:
        song_index = int(song_index)
        song_in_set = set['songs'][song_index]
    except (ValueError, IndexError):
        return HttpResponseNotFound('<h1>Error: Page not found</h1>')

    song_database_object = Song.objects.get(pk=song_in_set['id'])

    # Set service view in database
    beam = _get_beam_master(request)
    beam.current_song = song_database_object
    beam.current_key_index = song_in_set['key_index']
    beam.save()

    song = MhSong(song_database_object.raw)

    song.transpose(song_in_set['key_index'])

    context = {
        'song': song,
        'song_id': song_in_set['id'],
        'am_i_master': True,
        'current_index': song_index,
        'max_index': len(set['songs']) - 1,
    }
    return render(request, 'songview/song_in_set.html', context)


def get_beam_masters(request):
    context = {
        'beam_masters': BeamMaster.objects.all()
    }
    return render(request, 'songview/beam_masters.html', context)


def slave_to_master(request, master_id):
    master = get_object_or_404(BeamMaster, pk=master_id)

    if master.current_song:
        song = MhSong(master.current_song.raw)
        song.transpose(master.current_key_index)
        context = {
            'song': song,
            'song_id': master.current_song.pk,
            'am_i_master': False,
            'master_id': master_id,
            'update_key': master.has_changed_count,
        }
    else:
        context = {
            'song': None,
            'song_id': None,
            'am_i_master': False,
            'master_id': master_id,
            'update_key': -1,
        }

    return render(request, 'songview/song_in_set.html', context)


def slave_get_update_key(request, master_id):
    master = get_object_or_404(BeamMaster, pk=master_id)
    return JsonResponse({'update_key': master.has_changed_count})


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
