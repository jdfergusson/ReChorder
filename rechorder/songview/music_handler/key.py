from .interpret import interpret_absolute_chord


class Key:
    def __init__(self, text):
        self.index, self.qualification, _ = interpret_absolute_chord(text)

    def __repr__(self):
        return repr({
            'index': self.index,
            'qualification': self.qualification
        })


