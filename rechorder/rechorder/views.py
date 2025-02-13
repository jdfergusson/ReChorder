from django.http import (
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseBadRequest,
    HttpResponseForbidden,
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
from django.utils.text import slugify
from django.db.utils import IntegrityError
from django.db.models.functions import Lower

from copy import deepcopy

import datetime
import json
import os
import uuid
import zipfile

from rechorder.music_handler.interpret import KEYS, ABSOLUTE_LOOKUP, interpret_absolute_chord, song_from_onsong_text


from .models import Song, Set, Beam, User, ItemInSet, Tag


def _get_selected_chord_shapes(request):
    if 'selected_chord_shapes' not in request.session:
        # Start with C, D, E and G
        request.session['selected_chord_shapes'] = [3, 5, 7, 10]
        request.session.modified = True
    return request.session['selected_chord_shapes']


def _get_display_style(request):
    if request.session.get('chord_display_style') not in ('letters', 'nashville', 'roman'):
        request.session['chord_display_style'] = 'letters'
        request.session.modified = True
    return request.session['chord_display_style']


def _get_current_set_id(request):
    set_id = request.session.get('current_set_id')
    if Set.objects.filter(pk=set_id).exists():
        return set_id
    else:
        try:
            request.session.pop('current_set_id')
        except KeyError:
            pass
    return None


def _set_current_set(request, set):
    request.session['current_set_id'] = set.pk


def _clear_current_set(request):
    request.session['current_set_id'] = None


def _get_user_uuid(request):
    user_uuid = request.session.get('user_uuid')
    if user_uuid is None:
        user_uuid = str(uuid.uuid4())
        request.session['user_uuid'] = user_uuid
    return user_uuid


def _get_user(request):
    try:
        return User.objects.get(uuid=request.session.get('user_uuid'))
    except User.DoesNotExist:
        return None


def _get_or_create_device_name(request):
    device_name = request.session.get('device_name')
    if device_name is None:
        device_name = 'Unnamed Device'
    if device_name == 'Unnamed Device':
        user = _get_user(request)
        if user:
            device_name = "{}'s Device".format(user.name)
        request.session['device_name'] = device_name
    return device_name


def _get_optional_line_breaks_setting(request):
    opt_line_breaks = request.session['opt_line_breaks'] = bool(request.session.get('opt_line_breaks', False))
    return opt_line_breaks


def _get_display_full_song_order(request):
    display_full_song_order = \
        request.session['display_full_song_order'] = bool(request.session.get('display_full_song_order', False))
    return display_full_song_order


def _get_base_context(request, **overrides):
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

    user = _get_user(request)
    if user and user.is_admin:
        users_link = reverse('users')
    else:
        users_link = ""

    links =  {
        'header_link_back': '#',
        'header_link_songs': songs_link,
        'header_link_set': set_link,
        'header_link_receive': reverse('slave'),
        'header_link_users': users_link,
        'header_link_settings': reverse('settings'),
    }

    for override in overrides:
        links[override] = overrides[override]

    context = {
        **links,
        'user': user,
        'ItemInSetType': ItemInSet.ItemInSetType,
    }

    return context


def _get_sounding_key_index(request, song, item_in_set=None):
    """
    Returns the index of the sounding key of the song as preferred by the user or chosen by the current set.
    If the user has not set a preference, set the sounding key to the original key of the song.
    """
    sounding_key_index = song.original_key
    try:
        if item_in_set is not None:
            sounding_key_index = item_in_set.sounding_key_index
        else:
            song_key_data = _get_transpose_data(request, song.pk)
            sounding_key_index = song_key_data['sounding_key_index']
    except Exception:
        pass

    return sounding_key_index


def _get_transpose_data(request, song_pk, item_in_set=None):
    if item_in_set is None:
        return request.session.get('keys', {}).get('{}'.format(song_pk))
    return request.session.get('keys_in_sets', {}).get('{}'.format(item_in_set.pk))


def _set_transpose_data(request, song_pk, transpose_data, item_in_set=None):
    if item_in_set is None:
        keys_dict = request.session.get('keys', {})
        keys_dict['{}'.format(song_pk)] = deepcopy(transpose_data)
        request.session['keys'] = keys_dict
    else:
        keys_dict = request.session.get('keys_in_sets', {})
        keys_dict['{}'.format(item_in_set.pk)] = deepcopy(transpose_data)
        request.session['keys_in_sets'] = keys_dict
    request.session.modified = True


def _get_song_key_index(request, song, item_in_set=None):
    sounding_key_index = _get_sounding_key_index(request, song, item_in_set)

    # Get transpose data for the specific view we're looking at now
    transpose_data = _get_transpose_data(request, song.pk, item_in_set)

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
            key_index = (sounding_key_index + delta) % 12;
        elif transpose_type == 'abs':
            key_index = int(transpose_data.get('absolute-force-index', sounding_key_index))

    return key_index, capo_fret_number


def _get_key_details(request, song, item_in_set=None):
    key_details = {}
    key_details['key_index'], key_details['capo_fret_number'] = \
        _get_song_key_index(request, song, item_in_set=item_in_set)

    key_details['sounding_key_index'] = _get_sounding_key_index(request, song, item_in_set=item_in_set)
    key_details['transpose_data'] = _get_transpose_data(request, song.pk, item_in_set=item_in_set) or {
        # Default to displaying in sounding key
        'adv-tran-opt': 'sk'
    }
    key_details['original_key_index'] = song.original_key
    return key_details


def _get_base_song_context_dict(request, song, item_in_set=None):
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
            set_is_editable = set.owner == _get_user_uuid(request)
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
        'key_details': _get_key_details(request, song, item_in_set=item_in_set),
        'current_set': set,
        'set_is_editable': set_is_editable,
        'opt_line_breaks': _get_optional_line_breaks_setting(request),
        'display_full_song_order': _get_display_full_song_order(request),
        'is_verse_order_okay': not bool(song.check_verse_order()),
        'beaming_enabled': _is_beaming(request),
        'available_tags': Tag.objects.all,
    }


