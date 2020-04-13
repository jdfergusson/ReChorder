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

    s = string.strip().split('/')

    bass_string = s[1] if len(s) > 1 else ''
    s = s[0]

    qualifier_search = re.search('(add|sus|m|min|man|aug|dim|[0-9])', s)
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