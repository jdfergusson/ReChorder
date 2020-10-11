from .interpret import interpret_absolute_chord

CHORD_NAMES_BASE = ['A', 'B\u266d', 'B', 'C', 'C\u266f', 'D', 'E\u266d', 'E', 'F', 'F\u266f', 'G', 'G\u266f']
CHORD_NAMES_SLIGHTLY_FLAT = ['A', 'B\u266d', 'B', 'C', 'C\u266f', 'D', 'E\u266d', 'E', 'F', 'F\u266f', 'G', 'A\u266d']
CHORD_NAMES_SHARPS = ['A', 'A\u266f', 'B', 'C', 'C\u266f', 'D', 'D\u266f', 'E', 'F', 'F\u266f', 'G', 'G\u266f']
CHORD_NAMES_FLATS = ['A', 'B\u266d', 'B', 'C', 'D\u266d', 'D', 'E\u266d', 'E', 'F', 'G\u266d', 'G', 'A\u266d']

# This clearly looses quite a bit of information, doubling up chords in the way that it does.
# However, to handle major and minor keys without having that information, this is a (massive)
# compromise. That said, if you're using numbers, it's likely that you're just using basic chords.
CHORD_NAME_NUMBERS = ['1', '\u266d2', '2', '3', '3', '4', '\u266d5', '5', '6', '6', '7', '7']

# This is a rough attempt at improving the key choice. Is a key traditionally though of in flats or sharps?
# Sadly we're assuming here that the key is major. Definitely room for improvement
KEY_NAMES_LOOKUP = [
    # A major: 3#, A minor, none
    CHORD_NAMES_BASE,
    # Bb major: 2b, Bb minor: 5b, A# minor 7#,
    CHORD_NAMES_FLATS,
    # B major: 5#. B minor: 2#
    CHORD_NAMES_SHARPS,
    # C major: none, C minor: 3b
    CHORD_NAMES_SLIGHTLY_FLAT,
    # C# major: 7#, C# minor: 4#, Db minor 5b,
    CHORD_NAMES_SHARPS,
    # D major: 2#, D minor: 1 flat
    CHORD_NAMES_BASE,
    # Eb major: 3b, Eb minor: 6b
    CHORD_NAMES_FLATS,
    # E major: 4#, E minor: 1#
    CHORD_NAMES_SHARPS,
    # F major: 1b, F minor: 4b
    CHORD_NAMES_FLATS,
    # F# major: 6#, F# minor: 3#, Gb major: 6b
    CHORD_NAMES_SHARPS,
    # G major: 1#, G minor: 2b
    CHORD_NAMES_SLIGHTLY_FLAT,
    # Ab major: 4b, Ab minor, 7b, G# minor 5#
    CHORD_NAMES_FLATS,
]

class Chord:
    def __init__(self, string, key_ref=None, display_style='letters'):
        """
        :param string: String that indicates the chord
        :param key_ref: Object with a "key" and "original_key" properties that returns an integer of the key
        """

        self._key_ref = key_ref
        self._display_style = display_style

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

    @property
    def id(self):
        if self.index is None:
            return ''

        if self._display_style == 'numbers':
            return CHORD_NAME_NUMBERS[self.index]
        else:
            return KEY_NAMES_LOOKUP[self._key_ref.key][(self.index + self._key_index) % 12]

    @property
    def qualifiers(self):
        if self.index is None:
            return ''

        qualifiers = self.qualification

        if self.bass_index is not None:
            if self._display_style == 'numbers':
                qualifiers += '/{}'.format(CHORD_NAME_NUMBERS[self.bass_index])
            else:
                qualifiers += '/{}'.format(
                    KEY_NAMES_LOOKUP[self._key_ref.key][(self.bass_index + self._key_index) % 12]
                )

        return qualifiers

    def __str__(self):
        if self.index is None:
            return ''

        return '{}{}'.format(self.id, self.qualifiers)
        return chord

    def __repr__(self):
        return repr({
            'index': self.index,
            'qualification': self.qualification,
            'bass_index': self.bass_index
        })