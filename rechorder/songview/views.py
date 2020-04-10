from django.http import HttpResponseNotFound, HttpResponseBadRequest, JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
)
from django.template.loader import render_to_string

from copy import deepcopy

import json
import datetime

from songview.music_handler.interpret import KEYS, ABSOLUTE_LOOKUP, interpret_absolute_chord


from .models import Song, Set


def _get_selected_chord_shapes(request):
    if 'selected_chord_shapes' not in request.session:
        # Start with C, D, E and G
        request.session['selected_chord_shapes'] = [3, 5, 7, 10]
        request.session.modified = True
    return request.session['selected_chord_shapes']


def _get_or_create_my_set(request):
    set = None
    set_id = request.session.get('my_set_id')

    if set_id is not None:
        try:
            set = Set.objects.get(pk=set_id)
            set.check_list_integrity()
        except ObjectDoesNotExist:
            set = None

    if set is None:
        set = Set()
        set.song_list = []
        set.save()
        request.session['my_set_id'] = set.pk
        request.session.modified = True
    return set


def _get_sounding_key_index(request, song, sounding_key_index=None):
    song_key_data = request.session.get('keys', {}).get('{}'.format(song.pk), {})
    return int(song_key_data.get('sounding_key_index', song.original_key)
               if sounding_key_index is None else sounding_key_index)

def _get_song_key_index(request, song, set_id=-1, sounding_key_index=None):
    sounding_key_index = _get_sounding_key_index(request, song, sounding_key_index)
    song_key_data = request.session.get('keys', {}).get('{}'.format(song.pk), {})

    transpose_data = song_key_data.get('{}'.format(set_id))

    key_index = sounding_key_index
    capo_fret_number = 0

    if transpose_data is not None:
        # Defaults to sounding key mode
        transpose_type = transpose_data.get('adv-tran-opt', 'sk')
        if transpose_type == 'sk':
            key_index = sounding_key_index
        elif transpose_type == 'cs':
            print(transpose_data)
            if 'tran-cs-auto' not in transpose_data:
                key_index = int(transpose_data.get('chord-shape-index'))
            else:
                permitted_shape_keys = _get_selected_chord_shapes(request) or [sounding_key_index]
                deltas = [(i - sounding_key_index - 1) % 12 for i in permitted_shape_keys]
                key_index = permitted_shape_keys[deltas.index(max(deltas))]
            capo_fret_number = (sounding_key_index - key_index) % 12
        elif transpose_type == 'gc':
            capo_fret_number = int(transpose_data.get('capo-fret-number', 0))
            key_index = (sounding_key_index - capo_fret_number) % 12
        elif transpose_type == 'ti':
            delta = ABSOLUTE_LOOKUP['c'] - int(transpose_data.get('transposing-cnote', ABSOLUTE_LOOKUP['c']))
            key_index = sounding_key_index + delta
        elif transpose_type == 'abs':
            key_index = int(transpose_data.get('absolute-force-index', sounding_key_index))

    return key_index, capo_fret_number


def _get_key_details(request, song, set_id=-1, sounding_key_index=None):
    key_details = {}
    key_details['key_index'], key_details['capo_fret_number'] = _get_song_key_index(request, song, set_id)

    song_key_data = request.session.get('keys', {}).get('{}'.format(song.pk), {})
    key_details['sounding_key_index'] = _get_sounding_key_index(request, song, sounding_key_index)
    key_details['transpose_data'] = song_key_data.get('{}'.format(set_id), {
        # Default to displaying in sounding key
        'adv-tran-opt': 'sk'
    })
    return key_details