def _get_update_song_data(request, song, item_in_set=None):
    return {
        'song_html': render_to_string('rechorder/_print_song.html', {'song': song}),
        'key_details': _get_key_details(request, song, item_in_set=item_in_set),
        'song_meta': {
            'title': song.title,
            'artist': song.artist,
        },
    }


def _is_beaming(request):
    return request.session.get('is_beaming', False)


def _get_or_create_beam(request, item_in_set):
    owner = _get_user_uuid(request)
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
                current_item=item_in_set,
                owner=owner,
                beamer_device_name=device_name)
            beam.save()

        return beam

    else:
        return None


def _fix_set_indices(this_set):
    items = ItemInSet.objects.filter(set=this_set).order_by('index_in_set')
    for idx, item in enumerate(items):
        item.index_in_set = idx
        item.save()


def _delete_beam(request):
    owner = _get_user_uuid(request)
    beams = Beam.objects.filter(owner=owner)
    beams.delete()


###########################
# VIEWS
###########################

def index(request):
    return redirect(reverse('songs'))


##########################################################################################
# Sets
##########################################################################################


def sets_mine(request):
    # If we're here we don't have a current set
    _clear_current_set(request)

    # Find all sets we have permission to see
    sets_queryset = Set.objects.filter(owner=_get_user_uuid(request))

    paginator = Paginator(sets_queryset.order_by('-created_at'), 20)
    page_num = request.GET.get('page', 1)
    _sets = paginator.get_page(page_num)

    return render(request, 'rechorder/sets_mine.html', {
        'sets': _sets,
        **_get_base_context(
            request,
            header_link_back=reverse('sets')),
    })


