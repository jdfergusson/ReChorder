from django.db import models
from django.urls import reverse
from django.contrib.postgres.fields import JSONField
from django.core.validators import MaxValueValidator, MinValueValidator

import re
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

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('song', args=[str(self.id)])

    ###########################################
    # NON-DATABASE FUNCTIONS
    ###########################################

    def transpose(self, target_key):
        """
        Sets the target key for the song

        :param target_key: Key index as integer or absolute chord string
        """
        try:
            target_index = int(target_key) % 12
        except ValueError:
            target_index, _, _ = interpret_absolute_chord(target_key)

        if target_index is not None:
            self._key_index = target_index

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
            lyric = lyric.replace(' ', '&nbsp;').replace('\n','')
            blocks.append({'chord': Chord(chord, self), 'lyric': lyric})
        return blocks

    @property
    def sections(self):
        return self._extract_sections(self.raw)

    @property
    def key(self):
        return self._key_index


class Set(models.Model):
    song_list = JSONField(null=True)
    last_updated = models.DateTimeField(auto_now=True)
    beamed_song_index = models.IntegerField(null=True, default=None)
    has_changed_count = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.beamed_song_index is not None:
            if not 0 <= self.beamed_song_index < len(self.song_list):
                self.beamed_song_index = None
        self.has_changed_count = self.has_changed_count + 1 % 10000
        super().save(*args, **kwargs)
