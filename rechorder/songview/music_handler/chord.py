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

CHORD_NAMES = ['A', 'Bb', 'B', 'C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'G#']

class Chord:
    def __init__(self, string, key=None):

        self.key_index = 0 if key is None else key.index

        s = string.strip().split('/')

        bass_string = s[1] if len(s) > 1 else ''
        s = s[0]

        qualifier_search = re.search('(add|sus|m|min|man|aug|dim|[0-9])', s)
        if qualifier_search is None:
            note = s
            self.qualification = ''
        else:
            note = s[:qualifier_search.start()]
            self.qualification = s[qualifier_search.start():].strip()

        try:
            self.index = (ABSOLUTE_LOOKUP[note.strip().lower()] - self.key_index + 12) % 12
        except KeyError:
            # Invalid note!
            self.index = -1

        try:
            self.bass_index = (ABSOLUTE_LOOKUP[bass_string.strip().lower()] - self.key_index + 12) % 12
        except KeyError:
            # Invalid note - no bass
            self.bass_index = None

    def to_string(self, relative_key=None):
        if relative_key is None:
            key_index = self.key_index
        else:
            key_index = relative_key.index

        chord = '{}{}'.format(
            CHORD_NAMES[(self.index + key_index) % 12],
            self.qualification)

        if self.bass_index:
            chord += '/{}'.format(CHORD_NAMES[(self.bass_index + key_index) % 12])

        return chord

    def __str__(self):
        if self.index == -1:
            return ''
        return self.to_string()

    def __repr__(self):
        return repr({
            'index': self.index,
            'qualification': self.qualification,
            'bass_index': self.bass_index
        })