def _get_base_song_context_dict(request, song, set_id=-1, sounding_key_index=None):
    chord_shapes = []
    selected_chord_shapes = _get_selected_chord_shapes(request)
    for shape_index in selected_chord_shapes:
        chord_shapes.append({'index': shape_index, 'name': KEYS[shape_index]})
    # This will put a divider in the select box if we've got selected chord shapes
    if chord_shapes:
        chord_shapes.append({'index': -1, 'name': ''})
    for shape_index in range(12):
        if shape_index not in selected_chord_shapes:
            chord_shapes.append({'index': shape_index, 'name': KEYS[shape_index]})

    return {
        'keys': KEYS,
        'frets': [i for i in range(12)],
        'cnotes': [
            {'index': 1, 'name': 'Bb'},
            {'index': 6, 'name': 'Eb'},
            {'index': 7, 'name': 'F'},
        ],
        'chord_shapes': chord_shapes,
        'key_details': _get_key_details(request, song, set_id, sounding_key_index),
    }

###########################
# VIEWS
###########################

def index(request):
    return render(request, 'songview/index.html')


def set_add_song(request, song_id):
    song = Song.objects.get(pk=song_id)

    set = _get_or_create_my_set(request)

    # Get sounding key from current settings
    song_key_data = request.session.get('keys', {}).get('{}'.format(song.pk), {})
    sounding_key_index = int(song_key_data.get('sounding_key_index', song.original_key))

    song_in_set = {
        'id': song_id,
        'key_index': sounding_key_index,
    }

    # Copy current key settings to set settings
    if '-1' in song_key_data:
        song_key_data['{}'.format(set.id)] = deepcopy(song_key_data['-1'])
        request.session.modified = True

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
    return JsonResponse({'success': True})


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
        'set': set,
        'keys': KEYS,
    })


def set_update(request):
    set = _get_or_create_my_set(request)
    set.song_list = json.loads(request.POST.get('new_set'))
    set.save()
    return JsonResponse({'success': True})


def set_rename(request):
    set = _get_or_create_my_set(request)
    set.name = request.POST.get('name')[:200]
    set.save()
    return JsonResponse({'success': True, 'new_name': set.name})


def set_show_song(request, song_index):
    set = _get_or_create_my_set(request)

    try:
        # We'll never get negative numbers if the URL doesn't allow it
        song_index = int(song_index)
        song_in_set = set.song_list[song_index]
    except (ValueError, IndexError):
        return HttpResponseNotFound('<h1>Error: Page not found</h1>')

    song = Song.objects.get(pk=song_in_set['id'])

    # Set service view in database
    set.beamed_song_index = song_index
    set.save()

    key_index, capo_fret_number = _get_song_key_index(request, song, set.pk, song_in_set['key_index'])
    song.transpose(key_index)

    context = {
        'song': song,
        'am_i_master': True,
        'current_index': song_index,
        'max_index': len(set.song_list) - 1,
        'set_id': set.pk,
        **_get_base_song_context_dict(request, song, set.pk, song_in_set['key_index']),
    }
    return render(request, 'songview/song_in_set.html', context)


def get_beam_masters(request):
    update_time_cutoff = datetime.datetime.now() - datetime.timedelta(days=1)
    context = {
        # Will get all sets that have a beamed song index
        'sets': Set.objects.filter(
            beamed_song_index__isnull=False,
            last_updated__gte=update_time_cutoff,
        ).order_by('-last_updated'),
    }
    return render(request, 'songview/beam_masters.html', context)


def slave_to_master(request, set_id):
    set = get_object_or_404(Set, pk=set_id)

    context_base = {
        'set_id': set_id,
        'am_i_master': False,
        'capo_fret_number': 0,
    }

    if set.beamed_song_index is not None and \
            0 <= set.beamed_song_index < len(set.song_list):
        song_in_set = set.song_list[set.beamed_song_index]
        song = get_object_or_404(Song, pk=song_in_set['id'])

        key_index, capo_fret_number = _get_song_key_index(request, song, set_id, song_in_set['key_index'])
        song.transpose(key_index)

        context = {
            **context_base,
            'song': song,
            'update_token': set.has_changed_count,
            'capo_fret_number': capo_fret_number,
            **_get_base_song_context_dict(request, song, set_id, song_in_set['key_index']),
        }
    else:
        context = {
            **context_base,
            'song': None,
            'update_token': -1,
        }

    return render(request, 'songview/song_in_set.html', context)


