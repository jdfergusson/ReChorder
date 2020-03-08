import re

from .key import Key
from .interpret import interpret_absolute_chord

CHORD_NAMES = ['A', 'Bb', 'B', 'C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'G#']

class Chord:
    def __init__(self, string, key=None):

        # This will link the key to the key object, so that you can have multiple chords with one shared key
        self.key = Key('A') if key is None or key.index is None else key

        index, qualification, bass_index = interpret_absolute_chord(string)

        # Make chord relative to the key
        if index is not None:
            self.index = (index - self.key.index + 12) % 12
        else:
            self.index = None

        self.qualification = qualification

        if bass_index:
            self.bass_index = (bass_index - self.key.index + 12) % 12
        else:
            self.bass_index = None

    def __str__(self):
        if self.index is None:
            return ''

        chord = '{}{}'.format(
            CHORD_NAMES[(self.index + self.key.index) % 12],
            self.qualification)

        if self.bass_index is not None:
            chord += '/{}'.format(CHORD_NAMES[(self.bass_index + self.key.index) % 12])

        return chord

    def __repr__(self):
        return repr({
            'index': self.index,
            'qualification': self.qualification,
            'bass_index': self.bass_index
        })