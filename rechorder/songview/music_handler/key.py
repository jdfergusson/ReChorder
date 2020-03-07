from .chord import Chord


class Key:
    def __init__(self, text):
        chord = Chord(text)
        self.index = chord.index
        self.qualification = chord.qualification

    def __repr__(self):
        return repr({
            'index': self.index,
            'qualification': self.qualification
        })


