from parser.file_parser import FileParser

dummy_song = '''Title: Amazing Grace
Artist:
Key: [G]
Original Key: G
Notes: CANT Key E
Book: Retreat 2014, Hymns

Chorus 1:
Am[G]azing Gr[G7]ace, how [C]sweet the so[G]und,
That s[G]aved a wr[G7]etch like [D]me.
I [G]once was [G7]lost, but [C]now im [G]found,
Was bl[Em]ind, but [D]now I [G]see.

Chorus 2:
Twas [G]grace that [G7]taught my [C]heart to [G]fear,
And [G]grace my [G7]fears reli[D]eved.
How pr[G]ecious [G7]did that [C]grace app[G]ear,
The [Em]hour I [D]first bel[G]ieved.'''

def test_file_parser():
    fp = FileParser()
    fp.parse(dummy_song)