def sets_others(request):
    # If we're here we don't have a current set
    _clear_current_set(request)

    # Find all sets we have permission to see
    sets_queryset = \
        Set.objects.filter(is_public=True).exclude(owner=_get_user_uuid(request))

    paginator = Paginator(sets_queryset.order_by('-created_at'), 20)
    page_num = request.GET.get('page', 1)
    _sets = paginator.get_page(page_num)

    return render(request, 'rechorder/sets_others.html', {
        'sets': _sets,
        **_get_base_context(
            request,
            header_link_back=reverse('sets')),
    })


def sets(request):
    _clear_current_set(request)

    return render(request, 'rechorder/sets_choose_view.html', {
        **_get_base_context(request),
    })


def set_new(request):
    new_set = Set(owner=_get_user_uuid(request))
    new_set.save()
    new_set.name = 'New Set {}'.format(new_set.pk)
    new_set.save()
    return redirect(reverse('set', args=[new_set.pk]))


def set_duplicate(request, set_id):
    new_set = get_object_or_404(Set, pk=set_id)
    new_set.pk = None
    new_set.owner = _get_user_uuid(request)
    new_set.is_public = True
    new_set.save()
    new_set.name = "{} Copy of '{}'".format(new_set.pk, new_set.name)
    new_set.save()

    # Duplicate all songs in set
    for item in ItemInSet.objects.filter(set=set_id):
        item.pk = None
        item.set = new_set
        item.save()

    return redirect(reverse('set', args=[new_set.pk]))


def set_delete_item_by_index(request):
    item_id = int(request.POST.get('item_id'))
    item = get_object_or_404(ItemInSet, pk=item_id)
    this_set = item.set
    item.delete()
    _fix_set_indices(this_set)
    return JsonResponse({'success': True})


def set_remove_song(request, set_id):
    this_set = get_object_or_404(Set, pk=set_id)
    song_id = int(request.POST.get('song_id'))
    song = get_object_or_404(Song, pk=song_id)
    ItemInSet.objects.filter(song=song, set=this_set).delete()
    _fix_set_indices(this_set)
    return JsonResponse({'success': True})


def set_add_song(request, set_id):
    song = Song.objects.get(pk=int(request.POST.get('song_id')))

    this_set = get_object_or_404(Set, pk=set_id)

    # Get sounding key from current settings
    sounding_key_index = _get_sounding_key_index(request, song)

    # Add the song at the end of the set, which means working out how long the set is
    index_in_set = ItemInSet.objects.filter(set=this_set).count()

    song_in_set = ItemInSet(
        song=song,
        set=this_set,
        sounding_key_index=sounding_key_index,
        index_in_set=index_in_set,
        notes='',
        item_type=ItemInSet.ItemInSetType.SONG,
    )

    song_in_set.save()

    # Copy un-setted key settings to set settings
    # TODO simplify this to just use song_in_set object
    _set_transpose_data(
        request,
        song.pk,
        _get_transpose_data(request, song.pk),
        item_in_set=song_in_set
    )

    if request.POST.get('go_live', False):
        # This appears to be the old code that would, if you pressed "add and go live" insert
        # the song after the last viewed song in the set.
        #last_song_in_set = request.session.get('last_song_in_set')
        #song_in_set_index = len(this_set.song_list)
        #if last_song_in_set is not None:
        #    song_in_set_index = min(int(last_song_in_set) + 1, song_in_set_index)
        #this_set.song_list.insert(song_in_set_index, song_in_set)
        #this_set.save()

        redirect_url = reverse('set.song', args=[this_set.pk, song_in_set.index_in_set])
        return JsonResponse({'success': True, 'redirect': redirect_url})
    else:
        return JsonResponse({'success': True})


