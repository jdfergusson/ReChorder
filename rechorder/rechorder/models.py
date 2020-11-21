from django.db import models
from django.urls import reverse
from django.contrib.postgres.fields import JSONField
from django.core.validators import MaxValueValidator, MinValueValidator

from xml.etree import ElementTree
from xml.dom import minidom

import re
from .music_handler.chord import Chord
from .music_handler.interpret import interpret_absolute_chord

SECTION_NAMES = {
    'v': 'Verse',
    'c': 'Chorus',
    'b': 'Bridge',
    'p': 'Prechorus',
    'm': 'Instrumental',
    'i': 'Intro',
    'o': 'Ending',
}


class Song(models.Model):
    title = models.CharField(max_length=200)
    # TODO: This is an index - maybe the name should reflect this?
    original_key = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(11)]
    )
    artist = models.CharField(max_length=200, null=True)
    key_notes = models.CharField(max_length=200, null=False, default="")
    verse_order = models.CharField(max_length=200, null=False, default="")
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

    def to_xml(self):
        _song = ElementTree.Element('song', {
            'xmlns': 'http://openlyrics.info/namespace/2009/song',
            'version': '0.9',
        })

        # Properties
        _properties = ElementTree.SubElement(_song, 'properties')
        _titles = ElementTree.SubElement(_properties, 'titles')
        _title = ElementTree.SubElement(_titles, 'title')
        _title.text = self.title

        _authors = ElementTree.SubElement(_properties, 'authors')
        authors = re.split(r'[;,&\+]', self.artist)
        print(authors)
        for author in authors:
            _author = ElementTree.SubElement(_authors, 'author')
            _author.text = author.strip()

        if self.verse_order.strip():
            _verse_order = ElementTree.SubElement(_properties, 'verseOrder')
            _verse_order.text = self.verse_order

        # Lyrics
        _lyrics = ElementTree.SubElement(_song, 'lyrics')
        for section in self.sections:
            if section['is_lyrical']:
                _verse = ElementTree.SubElement(_lyrics, 'verse', {
                    'name': '{}{}'.format(section['code'], section['number'])
                })
                for line in section['lines']:
                    line = ''.join([i['lyric'] for i in line])
                    _lines = ElementTree.SubElement(_verse, 'lines')
                    _lines.text = line.replace('&nbsp;', ' ').strip()

        rough_string = ElementTree.tostring(_song)
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent='  ')

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

    @staticmethod
    def _extract_title(search):
        '''
        Returns the section title details

        :param search: Regex search to use to extract the details
        :return: (
            Section title, e.g. "Verse 2:",
            Details of the section
        )
        '''
        section_code = search.group(1).lower()
        number = search.group(2)
        is_lyrical = not search.group(3) == '!'

        details = {
            'code': section_code,
            'number': number,
            'is_lyrical': is_lyrical,
        }

        return (
            '{} {}'.format(
                SECTION_NAMES.get(section_code, 'Section'),
                number,
            ).strip() + ':',
            details,
        )

    def _extract_sections(self, text):
        section_header_re = re.compile(r'^\{([vcbmiop])([0-9]*)(\!?)\}', flags=re.IGNORECASE|re.MULTILINE)

        sections = []
        remaining_text = text
        while True:
            title_search = section_header_re.search(remaining_text)

            if title_search is None:
                sections.append(self._parse_section('', remaining_text))
                break

            title, section_details = self._extract_title(title_search)

            remaining_text = remaining_text[title_search.end():]
            next_break = section_header_re.search(remaining_text)
            if next_break is None:
                sections.append(self._parse_section(title, section_details, remaining_text))
                break
            else:
                sections.append(self._parse_section(
                    title,
                    section_details,
                    remaining_text[:next_break.start()]
                ))

        return sections

    def _parse_section(self, title, details, text):
        section = {
            'title': title,
            **details,
        }

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