CHORD_LOOKUP = {
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
    def __init__(self, string):
