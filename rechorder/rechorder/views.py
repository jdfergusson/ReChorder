from django.http import (
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.urls import reverse
from django.core.paginator import Paginator
from django.core import serializers
from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
)
from django.template.loader import render_to_string

from copy import deepcopy

import datetime
import json
import os
import uuid
import zipfile

#TODO: Remove this
import inspect

from rechorder.music_handler.interpret import KEYS, ABSOLUTE_LOOKUP, interpret_absolute_chord, song_from_onsong_text


from .models import Song, Set, Beam


def _get_selected_chord_shapes(request):
    if 'selected_chord_shapes' not in request.session:
        # Start with C, D, E and G
        request.session['selected_chord_shapes'] = [3, 5, 7, 10]
        request.session.modified = True
    return request.session['selected_chord_shapes']


def _get_display_style(request):
    if request.session.get('chord_display_style') not in ('letters', 'numbers'):
        request.session['chord_display_style'] = 'letters'
        request.session.modified = True
    return request.session['chord_display_style']


def _get_current_set_id(request):
    set_id = request.session.get('current_set_id')
    return set_id


def _set_current_set(request, set):
    request.session['current_set_id'] = set.pk


def _clear_current_set(request):
    request.session['current_set_id'] = None


def _get_or_create_user_uuid(request):
    user_uuid = request.session.get('user_uuid')
    if user_uuid is None:
        user_uuid = str(uuid.uuid4())
        request.session['user_uuid'] = user_uuid
    return user_uuid


def _get_or_create_device_name(request):
    device_name = request.session.get('device_name')
    if device_name is None:
        device_name = 'Unnamed Device'
        request.session['device_name'] = device_name
    return device_name


def _get_header_links(request, **overrides):
    if 'last_visited_song' in request.session:
        songs_link = reverse('song', args=[request.session['last_visited_song']])
    else:
        songs_link = reverse('songs')

    current_set_id = _get_current_set_id(request)
    if current_set_id:
        if 'last_song_in_set' in request.session:
            set_link = reverse('set.song', args=[current_set_id, request.session['last_song_in_set']])
        else:
            set_link = reverse('set', args=[current_set_id])
    else:
        set_link = reverse('sets')

    links = {
        'header_link_back': '#',
        'header_link_songs': songs_link,
        'header_link_set': set_link,
        'header_link_receive': reverse('slave'),
        'header_link_settings': reverse('settings')
    }

    for override in overrides:
        links[override] = overrides[override]

    return links


def _get_sounding_key_index(request, song, set_pk=None, song_in_set=None):
    """
    Returns the index of the sounding key of the song as preferred by the user or chosen by the current set.
    If the user has not set a preference, set the sounding key to the original key of the song.
    """
    sounding_key_index = song.original_key
    try:
        if None not in (set_pk, song_in_set):
            set = Set.objects.get(pk=set_pk)
            sounding_key_index = set.song_list[song_in_set]['key_index']
        else:
            # set_pk and song_in_set should both be none
            song_key_data = _get_transpose_data(request, song.pk, None, None)
            sounding_key_index = song_key_data['sounding_key_index']
    except Exception:
        pass

    return sounding_key_index


def _get_transpose_data(request, song_pk, set_pk, song_in_set):
    song_key_data = request.session.get('keys', {}).get('{}'.format(song_pk), {})
    return song_key_data.get('{}.{}'.format(set_pk, song_in_set))


def _set_transpose_data(request, song_pk, set_pk, song_in_set, transpose_data):
    keys_dict = request.session.get('keys', {})
    song_key_data = keys_dict['{}'.format(song_pk)] = keys_dict.get('{}'.format(song_pk), {})
    song_key_data['{}.{}'.format(set_pk, song_in_set)] = deepcopy(transpose_data)
    request.session['keys'] = keys_dict
    request.session.modified = True


def _get_song_key_index(request, song, set_pk=None, song_in_set=None):
    sounding_key_index = _get_sounding_key_index(request, song, set_pk, song_in_set)

    # Get transpose data for the specific view we're looking at now
    transpose_data = _get_transpose_data(request, song.pk, set_pk, song_in_set)

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


