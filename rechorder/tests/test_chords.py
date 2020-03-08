from ..songview.music_handler.chord import Chord
from ..songview.music_handler.key import Key


def test_chord_init():
    c = Chord('A')
    assert(c.index == 0)
    assert(c.qualification == '')
    assert(c.bass_index == None)

    c = Chord('Bb')
    assert(c.index == 1)

    c = Chord('B#')
    assert(c.index == 3)

    c = Chord('B# ')
    assert(c.index == 3)

    c = Chord('B# sus 4')
    assert(c.index == 3)
    assert(c.qualification == 'sus 4')

    c = Chord('Bbsus4')
    assert(c.index == 1)
    assert(c.qualification == 'sus4')


    c = Chord('Bbsus4add9')
    assert(c.index == 1)
    assert(c.qualification == 'sus4add9')

    c = Chord('L')
    assert(c.index == None)

    c = Chord('Bb/G')
    assert(c.index == 1)
    assert(c.qualification == '')
    assert(c.bass_index == 10)

    c = Chord('Bbm/G')
    assert(c.index == 1)
    assert(c.qualification == 'm')
    assert(c.bass_index == 10)

    # Try some different keys
    c = Chord('B# ', key=Key('C'))
    assert(c.index == 0)

    c = Chord('B ', key=Key('C'))
    assert (c.index == 11)

    c = Chord('B ', key=Key('G'))
    assert (c.index == 4)