def view_set(request, set_id):
    this_set = get_object_or_404(Set, pk=set_id)
    set_songs = []

    # Check permissions etc.
    am_i_owner = this_set.owner == _get_user_uuid(request)
    is_viewable = this_set.is_public | am_i_owner

    # Make this the current set
    _set_current_set(request, this_set)

    try:
        request.session.pop('last_song_in_set')
        request.session.modified = True
    except KeyError:
        pass

    # Get list of set items
    set_items = ItemInSet.objects.filter(set=this_set).order_by('index_in_set')

    return render(request, 'rechorder/set.html', {
        'set_items': set_items,
        'set': this_set,
        'keys': KEYS,
        'can_edit': am_i_owner,
        'am_i_owner': am_i_owner,
        'is_viewable': is_viewable,
        **_get_base_context(
            request,
            header_link_back=reverse('sets_mine') if am_i_owner else reverse('sets_others')),
    })


def set_delete(request, set_id):
    this_set = get_object_or_404(Set, pk=set_id)
    this_set.delete()
    _clear_current_set(request)
    return JsonResponse({'success': True})


def set_update_order(request, set_id):
    this_set = get_object_or_404(Set, pk=set_id)
    new_order = json.loads(request.POST.get('new_order'))
    items = [get_object_or_404(ItemInSet, pk=pk) for pk in new_order]

    for item in items:
        if item.set != this_set:
            raise IntegrityError("Item not in specified set");

    for idx, item in enumerate(items):
        item.index_in_set = idx
        item.save()
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


def set_song_update_notes(request, item_in_set_id):
    item_in_set = get_object_or_404(ItemInSet, pk=item_in_set_id)
    item_in_set.notes = request.POST.get('notes')
    item_in_set.save()
    return JsonResponse({'success': True})


def set_add_text_item(request, set_id):
    this_set = get_object_or_404(Set, pk=set_id)
    # Insert onto set, so make sure set indices are in order first
    _fix_set_indices(this_set)
    new_text_item = ItemInSet(
        set=this_set,
        index_in_set=this_set.num_of_items,
        item_type=ItemInSet.ItemInSetType.TEXT,
        # Default new title name
        title="New Non-song item",
    )
    new_text_item.save()

    return JsonResponse({
        'html': render_to_string(
            'rechorder/_item_in_set_list.html',
            {
                'can_edit': True,
                'item': new_text_item,
                'ItemInSetType': ItemInSet.ItemInSetType,
            }
        ),
        'item_pk': new_text_item.pk,
        'title': new_text_item.title,
    })


def item_set_key(request, item_in_set_id):
    item_in_set = get_object_or_404(ItemInSet, pk=item_in_set_id)
    new_key_index = request.POST.get('sounding_key_index')
    if new_key_index is None:
        # Will cause a 500 error to be returned to the client
        raise IndexError("Invalid Key Index")
    item_in_set.sounding_key_index = new_key_index
    item_in_set.save()
    return JsonResponse({'success': True})


def item_set_title(request, item_in_set_id):
    item_in_set = get_object_or_404(ItemInSet, pk=item_in_set_id)
    new_title = request.POST['new_title']
    item_in_set.title = new_title
    item_in_set.save()
    return JsonResponse({'success': True})