def _get_key_details(request, song, set_pk=None, song_in_set=None):
    key_details = {}
    key_details['key_index'], key_details['capo_fret_number'] = \
        _get_song_key_index(request, song, set_pk, song_in_set)

    key_details['sounding_key_index'] = _get_sounding_key_index(request, song, set_pk, song_in_set)
    key_details['transpose_data'] = _get_transpose_data(request, song.pk, set_pk, song_in_set) or {
        # Default to displaying in sounding key
        'adv-tran-opt': 'sk'
    }
    key_details['original_key_index'] = song.original_key
    return key_details


def _get_base_song_context_dict(request, song, set_pk=None, song_in_set=None):
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

    current_set_id = _get_current_set_id(request)
    set = None
    set_is_editable = False
    if current_set_id is not None:
        try:
            set = Set.objects.get(pk=current_set_id)
            set_is_editable = set.owner == _get_or_create_user_uuid(request)
        except Set.DoesNotExist:
            pass

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
        'key_details': _get_key_details(request, song, set_pk, song_in_set),
        'current_set': set,
        'set_is_editable': set_is_editable,
    }


def _get_update_song_data(request, song, set_pk=None, song_in_set=None):
    return {
        'song_html': render_to_string('rechorder/_print_song.html', {'song': song}),
        'key_details': _get_key_details(request, song, set_pk, song_in_set),
        'song_meta': {
            'title': song.title,
            'artist': song.artist,
        },
    }


def _is_beaming(request):
    return request.session.get('is_beaming', False)


def _get_or_create_beam(request, set, song_index=None):
    owner = _get_or_create_user_uuid(request)
    if _is_beaming(request):
        beams = Beam.objects.filter(owner=owner)

        # This should never happen, but just in case, remove down to only one
        # beam per user
        if beams.count() > 1:
            beams.delete()
            # Since this should never happen, I have no qualms about doing a
            # second database filter here
            beams = Beam.objects.filter(owner=owner)

        # Find or create the beam object
        if beams.count() == 1:
            beam = beams[0]
        else:
            device_name = _get_or_create_device_name(request)
            beam = Beam(
                set=set,
                owner=owner,
                beamer_device_name=device_name,
                current_song_index=song_index)
            beam.save()

        return beam

    else:
        return None


def _delete_beam(request):
    owner = _get_or_create_user_uuid(request)
    beams = Beam.objects.filter(owner=owner)
    beams.delete()


###########################
# VIEWS
###########################

def index(request):
    return redirect(reverse('songs'))


def sets_mine(request):
    # If we're here we don't have a current set
    _clear_current_set(request)

    # Find all sets we have permission to see
    sets_queryset = Set.objects.filter(owner=_get_or_create_user_uuid(request))

    paginator = Paginator(sets_queryset.order_by('-last_updated'), 20)
    page_num = request.GET.get('page', 1)
    _sets = paginator.get_page(page_num)

    return render(request, 'rechorder/sets_mine.html', {
        'sets': _sets,
        **_get_header_links(
            request,
            header_link_back=reverse('sets')),
    })


def sets_others(request):
    # If we're here we don't have a current set
    _clear_current_set(request)

    # Find all sets we have permission to see
    sets_queryset = \
        Set.objects.filter(is_public=True).exclude(owner=_get_or_create_user_uuid(request))

    paginator = Paginator(sets_queryset.order_by('-last_updated'), 20)
    page_num = request.GET.get('page', 1)
    _sets = paginator.get_page(page_num)

    return render(request, 'rechorder/sets_others.html', {
        'sets': _sets,
        **_get_header_links(
            request,
            header_link_back=reverse('sets')),
    })


def sets(request):
    _clear_current_set(request)

    return render(request, 'rechorder/sets_choose_view.html', {
        **_get_header_links(request),
    })


def set_new(request):
    new_set = Set(owner=_get_or_create_user_uuid(request))
    new_set.save()
    new_set.name = 'New Set {}'.format(new_set.pk)
    new_set.save()
    return redirect(reverse('set', args=[new_set.pk]))


def set_duplicate(request, set_id):
    this_set = get_object_or_404(Set, pk=set_id)
    this_set.pk = None
    this_set.owner = _get_or_create_user_uuid(request)
    this_set.is_public = True
    this_set.save()
    this_set.name = "{} Copy of '{}'".format(this_set.pk, this_set.name)
    this_set.save()
    return redirect(reverse('set', args=[this_set.pk]))


