from django.http import (
    HttpResponseNotFound,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.urls import reverse
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
import zipfile
import os

from rechorder.music_handler.interpret import KEYS, ABSOLUTE_LOOKUP, interpret_absolute_chord, song_from_onsong_text


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
        set.name = "My set"
        set.save()
        request.session['my_set_id'] = set.pk
        request.session.modified = True
    return set


def _get_header_links(request, **overrides):
    if 'last_visited_song' in request.session:
        songs_link = reverse('song', args=[request.session['last_visited_song']])
    else:
        songs_link = reverse('songs')

    if 'last_song_in_set' in request.session:
        set_link = reverse('set.song', args=[request.session['last_song_in_set']])
    else:
        set_link = reverse('set')

    links = {
        'header_link_back': '#',
        'header_link_songs': songs_link,
        'header_link_set': set_link,
        'header_link_receive': reverse('slave'),
        'header_link_settings': reverse('settings.chord_shapes')
    }

    for override in overrides:
        links[override] = overrides[override]

    return links


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
            key_index = int(transpose_data.get('chord-shape-index', '0'))
            capo_fret_number = (sounding_key_index - key_index) % 12
        elif transpose_type == 'acs':
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
    key_details['original_key_index'] = song.original_key
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
            {'index': 1, 'name': 'B\u266d'},
            {'index': 6, 'name': 'E\u266d'},
            {'index': 8, 'name': 'F'},
            {'index': 0, 'name': 'A'},
        ],
        'chord_shapes': chord_shapes,
        'key_details': _get_key_details(request, song, set_id, sounding_key_index),
    }


def _get_update_song_data(request, song, set_id=-1):
    return {
        'song_html': render_to_string('rechorder/_print_song.html', {'song': song}),
        'key_details': _get_key_details(request, song, set_id),
        'song_meta': {
            'title': song.title,
            'artist': song.artist,
        },
    }


###########################
# VIEWS
###########################

def index(request):
    return redirect(reverse('songs'))


def set_add_song(request):

    song = Song.objects.get(pk=int(request.POST.get('song_id')))

    set = _get_or_create_my_set(request)

    # Get sounding key from current settings
    song_key_data = request.session.get('keys', {}).get('{}'.format(song.pk), {})
    sounding_key_index = int(song_key_data.get('sounding_key_index', song.original_key))

    song_in_set = {
        'id': song.pk,
        'key_index': sounding_key_index,
    }

    # Copy current key settings to set settings
    if '-1' in song_key_data:
        song_key_data['{}'.format(set.id)] = deepcopy(song_key_data['-1'])
        request.session.modified = True

    if request.POST.get('go_live', False):
        if set.beamed_song_index is None:
            song_in_set_index = len(set.song_list)
        else:
            song_in_set_index = set.beamed_song_index + 1

        set.song_list.insert(song_in_set_index, song_in_set)
        set.save()

        redirect_url = reverse('set.song', args=[song_in_set_index])
        return JsonResponse({'success': True, 'redirect': redirect_url})
    else:
        set.song_list.append(song_in_set)
        set.save()
        return JsonResponse({'success': True})


def set_clear(request):
    set = _get_or_create_my_set(request)
    set.song_list = []
    set.beamed_song_index = -1
    set.save()
    return JsonResponse({'success': True})