def set_show_song(request, set_id, song_index):
    try:
        this_set = Set.objects.get(pk=set_id)
    except Set.DoesNotExist:
        return redirect(reverse('sets'))

    try:
        # We'll never get negative numbers if the URL doesn't allow it
        song_index = int(song_index)
        # If this returns more than one object, something has gone wrong. Just return the first one.
        set_item = this_set.items.filter(index_in_set=song_index)[0]
    except (ValueError, IndexError):
        return redirect(reverse('set', args=[this_set.pk]))

    request.session['last_song_in_set'] = song_index

    # Update beam if applicable
    if _is_beaming(request):
        beam = _get_or_create_beam(request, set_item)
        beam.current_item = set_item
        beam.save()

    set_length = this_set.items.count()

    if set_item.item_type == ItemInSet.ItemInSetType.SONG:
        song = set_item.song
        key_index, capo_fret_number = _get_song_key_index(request, song, item_in_set=set_item)
        display_style = _get_display_style(request)
        song.display_in(key_index, display_style)

        context = {
            'song': song,
            'current_index': song_index,
            'set': this_set,
            'item_in_set': set_item,
            'set_length': set_length,
            'max_index': set_length - 1,
            'am_i_owner': this_set.owner == _get_user_uuid(request),

            **_get_base_song_context_dict(request, song, item_in_set=set_item),
            **_get_base_context(
                request,
                header_link_back=reverse('set', args=[this_set.pk]),
                header_link_set=reverse('set', args=[this_set.pk]),
                header_link_songs=reverse('songs')),
        }
        return render(request, 'rechorder/song_in_set.html', context)

    elif set_item.item_type == ItemInSet.ItemInSetType.TEXT:
        context = {
            'current_index': song_index,
            'set': this_set,
            'item_in_set': set_item,
            'set_length': set_length,
            'max_index': set_length - 1,
            'am_i_owner': this_set.owner == _get_user_uuid(request),
            **_get_base_context(
                request,
                header_link_back=reverse('set', args=[this_set.pk]),
                header_link_set=reverse('set', args=[this_set.pk]),
                header_link_songs=reverse('songs')),
        }
        return render(request, 'rechorder/song_in_set.html', context)


def set_print(request, set_id):
    this_set = get_object_or_404(Set, pk=set_id)

    songs = []
    for item in this_set.items.order_by('index_in_set'):
        if item.item_type == ItemInSet.ItemInSetType.SONG:
            song = item.song
            if request.GET.get('no_personal_keys', False):
                key_index = item.sounding_key_index
                capo_fret_number = 0
            else:
                key_index, capo_fret_number = _get_song_key_index(request, song, item_in_set=item)

            display_style = _get_display_style(request)
            song.display_in(key_index, display_style)

            songs.append({
                'song': song,
                'sounding_key_index': item.sounding_key_index,
                'key_index': key_index,
                'capo_fret_number': capo_fret_number,
                'notes': item.notes,
            })

    context = {
        'songs': songs,
        'set_id': this_set.pk,
        'opt_line_breaks': _get_optional_line_breaks_setting(request),
        'display_full_song_order': _get_display_full_song_order(request),
    }

    if request.GET.get('no_personal_keys', False):
       context['no_personal_keys'] = True

    return render(request, 'rechorder/print_set.html', context)


##########################################################################################
# Beaming
##########################################################################################


def beaming_toggle(request):
    is_beaming = json.loads(request.POST.get('enable', ''))

    request.session['is_beaming'] = bool(is_beaming)
    request.session.modified = True

    if is_beaming:
        # If we also have a set ID, we can create the Beam object. If not,
        # it'll be done when the set is navigated to.
        try:
            this_set = get_object_or_404(Set, pk=int(request.POST.get('set_pk', None)))
            song_index = int(request.POST.get('song_index', None))
            if song_index is not None:
                item = this_set.items[song_index]
                _get_or_create_beam(request, item)
        except (Set.DoesNotExist, ValueError, TypeError, IndexError):
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
        **_get_base_context(request),
    }
    return render(request, 'rechorder/beam_masters.html', context)