def set_add_song(request, set_id):
    song = Song.objects.get(pk=int(request.POST.get('song_id')))

    this_set = get_object_or_404(Set, pk=set_id)

    # Get sounding key from current settings
    sounding_key_index = _get_sounding_key_index(request, song)

    song_in_set = {
        'id': song.pk,
        'key_index': sounding_key_index,
    }

    # Copy un-setted key settings to set settings
    _set_transpose_data(
        request,
        song.pk,
        this_set.pk,
        len(this_set.song_list),
        _get_transpose_data(request, song.pk, None, None))

    if request.POST.get('go_live', False):
        last_song_index = int(request.session.get('last_song_in_set'))
        song_in_set_index = last_song_index + 1 if last_song_index is not None else len(this_set.song_list)
        this_set.song_list.insert(song_in_set_index, song_in_set)
        this_set.save()

        redirect_url = reverse('set.song', args=[this_set.pk, song_in_set_index])
        return JsonResponse({'success': True, 'redirect': redirect_url})
    else:
        this_set.song_list.append(song_in_set)
        this_set.save()
        return JsonResponse({'success': True})


def set_clear(request, set_id):
    this_set = get_object_or_404(Set, pk=set_id)
    this_set.song_list = []
    this_set.beamed_song_index = -1
    this_set.save()
    return JsonResponse({'success': True})


def set(request, set_id):
    this_set = get_object_or_404(Set, pk=set_id)
    this_set.check_list_integrity()
    set_songs = []

    # Check permissions etc.
    am_i_owner = this_set.owner == _get_or_create_user_uuid(request)
    is_viewable = this_set.is_public | am_i_owner

    # Make this the current set
    _set_current_set(request, this_set)

    try:
        request.session.pop('last_song_in_set')
        request.session.modified = True
    except KeyError:
        pass

    for song in this_set.song_list:
        s = Song.objects.get(pk=song['id'])
        set_song = {
            'id': s.pk,
            'key_index': song['key_index'],
            'title': s.title,
        }
        set_songs.append(set_song)

    return render(request, 'rechorder/set.html', {
        'set_songs': set_songs,
        'set': this_set,
        'keys': KEYS,
        'am_i_owner': am_i_owner,
        'is_viewable': is_viewable,
        **_get_header_links(
            request,
            header_link_back=reverse('sets')),
    })


def set_delete(request, set_id):
    set = get_object_or_404(Set, pk=set_id)
    set.delete()
    _clear_current_set(request)
    return JsonResponse({'success': True})


def set_update(request, set_id):
    this_set = get_object_or_404(Set, pk=set_id)
    this_set.song_list = json.loads(request.POST.get('new_set'))
    this_set.save()
    return JsonResponse({'success': True})


def set_rename(request, set_id):
    this_set = get_object_or_404(Set, pk=set_id)
    this_set.name = request.POST.get('name')[:200]
    this_set.is_public = request.POST.get('is_public') == "true"
    this_set.is_protected = request.POST.get('is_protected') == "true"
    this_set.save()
    return JsonResponse({'success': True, 'new_name': this_set.name})


def set_delete_all_old(request):
    # Deletes all unprotected sets older than 1 month
    one_month_ago = datetime.datetime.now() - datetime.timedelta(days=31)
    Set.objects.filter(last_updated__lt=one_month_ago, is_protected=False).delete()
    return redirect(reverse('sets'))


