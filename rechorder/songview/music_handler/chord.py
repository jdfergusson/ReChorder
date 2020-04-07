from .interpret import interpret_absolute_chord

CHORD_NAMES = ['A', 'Bb', 'B', 'C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'G#']


class Chord:
    def __init__(self, string, key_ref=None):
        """
        :param string: String that indicates the chord
        :param song: Object with a "key" and "original_key" properties that returns an integer of the key
        """

        self._key_ref = key_ref

        index, qualification, bass_index = interpret_absolute_chord(string)

        # Make chord relative to the key
        if index is not None:
            self.index = (index - self._original_key_index + 12) % 12
        else:
            self.index = None

        self.qualification = qualification

        if bass_index:
            self.bass_index = (bass_index - self._original_key_index + 12) % 12
        else:
            self.bass_index = None

    @property
    def _key_index(self):
        return 0 if self._key_ref is None else self._key_ref.key

    @property
    def _original_key_index(self):
        return 0 if self._key_ref is None else self._key_ref.original_key

    def __str__(self):
        if self.index is None:
            return ''

        chord = '{}{}'.format(
            CHORD_NAMES[(self.index + self._key_index) % 12],
            self.qualification)

        if self.bass_index is not None:
            chord += '/{}'.format(CHORD_NAMES[(self.bass_index + self._key_index) % 12])

        return chord

    def __repr__(self):
        return repr({
            'index': self.index,
            'qualification': self.qualification,
            'bass_index': self.bass_index
        })