def slave_to_master(request, beam_id):
    beam = get_object_or_404(Beam, pk=beam_id)

    context_base = {
        'capo_fret_number': 0,
        'beam': beam,
        **_get_base_context(request, header_link_back=reverse('slave')),
    }

    if beam.current_item is None:
        context = {
            **context_base,
            'item_in_set': None,
            'update_token': -1,
        }
    elif beam.current_item.item_type == ItemInSet.ItemInSetType.SONG:
        song = beam.current_item.song

        # TODO: Why are we passing the song and the current item, when the current item contains the song
        key_index, capo_fret_number = _get_song_key_index(
            request,
            song,
            item_in_set=beam.current_item)
        display_style = _get_display_style(request)
        song.display_in(key_index, display_style)

        context = {
            **context_base,
            'item_in_set': beam.current_item,
            'ItemInSetType': ItemInSet.ItemInSetType,
            'song': song,
            'update_token': beam.has_changed_count,
            'capo_fret_number': capo_fret_number,
            'set_length': beam.current_item.set.num_of_items,
            'current_index': beam.current_item.index_in_set,
            **_get_base_song_context_dict(request, song, item_in_set=beam.current_item),
        }
    elif beam.current_item.item_type == ItemInSet.ItemInSetType.TEXT:
        context = {
            **context_base,
            'item_in_set': beam.current_item,
            'update_token': beam.has_changed_count,
            'ItemInSetType': ItemInSet.ItemInSetType,
        }
    else:
        # This should cause an error
        return None

    return render(request, 'rechorder/song_as_slave.html', context)


def slave_get_update_token(request, beam_id):
    beam = get_object_or_404(Beam, pk=beam_id)
    return JsonResponse({'update_token': beam.has_changed_count})


##########################################################################################
# Songs
##########################################################################################


def song_update(request, song_id):
    song = get_object_or_404(Song, pk=song_id)

    # Can't be None
    title = request.POST.get('title')
    artist = request.POST.get('artist')
    tags = request.POST.getlist('tags[]')
    original_key = int(request.POST.get('original_key'))
    key_notes = request.POST.get('key_notes')
    verse_order = request.POST.get('verse_order')
    content = request.POST.get('content')

    # Can be None
    try:
        ccli_number = int(request.POST.get('ccli_number'))
    except (ValueError, TypeError):
        ccli_number = None

    if None not in (title, artist, original_key, key_notes, content):
        song.title = title
        song.artist = artist
        song.ccli_number = ccli_number
        song.original_key = original_key
        song.key_notes = key_notes
        song.verse_order = verse_order
        song.raw = content

        song.tags.clear()
        for tag_id in tags:
            try:
                song.tags.add(Tag.objects.get(id=tag_id))
            except Tag.DoesNotExist:
                pass

        song.save()

        verse_order_errors = render_to_string('rechorder/_verse_order_errors.html', {'errors': song.check_verse_order})

        return JsonResponse({'verse_order': song.verse_order, 'verse_order_errors': verse_order_errors})
    return HttpResponseBadRequest('Invalid POST data')


def song_delete(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    song.delete()
    # TODO: We might need to worry about the integrity of the sets containing the song
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
        'opt_line_breaks': _get_optional_line_breaks_setting(request),
        'display_full_song_order': _get_display_full_song_order(request),
    }

    if request.GET.get('no_personal_keys', False):
       context['no_personal_keys'] = True

    return render(request, 'rechorder/print_set.html', context)


def song_xml(request, song_id):
    _song = get_object_or_404(Song, pk=song_id)
    return HttpResponse(_song.to_xml(), content_type='text/xml')


def song_create(request):
    if request.method == 'POST':
        song = Song(
            title=request.POST.get('title'),
            artist=request.POST.get('artist'),
            ccli_number=request.POST.get('ccli_number') or None,
            original_key=request.POST.get('original_key'),
            key_notes=request.POST.get('key_notes', ''),
            verse_order=request.POST.get('verse_order', ''),
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
            **_get_base_context(request, header_link_back=reverse('songs')),
        }
        return render(request, 'rechorder/song_create.html', context)