def slave_get_update_token(request, set_id):
    set = get_object_or_404(Set, pk=set_id)
    return JsonResponse({'update_token': set.has_changed_count})


def song_edit(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    context = {
        'song': song,
        'keys': KEYS,
    }
    return render(request, 'songview/song_edit.html', context)


def song_change_data(request, song_id):
    song = get_object_or_404(Song, pk=song_id)

    title = request.POST.get('title')
    artist = request.POST.get('artist')
    original_key = request.POST.get('original_key')
    content = request.POST.get('content')

    if None not in (title, artist, original_key, content):
        song.title = title
        song.artist = artist
        song.original_key = original_key
        song.raw = content
        song.save()

        return JsonResponse({'success': True})
    return HttpResponseBadRequest('Invalid POST data')


def song_delete(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    song.delete()
    return JsonResponse({'success': True})


def song_create(request):
    if request.POST:
        song = Song(
            title=request.POST.get('title'),
            artist=request.POST.get('artist'),
            original_key=request.POST.get('original_key'),
            raw=request.POST.get('content')
        )
        song.save()
        return JsonResponse({
            'success': True,
            'new_song_url': song.get_absolute_url(),
        })

    else:
        return render(request, 'songview/song_create.html', {'keys': KEYS})


def song_transpose(request):
    transpose_data = json.loads(request.POST['transpose_data'])
    song_id = int(request.POST['song_id'])
    song = get_object_or_404(Song, pk=song_id)
    set_id = int(request.POST.get('set_id', -1))

    # Get the user's keys data for this song
    users_keys = request.session.get('keys')
    if users_keys is None:
        users_keys = request.session['keys'] = {}
    song_dict_key = '{}'.format(song_id)
    if song_dict_key not in users_keys:
        users_keys[song_dict_key] = {}
    users_key_song_data = users_keys[song_dict_key]

    # Sounding key index is static if we have a set ID, or dynamic (and thus in the form details)
    # if we're outside a set
    if set_id == -1:
        try:
            sounding_key_index = int(transpose_data.pop('sounding-key'))
        except (ValueError, KeyError):
            # Default to original key
            sounding_key_index = song.original_key
        users_key_song_data['sounding_key_index'] = sounding_key_index
    else:
        sounding_key_index = request.POST['sounding_key_index']

    # Save the key information
    users_key_song_data['{}'.format(set_id)] = transpose_data

    request.session.modified = True

    key_index, capo_fret_number = _get_song_key_index(request, song, set_id, sounding_key_index)
    song.transpose(key_index)

    json_data = {
        'song_html': render_to_string('songview/_print_song.html', {'song': song}),
        'key_details': _get_key_details(request, song, set_id),
    }
    return JsonResponse(json_data)


def songs(request):
    songs = Song.objects.order_by('title')
    context = {
        'songs': songs,
        'keys': KEYS,
    }
    return render(request, 'songview/songs.html', context)


def song(request, song_id):
    song = get_object_or_404(Song, pk=song_id)

    key_index, capo_fret_number = _get_song_key_index(request, song)
    song.transpose(key_index)

    context = {
        'song': song,
        **_get_base_song_context_dict(request, song),
    }
    return render(request, 'songview/song.html', context)


def settings_chord_shapes(request):
    if request.POST:
        request.session['selected_chord_shapes'] = \
            [int(i) for i in json.loads(request.POST.get('permitted_shapes', ''))]
        request.session.modified = True
        return JsonResponse({'success': True})
    else:
        context = {
            'selected_shapes': _get_selected_chord_shapes(request),
            'possible_shapes': [{'name': i, 'index': interpret_absolute_chord(i)[0]} for i in KEYS],
        }
        print(context)
        return render(request, 'songview/settings_chord_shapes.html', context)