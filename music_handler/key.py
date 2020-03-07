from .chord import Chord


class Key:
    def __init__(self, text):
        chord = Chord(text)
        self.index = chord.index
        self.qualification = chord.qualification