def song_get_verse_order_errors(request, song_id):
    _song = get_object_or_404(Song, pk=song_id)
    verse_order_errors = _song.check_verse_order()
    verse_order_errors_html = render_to_string('rechorder/_verse_order_errors.html', {'errors': verse_order_errors}),

    return JsonResponse({
        'errors_html': verse_order_errors_html,
        'errors_list': verse_order_errors,
        'is_verse_order_okay': not bool(verse_order_errors),
    })


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

    # TODO Can we pass the details into this function differently?

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
        item_in_set = None
    else:
        transpose_data['sounding_key_index'] = request.POST['sounding_key_index']
        # This looks fragile, but if we've got bad data we want to throw an error
        item_in_set = ItemInSet.objects.filter(set=set_id, index_in_set=song_in_set_index)[0]

    # Save the key information
    _set_transpose_data(request, song_id, transpose_data, item_in_set=item_in_set)

    key_index, capo_fret_number = _get_song_key_index(request, song, item_in_set=item_in_set)
    display_style = _get_display_style(request)
    song.display_in(key_index, display_style)

    return JsonResponse({
        'song_html': render_to_string(
            'rechorder/_print_song.html',
            {'song': song, **_get_base_song_context_dict(request, song, item_in_set=item_in_set)}
        ),
        'key_details': _get_key_details(request, song, item_in_set=item_in_set),
        'song_meta': {
            'title': song.title,
            'artist': song.artist,
        },
    })


def songs(request):
    _songs = Song.objects.order_by('title')

    # In this case, the current set is only wanted if it's owned by the current user.
    song_ids_in_set = []
    try:
        this_set = Set.objects.get(pk=_get_current_set_id(request), owner=_get_user_uuid(request))
        items_in_set = ItemInSet.objects.filter(set=this_set, item_type=ItemInSet.ItemInSetType.SONG)
        song_ids_in_set = [i.song.pk for i in items_in_set]
        current_set_id = this_set.pk
    except Set.DoesNotExist:
        current_set_id = -1

    try:
        request.session.pop('last_visited_song')
        request.session.modified = True
    except KeyError:
        pass

    context = {
        'songs': _songs,
        'keys': KEYS,
        'current_set_id': current_set_id,
        'song_ids_in_set': song_ids_in_set,
        'tags': Tag.objects.all,
        **_get_base_context(request, header_link_songs=reverse('songs'))
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
        **_get_base_context(
            request,
            header_link_songs=reverse('songs'),
            header_link_back='{}#song{}'.format(reverse('songs'), song.id),
        ),
    }
    return render(request, 'rechorder/song.html', context)


##########################################################################################
# Settings
##########################################################################################

def download_xml(request):
    songs = Song.objects.all()
    response = HttpResponse(content_type='application/zip')
    zip_file = zipfile.ZipFile(response, 'w')
    for song in songs:
        try:
            zip_file.writestr('openlyric-songs/{}-{}.xml'.format(song.pk, slugify(song.title)), song.to_xml())
        except Exception:
            pass
    response['Content-Disposition'] = 'attachment; filename="rechorder_songs.zip"'
    return response


def settings(request):
    context = {
        'beaming_enabled': _is_beaming(request),
        'selected_shapes': _get_selected_chord_shapes(request),
        'possible_shapes': [{'name': KEYS[i], 'index': i} for i in range(12)],
        'device_name': _get_or_create_device_name(request),
        'chord_display_style': _get_display_style(request),
        'opt_line_breaks': _get_optional_line_breaks_setting(request),
        'display_full_song_order': _get_display_full_song_order(request),
        **_get_base_context(request),
    }
    return render(request, 'rechorder/settings.html', context)


def settings_set(request):
    request.session['selected_chord_shapes'] = \
        [int(i) for i in json.loads(request.POST.get('permitted_shapes', ''))]
    request.session['chord_display_style'] = request.POST.get('display_style', 'letters')
    request.session['device_name'] = request.POST.get('device_name', '["Unnamed Device"]').strip()
    request.session['opt_line_breaks'] = bool(json.loads(request.POST.get('opt_line_breaks', 'false')))
    request.session['display_full_song_order'] = bool(json.loads(request.POST.get('display_full_song_order', 'false')))
    request.session.modified = True

    # Try to update the user's beam if it exists
    try:
        beam = Beam.objects.get(owner=_get_user_uuid(request))
        beam.beamer_device_name = request.session['device_name']
        beam.save()
    except Beam.DoesNotExist:
        pass

    return JsonResponse({'success': True})