def set_show_song(request, set_id, song_index):
    this_set = get_object_or_404(Set, pk=set_id)

    try:
        # We'll never get negative numbers if the URL doesn't allow it
        song_index = int(song_index)
        song_in_set = this_set.song_list[song_index]
    except (ValueError, IndexError):
        return HttpResponseNotFound('<h1>Error: Page not found</h1>')

    request.session['last_song_in_set'] = song_index
    request.session.modified = True

    song = get_object_or_404(Song, pk=song_in_set['id'])

    # Update beam if applicable
    if _is_beaming(request):
        beam = _get_or_create_beam(request, this_set)
        beam.set = this_set
        beam.current_song_index = song_index
        beam.save()

    key_index, capo_fret_number = _get_song_key_index(request, song, this_set.pk, song_index)
    display_style = _get_display_style(request)
    song.display_in(key_index, display_style)

    context = {
        'song': song,
        'current_index': song_index,
        'set': this_set,
        'set_length': len(this_set.song_list),
        'max_index': len(this_set.song_list) - 1,
        'am_i_owner': this_set.owner == _get_or_create_user_uuid(request),
        **_get_base_song_context_dict(request, song, this_set.pk, song_index),
        **_get_header_links(
            request,
            header_link_back=reverse('set', args=[this_set.pk]),
            header_link_set=reverse('set', args=[this_set.pk]),
            header_link_songs=reverse('songs')),
    }
    return render(request, 'rechorder/song_in_set.html', context)


def set_print(request, set_id):
    this_set = get_object_or_404(Set, pk=set_id)
    this_set.check_list_integrity()

    songs = []
    for i in range(len(this_set.song_list)):
        song_in_set = this_set.song_list[i]
        song = Song.objects.get(pk=song_in_set['id'])
        request.GET.get('no_personal_keys', False)
        if request.GET.get('no_personal_keys', False):
            key_index =  song_in_set['key_index']
            capo_fret_number = 0
        else:
            key_index, capo_fret_number = _get_song_key_index(request, song, this_set.pk, i)

        display_style = _get_display_style(request)
        song.display_in(key_index, display_style)

        songs.append({
            'song': song,
            'sounding_key_index': song_in_set['key_index'],
            'key_index': key_index,
            'capo_fret_number': capo_fret_number,
        })

    context = {
        'songs': songs,
        'set_id': this_set.pk,
    }

    if request.GET.get('no_personal_keys', False):
       context['no_personal_keys'] = True

    return render(request, 'rechorder/print_set.html', context)


def beaming_toggle(request):
    is_beaming = json.loads(request.POST.get('enable', ''))

    request.session['is_beaming'] = bool(is_beaming)
    request.session.modified = True

    if is_beaming:
        # If we also have a set ID, we can create the Beam object. If not,
        # it'll be done when the set is navigated to.
        try:
            set_pk = int(request.POST.get('set_pk', None))
            song_index = int(request.POST.get('song_index', None))
            print(set_pk, song_index)
            if None not in (set_pk, song_index):
                _set = Set.objects.get(pk=set_pk)
                beam = _get_or_create_beam(request, _set, song_index)
        except (Set.DoesNotExist, ValueError, TypeError):
            pass

    else:
        _delete_beam(request)

    return beaming_status(request)


def beaming_status(request):
    return JsonResponse({'beaming_enabled': _is_beaming(request)})


def get_beams(request):
    update_time_cutoff = datetime.datetime.now() - datetime.timedelta(days=1)
    # Clean all old beams out
    Beam.objects.filter(last_updated__lte=update_time_cutoff).delete()

    context = {
        # Will get all sets that have a beamed song index
        'masters': Beam.objects.all().order_by('-last_updated'),
        **_get_header_links(request),
    }
    return render(request, 'rechorder/beam_masters.html', context)


def slave_to_master(request, beam_id):
    beam = get_object_or_404(Beam, pk=beam_id)

    context_base = {
        'capo_fret_number': 0,
        'beam': beam,
        **_get_header_links(request, header_link_back=reverse('slave')),
    }

    if beam.current_song_index is not None and \
            0 <= beam.current_song_index < len(beam.set.song_list):
        song_in_set = beam.set.song_list[beam.current_song_index]
        song = get_object_or_404(Song, pk=song_in_set['id'])

        key_index, capo_fret_number = _get_song_key_index(
            request,
            song,
            beam.set.pk,
            beam.current_song_index)
        display_style = _get_display_style(request)
        song.display_in(key_index, display_style)

        context = {
            **context_base,
            'song': song,
            'update_token': beam.has_changed_count,
            'capo_fret_number': capo_fret_number,
            'set_length': len(beam.set.song_list),
            'current_index': beam.current_song_index,
            **_get_base_song_context_dict(request, song, beam.set.pk, beam.current_song_index),
        }
    else:
        context = {
            **context_base,
            'song': None,
            'update_token': -1,
        }

    return render(request, 'rechorder/song_as_slave.html', context)