def set(request):
    set = _get_or_create_my_set(request)
    set_songs = []

    try:
        request.session.pop('last_song_in_set')
        request.session.modified = True
    except KeyError:
        pass

    for song in set.song_list:
        s = Song.objects.get(pk=song['id'])
        set_song = {
            'id': s.pk,
            'key_index': song['key_index'],
            'title': s.title,
        }
        set_songs.append(set_song)

    return render(request, 'rechorder/set.html', {
        'set_songs': set_songs,
        'set': set,
        'keys': KEYS,
        **_get_header_links(request),
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

    request.session['last_song_in_set'] = song_index
    request.session.modified = True

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
        'set_id': set.pk,
        'set_length': len(set.song_list),
        'max_index': len(set.song_list) - 1,
        **_get_base_song_context_dict(request, song, set.pk, song_in_set['key_index']),
        **_get_header_links(
            request,
            header_link_back=reverse('set'),
            header_link_set=reverse('set'),
            header_link_songs=reverse('songs')),
    }
    return render(request, 'rechorder/song_in_set.html', context)


def set_print(request, set_id):
    set = get_object_or_404(Set, pk=set_id)
    set.check_list_integrity()

    songs = []
    for song_in_set in set.song_list:
        song = Song.objects.get(pk=song_in_set['id'])
        request.GET.get('no_personal_keys', False)
        if request.GET.get('no_personal_keys', False):
            key_index =  song_in_set['key_index']
            capo_fret_number = 0
        else:
            key_index, capo_fret_number = _get_song_key_index(request, song, set.pk, song_in_set['key_index'])

        song.transpose(key_index)

        songs.append({
            'song': song,
            'sounding_key_index': song_in_set['key_index'],
            'key_index': key_index,
            'capo_fret_number': capo_fret_number,
        })

    context = {
        'songs': songs,
        'set_id': set.pk,
    }

    if request.GET.get('no_personal_keys', False):
       context['no_personal_keys'] = True

    return render(request, 'rechorder/print_set.html', context)


def get_beam_masters(request):
    update_time_cutoff = datetime.datetime.now() - datetime.timedelta(days=1)
    context = {
        # Will get all sets that have a beamed song index
        'sets': Set.objects.filter(
            beamed_song_index__isnull=False,
            last_updated__gte=update_time_cutoff,
        ).order_by('-last_updated'),
        **_get_header_links(request),
    }
    return render(request, 'rechorder/beam_masters.html', context)


def slave_to_master(request, set_id):
    set = get_object_or_404(Set, pk=set_id)

    context_base = {
        'set_id': set_id,
        'am_i_master': False,
        'capo_fret_number': 0,
        **_get_header_links(request, header_link_back=reverse('slave')),
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
            'set_length': len(set.song_list),
            'current_index': set.beamed_song_index,
            **_get_base_song_context_dict(request, song, set_id, song_in_set['key_index']),
        }
    else:
        context = {
            **context_base,
            'song': None,
            'update_token': -1,
        }

    return render(request, 'rechorder/song_in_set.html', context)


def slave_get_update_token(request, set_id):
    set = get_object_or_404(Set, pk=set_id)
    return JsonResponse({'update_token': set.has_changed_count})


def song_update(request, song_id):
    song = get_object_or_404(Song, pk=song_id)

    title = request.POST.get('title')
    artist = request.POST.get('artist')
    original_key = int(request.POST.get('original_key'))
    content = request.POST.get('content')

    if None not in (title, artist, original_key, content):
        song.title = title
        song.artist = artist
        song.original_key = original_key
        song.raw = content
        song.save()

        return JsonResponse(_get_update_song_data(request, song))
    return HttpResponseBadRequest('Invalid POST data')


def song_delete(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    song.delete()
    return JsonResponse({'success': True})


def song_print(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    key_index, capo_fret_number = _get_song_key_index(request, song)
    song.transpose(key_index)

    songs = [{
        'song': song,
        'sounding_key_index': (key_index + capo_fret_number) % 12,
        'key_index': key_index,
        'capo_fret_number': capo_fret_number,
    }]

    context = {
        'songs': songs,
    }

    if request.GET.get('no_personal_keys', False):
       context['no_personal_keys'] = True

    return render(request, 'rechorder/print_set.html', context)

    return JsonResponse({'success': True})


def song_create(request):
    if request.method == 'POST':
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
        context = {
            'keys': KEYS,
            **_get_header_links(request, header_link_back=reverse('songs')),
        }
        return render(request, 'rechorder/song_create.html', context)


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

    return JsonResponse(_get_update_song_data(request, song, set_id))


def songs(request):
    songs = Song.objects.order_by('title')

    try:
        request.session.pop('last_visited_song')
        request.session.modified = True
    except KeyError:
        pass

    context = {
        'songs': songs,
        'keys': KEYS,
        **_get_header_links(request, header_link_songs=reverse('songs'))
    }
    return render(request, 'rechorder/songs.html', context)


def song(request, song_id):
    song = get_object_or_404(Song, pk=song_id)

    request.session['last_visited_song'] = song_id
    request.session.modified = True

    key_index, capo_fret_number = _get_song_key_index(request, song)
    song.transpose(key_index)

    context = {
        'song': song,
        **_get_base_song_context_dict(request, song),
        **_get_header_links(
            request,
            header_link_songs=reverse('songs'),
            header_link_back='{}#song{}'.format(reverse('songs'), song.id),
        ),
    }
    return render(request, 'rechorder/song.html', context)


def settings_chord_shapes(request):
    if request.method == 'POST':
        request.session['selected_chord_shapes'] = \
            [int(i) for i in json.loads(request.POST.get('permitted_shapes', ''))]
        request.session.modified = True
        return JsonResponse({'success': True})
    else:
        context = {
            'selected_shapes': _get_selected_chord_shapes(request),
            'possible_shapes': [{'name': KEYS[i], 'index': i} for i in range(12)],
            **_get_header_links(request),
        }
        return render(request, 'rechorder/settings_chord_shapes.html', context)


def upload(request):
    if request.method == 'POST':
        with zipfile.ZipFile(request.FILES['zipfile']) as zip_file:
            file_names = zip_file.namelist()
            for name in file_names:
                if os.path.splitext(name)[1].lower() != '.onsong':
                    continue

                try:
                    with zip_file.open(name, 'r') as f:
                        data = f.read().decode('utf-8', errors='ignore')

                    song_data = song_from_onsong_text(data)
                    if song_data is not None:
                        song = Song(**song_data)
                        song.save()
                        print('Added song "{}"'.format(song.title))
                except Exception as e:
                    print('{} failed:'.format(name))
                    print(e)
                    continue

        return render(request, 'rechorder/upload.html')
    else:
        return render(request, 'rechorder/upload.html')
