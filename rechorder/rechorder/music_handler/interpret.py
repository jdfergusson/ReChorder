import re

ABSOLUTE_LOOKUP = {
    'a': 0,
    'a#': 1,
    'bb': 1,
    'b': 2,
    'b#': 3,
    'cb': 2,
    'c': 3,
    'c#': 4,
    'db': 4,
    'd': 5,
    'd#': 6,
    'eb': 6,
    'e': 7,
    'e#': 8,
    'fb': 7,
    'f': 8,
    'f#': 9,
    'gb': 9,
    'g': 10,
    'g#': 11,
    'ab': 11
}

KEYS = ['A', 'B\u266d', 'B', 'C', 'C\u266f', 'D', 'E\u266d', 'E', 'F', 'F\u266f', 'G', 'A\u266d']


def interpret_absolute_chord(string):
    # Remove any surrounding brackets
    string = string.replace('[', '').replace(']', '')

    # Remove any internal parentheses
    string = string.replace('(', '').replace(')', '')

    s = string.strip().split('/')

    bass_string = s[1] if len(s) > 1 else ''
    s = s[0]


    qualifier_search = re.search(r'(add|sus|m|min|man|aug|dim|[0-9])', s)
    if qualifier_search is None:
        note = s
        qualification = ''
    else:
        note = s[:qualifier_search.start()]
        qualification = s[qualifier_search.start():].strip().replace('b', '\u266d').replace('#', '\u266f')

    try:
        index = ABSOLUTE_LOOKUP[note.strip().lower()]
    except KeyError:
        # Invalid note!
        index = None

    try:
        bass_index = ABSOLUTE_LOOKUP[bass_string.strip().lower()]
    except KeyError:
        # Invalid note - no bass
        bass_index = None

    return (index, qualification, bass_index)


def _extract_keyword(keyword, text):
    try:
        return re.search(r'^{}: (.*)'.format(keyword), text, re.IGNORECASE | re.MULTILINE).group(1)
    except AttributeError:
        return None


def song_from_onsong_text(text):
    ret_dict = {}

    # line breaks
    text = text.replace('\r', '')

    # strip comments
    lines = text.split('\n')
    text = '\n'.join([line for line in lines if not line.strip().startswith('#')])

    split = re.split(r'\n[ \t]*\n', text, maxsplit=1)

    header = split[0]
    body = split[1]

    metadata_keywords = [
        'title',
        'artist',
        'author',
        'key',
        'transposedkey',
        'in',
        'capo',
        'tempo',
        'time',
        'duration',
        'book',
        'number',
        'flow',
        'midi',
        'midi-index',
        'keywords',
        'index',
        'copyright',
        'footer',
        'ccli',
        'restrictions',
        'pitch',
        'subdivision',
        'beat',
        'transpose',
        'scene',
    ]

    metadata = {}

    for word in metadata_keywords:
        metadata[word] = _extract_keyword(word, header)

    ret_dict['title'] = metadata.get('title')
    if ret_dict['title'] is None:
        ret_dict['title'] = header.split('\n')[0]

    ret_dict['artist'] = metadata.get('artist')
    if ret_dict['artist'] is None:
        ret_dict['artist'] = metadata.get('author')
    if ret_dict['artist'] is None:
        ret_dict['artist'] = header.split('\n')[1]


    # Extract key
    key_text = metadata.get('key')
    if key_text is None:
        key_text = metadata.get('in')
    if key_text is None:
        try:
            # Extract the first chord of the song (just a guess!)
            key_text = body.split('[')[1].split(']')[0]
        except IndexError:
            # Failing that, it's in C. This shouldn't matter as we've established it has no chords anyway!
            key_text = 'C'

    ret_dict['original_key'] = int(interpret_absolute_chord(key_text)[0])
    ret_dict['raw'] = body

    return ret_dict