def slave_get_update_token(request, beam_id):
    beam = get_object_or_404(Beam, pk=beam_id)
    return JsonResponse({'update_token': beam.has_changed_count})


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
    display_style = _get_display_style(request)
    song.display_in(key_index, display_style)

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
    song_in_set_index = int(request.POST.get('song_in_set_index', -1))
    if set_id < 0:
        set_id = None
    if song_in_set_index < 0:
        song_in_set_index = None

    # Sounding key index is static if we have a set ID, or dynamic (and thus in the form details)
    # if we're outside a set
    if None in (set_id, song_in_set_index):
        try:
            # Pop this off the data since we store it differently in the dict
            sounding_key_index = int(transpose_data.pop('sounding-key'))
        except (ValueError, KeyError):
            # Default to original key
            sounding_key_index = song.original_key
        transpose_data['sounding_key_index'] = sounding_key_index
    else:
        transpose_data['sounding_key_index'] = request.POST['sounding_key_index']

    # Save the key information
    _set_transpose_data(request, song_id, set_id, song_in_set_index, transpose_data)

    key_index, capo_fret_number = _get_song_key_index(request, song, set_id, song_in_set_index)
    display_style = _get_display_style(request)
    song.display_in(key_index, display_style)

    return JsonResponse(_get_update_song_data(request, song, set_id, song_in_set_index))


def songs(request):
    _songs = Song.objects.order_by('title')

    try:
        request.session.pop('last_visited_song')
        request.session.modified = True
    except KeyError:
        pass

    context = {
        'songs': _songs,
        'keys': KEYS,
        **_get_header_links(request, header_link_songs=reverse('songs'))
    }
    return render(request, 'rechorder/songs.html', context)


def song(request, song_id):
    song = get_object_or_404(Song, pk=song_id)

    request.session['last_visited_song'] = song_id
    request.session.modified = True

    key_index, capo_fret_number = _get_song_key_index(request, song)
    display_style = _get_display_style(request)
    song.display_in(key_index, display_style)

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


def settings(request):
    context = {
        'selected_shapes': _get_selected_chord_shapes(request),
        'possible_shapes': [{'name': KEYS[i], 'index': i} for i in range(12)],
        'device_name': _get_or_create_device_name(request),
        'chord_display_style': _get_display_style(request),
        **_get_header_links(request),
    }
    return render(request, 'rechorder/user_settings.html', context)


def settings_set(request):
    request.session['selected_chord_shapes'] = \
        [int(i) for i in json.loads(request.POST.get('permitted_shapes', ''))]
    request.session['chord_display_style'] = json.loads(request.POST.get('display_style', ''))['chord-display-style']
    request.session['device_name'] = request.POST.get('device_name', '["Unnamed Device"]').strip()
    request.session.modified = True

    # Try to update the user's beam if it exists
    try:
        beam = Beam.objects.get(owner=_get_or_create_user_uuid(request))
        beam.beamer_device_name = request.session['device_name']
        beam.save()
    except Beam.DoesNotExist:
        pass

    return JsonResponse({'success': True})


def upload(request):
    if request.method == 'POST':
        if request.FILES.get('zipfile') is not None:
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
        elif request.FILES.get('jsonfile') is not None:
            data = json.load(request.FILES['jsonfile'])
            for s in data:
                if s.get('model') != 'rechorder.song':
                    continue
                song_data = s['fields']
                existing_songs = Song.objects.filter(
                    title=song_data['title'],
                    artist=song_data['artist'],
                    original_key=song_data['original_key'],
                    raw=song_data['raw'],
                )
                if existing_songs.count() == 0:
                    new_song = Song(
                        title=song_data['title'],
                        artist=song_data['artist'],
                        original_key=song_data['original_key'],
                        raw=song_data['raw'],
                    )
                    new_song.save()
                    print("Added new song: {}".format(new_song.title))

        return render(request, 'rechorder/upload.html')
    else:
        return render(request, 'rechorder/upload.html')


def download(request):
    songs = Song.objects.order_by('title')
    songs_json = serializers.serialize('json', songs)
    return HttpResponse(songs_json, content_type='application/json')