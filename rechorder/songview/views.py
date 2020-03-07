from django.shortcuts import render
from songview.music_handler.song import Song as MhSong

from .models import Song

dummy_song = '''Title: Come, Now is the Time to Worship
Artist: Brian Doerkson
Copyright: 1998 Vineyard Songs
Key: [D]
Original Key: D
Notes:


Verse 1:
[D]Come, now is the time to [Em/D]wors[D]hip,
[A]Come, now is the time to [Em]give your [G]heart

[D]Come, just as you are to [Em/D]wors[D]hip,
[A]Come, just as you are be[Em]fore your [G]god, [D]Come

Chorus:
[G]One day every tongue will con[D]fess you are God,
[G]One day every knee will [D]bow

[G]Still the greatest treasure re[Bm]mains for those,
Who [Em7]gladly choose you [A]now'''


def index(request):
    s = MhSong(dummy_song)

    return render(request, 'songview/song.html', {'song': s})

def songs(request):
    songs = Song.objects.all()
    return render(request, 'songview/songs.html', {'songs': songs})

def song(request, song_id):
    song = MhSong(Song.objects.get(pk=song_id).raw)
    return render(request, 'songview/song.html', {'song': song})