##########################################################################################
# Users
##########################################################################################


def user_login(request):
    username = request.POST['username']
    password = request.POST['password']

    try:
        user = User.objects.get(name=username)
    except User.DoesNotExist:
        return JsonResponse({'success': False})

    if not user.check_password(password):
        return JsonResponse({'success': False})

    request.session['user_uuid'] = user.uuid
    request.session.modified = True

    return JsonResponse({'success': True})


def user_create(request):
    username = request.POST['username']
    password = request.POST['password']
    # By using the current uuid, we make the new user the owner of the sets that the device making the request owns.
    uuid = _get_user_uuid(request)

    # Test for a current user with the same username
    try:
        User.objects.get(name=username)
        return JsonResponse({'success': False, 'error_message': 'A user with that name already exists'})
    except User.DoesNotExist:
        pass

    # Check that the UUID hasn't come from a user that's already logged in
    try:
        User.objects.get(uuid=uuid)
        return JsonResponse({'success': False, 'error_message': 'Something went wrong. Do you need to logout?'})
    except User.DoesNotExist:
        pass

    try:
        user = User(uuid=uuid, name=username)
        user.set_password(password)
        user.save()
    except IntegrityError:
        return JsonResponse({'success': False, 'error_message': 'Something went wrong, please try different values'})

    request.session['user_uuid'] = user.uuid
    request.session.modified = True

    return JsonResponse({'success': True})


def user_logout(request):
    request.session.pop('user_uuid')
    request.session.modified = True
    return JsonResponse({'success': True})


def users(request):
    current_user = get_object_or_404(User, uuid=_get_user_uuid(request))

    if not current_user.is_admin:
        return redirect(reverse('user', args=[current_user.id]))

    paginator = Paginator(User.objects.all().order_by(Lower('name')), 10)
    page_num = request.GET.get('page', 1)
    _users = paginator.get_page(page_num)

    context = {
        'users': _users,
        **_get_base_context(
            request,
            header_link_back="javascript:history.back()"
        ),
    }
    return render(request, 'rechorder/users.html', context)


def user(request, user_id=None, user_name=None):
    current_user = _get_user(request)

    if user_id is not None:
        user = get_object_or_404(User, id=user_id)
    else:
        user = get_object_or_404(User, name=user_name)

    if not (current_user and (current_user == user or current_user.is_admin)):
        return HttpResponseForbidden()

    context = {
        'this_user': user,
        **_get_base_context(
            request,
            header_link_back="javascript:history.back()"
        ),
    }
    return render(request, 'rechorder/user.html', context)


def user_update(request, user_id):
    current_user = get_object_or_404(User, uuid=_get_user_uuid(request))
    this_user = get_object_or_404(User, id=user_id)

    if current_user != this_user and not current_user.is_admin:
        return HttpResponseForbidden()

    if 'username' in request.POST:
        this_user.name = request.POST['username'].strip()
        this_user.save()
        return JsonResponse({'success': True})

    elif 'password' in request.POST:
        this_user.set_password(request.POST['password'])
        this_user.save()
        return JsonResponse({'success': True})

    elif 'is_admin' in request.POST:
        if not current_user.is_admin:
            return HttpResponseForbidden()
        this_user.is_admin = request.POST['is_admin'] == "true"
        this_user.save()
        return JsonResponse({'success': True})

    else:
        return HttpResponseBadRequest()

    return JsonResponse({'success': False})


##########################################################################################
# Admin
##########################################################################################


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
                    key_notes=song_data['key_notes'],
                    verse_order=song_data['verse_order'],
                    raw=song_data['raw'],
                )
                if existing_songs.count() == 0:
                    new_song = Song(
                        title=song_data['title'],
                        artist=song_data['artist'],
                        original_key=song_data['original_key'],
                        key_notes=song_data['key_notes'],
                        verse_order=song_data['verse_order'],
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
