from django.db import models
from django.urls import reverse
from django.contrib.postgres.fields import JSONField
from django.core.validators import MaxValueValidator, MinValueValidator

import re
import uuid
from .music_handler.chord import Chord
from .music_handler.interpret import interpret_absolute_chord


class Song(models.Model):
    title = models.CharField(max_length=200)
    # TODO: This is an index - maybe the name should reflect this?
    original_key = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(11)]
    )
    artist = models.CharField(max_length=200, null=True)
    raw = models.TextField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._key_index = self.original_key
        self._display_style = 'letters'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('song', args=[str(self.id)])

    ###########################################
    # NON-DATABASE FUNCTIONS
    ###########################################

    def display_in(self, target_key, display_style):
        """
        How to display the song's chords

        :param target_key: Key index as integer or absolute chord string
        :param display_style: Display style for chords
        """
        try:
            target_index = int(target_key) % 12
        except ValueError:
            target_index, _, _ = interpret_absolute_chord(target_key)

        if target_index is not None:
            self._key_index = target_index

        self._display_style = display_style

    def _extract_sections(self, text):
        section_header_re = re.compile(r'^([a-zA-Z0-9 \.\-\+_~#]+):[ \t]*\n', flags=re.MULTILINE)

        sections = []
        remaining_text = text
        while True:
            title = section_header_re.search(remaining_text)

            if title is None:
                sections.append(self._parse_section('', remaining_text))
                break

            remaining_text = remaining_text[title.end():]
            next_break = section_header_re.search(remaining_text)
            if next_break is None:
                sections.append(self._parse_section(title.group(0).strip(), remaining_text))
                break
            else:
                sections.append(self._parse_section(title.group(0).strip(), remaining_text[:next_break.start()]))

        return sections

    def _parse_section(self, title, text):
        section = {'title': title}

        section['lines'] = []
        for line in text.split('\n'):
            # Gets rid of extra line breaks
            if line.strip() != '':
                section['lines'].append(self._parse_line(line))

        return section

    def _parse_line(self, line):
        blocks = []
        a = line.split('[')
        for block in a:
            k = block.split(']')
            if len(k) > 1:
                chord = k[0]
                lyric = k[1]
            else:
                chord = ''
                lyric = block
            if not lyric.strip() and not chord.strip():
                continue
            lyric = lyric.replace(' ', '&nbsp;').replace('\n','')
            blocks.append({'chord': Chord(chord, self, self._display_style), 'lyric': lyric})
        return blocks

    @property
    def sections(self):
        return self._extract_sections(self.raw)

    @property
    def key(self):
        return self._key_index


class Set(models.Model):
    song_list = JSONField(null=False, default=list)
    last_updated = models.DateTimeField(auto_now=True)
    # Owner is a UUID, but the UUID django field has a bug, so we'll just store it as a string
    owner = models.CharField(max_length=36, default='')
    name = models.CharField(max_length=200, default='')
    is_public = models.BooleanField(default=True)
    is_protected = models.BooleanField(default=False)

    def save(self, *args, **kwargs):

        # Let's make sure the set has a name while we're here
        if not self.name.strip():
            self.name = "Unnamed set"

        super().save(*args, **kwargs)

    def check_list_integrity(self):
        """
        This is basically a hack for not having implemented a properly relational song list
        """
        self.song_list = [song for song in self.song_list if Song.objects.filter(pk=song['id']).exists()]
        # Don't update the has_changed_count here
        super().save()

    def __str__(self):
        return '"{}" containing {} songs'.format(self.name, len(self.song_list))


class Beam(models.Model):
    set = models.ForeignKey(Set, null=False, on_delete=models.CASCADE)
    last_updated = models.DateTimeField(auto_now=True)
    # Owner is a UUID, but the UUID django field has a bug, so we'll just store it as a string
    owner = models.CharField(max_length=36, default='')
    current_song_index = models.IntegerField(null=True, default=None)
    has_changed_count = models.IntegerField(default=0)
    beamer_device_name = models.CharField(max_length=200, default='Unknown')

    def save(self, *args, **kwargs):
        if self.current_song_index is not None:
            if not 0 <= self.current_song_index < len(self.set.song_list):
                self.current_song_index = None
        self.has_changed_count = self.has_changed_count + 1 % 10000

        super().save(*args, **kwargs)