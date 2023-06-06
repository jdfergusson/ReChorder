from django.db import models
from django.urls import reverse
from django.db.models import JSONField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

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
    created_at = models.DateTimeField(auto_now_add=True)
    raw = models.TextField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._key_index = self.original_key
        self._display_style = 'letters'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('song', args=[str(self.id)])

    def save(self, *args, **kwargs):
        self.verse_order = self.verse_order.strip().lower().replace(',', '')

        # Remove double blank lines from text
        self.raw = re.sub(r"^([\s]*\n){2,}", "\n", self.raw, flags=re.MULTILINE)

        super().save(*args, **kwargs)

    ###########################################
    # NON-DATABASE FUNCTIONS
    ###########################################

    def check_verse_order(self):
        problems = []

        if self.verse_order == "":
            problems.append("Verse order empty")

        verses_in_order = {}

        for i in self.verse_order.split(' '):
            verses_in_order[i] = 0

        for i in re.findall(r'\{[a-zA-Z0-9]+\}', self.raw.lower()):
            section = i[1:-1]
            if section not in verses_in_order:
                problems.append("Section '{}' in song but not in verse order.".format(section))
            else:
                verses_in_order[section] += 1
            if re.sub(r'[0-9]+', '', section) not in SECTION_NAMES:
                problems.append("Section '{}' not a valid section type (see syntax help for full list).".format(section))

        for i in re.findall(r'\{[a-zA-Z0-9]+!\}', self.raw.lower()):
            section = i[1:-2]
            if section in verses_in_order:
                verses_in_order[section] += 1

        for i in verses_in_order:
            if verses_in_order[i] == 0:
                problems.append("Section '{}' found in the verse order but doesn't exist in the song".format(i))

        return problems

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
        for author in authors:
            _author = ElementTree.SubElement(_authors, 'author')
            _author.text = author.strip()

        if self.verse_order.strip():
            _verse_order = ElementTree.SubElement(_properties, 'verseOrder')
            _verse_order.text = self.verse_order

        # Lyrics
        _lyrics = ElementTree.SubElement(_song, 'lyrics')
        for section in self.sections:
            _lines = None
            if section['is_lyrical'] and section['subsections']:
                _verse = ElementTree.SubElement(_lyrics, 'verse', {
                    'name': section['id'],
                })
                for subsection in section['subsections']:
                    # Set break=optional (can we make it mandatory?)
                    for long_line in subsection:
                        for line in long_line:
                            line = ''.join([i['lyric'] for i in line])
                            line = line.replace('&nbsp;', ' ').strip()
                            line = re.sub(r' {2,}', ' ', line)
                            if line.strip():
                                _lines = ElementTree.SubElement(_verse, 'lines')
                                _lines.text = line
                    if _lines is not None:
                        _lines.set("break", "optional")
                # For some reason, casting an element to boolean will reveal whether it has any children.
                # This will remove a verse that has no lyrics in
                if not _verse:
                    _lyrics.remove(_verse)
            if _lines is not None:
                _lines.attrib.pop("break")

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
        if search is None:
            return ('', {'code': 'c', 'number': '', 'is_lyrical': True})

        section_code = search.group(1).lower()
        number = search.group(2)
        is_lyrical = not search.group(3) == '!'

        details = {
            'code': section_code,
            'number': number,
            'is_lyrical': is_lyrical,
            'id': '{}{}'.format(section_code, number),
        }

        return (
            '{} {}'.format(
                SECTION_NAMES.get(section_code, 'Section'),
                number,
            ).strip() + ':',
            details,
        )

    def _extract_sections(self, text):
        section_header_re = re.compile(r'\{([vcbmiop])([0-9]*)(\!?)\}', flags=re.IGNORECASE|re.MULTILINE)
        sections = []
        remaining_text = text
        while True:
            title_search = section_header_re.search(remaining_text)

            title, section_details = self._extract_title(title_search)

            if title_search is None:
                sections.append(self._parse_section('', section_details, remaining_text))
                break

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

        # Section contains three levels of array:
        # Section [
        #   subsection [
        #       long_line [
        #           short_line [
        # ] ] ] ]

        text = text.strip()

        section['subsections'] = []
        for subsection_text in text.split('\n\n'):
            subsection = []
            for long_line_text in subsection_text.split('\n'):
                long_line = []
                for small_line in long_line_text.split("\\"):
                    long_line.append(self._parse_small_line(small_line))
                subsection.append(long_line)
            section['subsections'].append(subsection)

        return section

    def _parse_small_line(self, line):
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
    def expanded_sections(self):
        sections = self._extract_sections(self.raw)

        non_lyrical_sections = {}
        for i in range(len(sections)):
            if not sections[i]['is_lyrical']:
                non_lyrical_sections[sections[i]['id']] = {
                    'prev': sections[i - 1]['id'] if i > 0 else None,
                    'next': sections[i + 1]['id'] if i < len(sections) - 1 else None,
                }

        section_order = self.verse_order.split(" ")
        intros = [i for i in non_lyrical_sections if i.startswith("i")]
        outros = [i for i in non_lyrical_sections if i.startswith("o")]
        section_order = intros + section_order + outros

        non_lyrical_sections = {i: non_lyrical_sections[i] for i in non_lyrical_sections if not (i.startswith("i") or i.startswith("o"))}

        new_section_order = []
        for section in section_order:
            for i in non_lyrical_sections:
                if non_lyrical_sections[i]['prev'] is None and non_lyrical_sections[i]['next'] == section:
                    new_section_order.append(i)
            new_section_order.append(section)
            for i in non_lyrical_sections:
                if non_lyrical_sections[i]['prev'] == section:
                    new_section_order.append(i)


        try:
            sections = {i['id']: i for i in sections}
            sections = [sections[i] for i in new_section_order if i in sections]
        except Exception:
            sections = ['Error rendering song - check the verse order is okay']

        return sections

    @property
    def key(self):
        return self._key_index


class Set(models.Model):
    song_list = JSONField(null=False, default=list)
    last_updated = models.DateTimeField(auto_now=True)
    # Owner is a UUID, but the UUID django field has a bug, so we'll just store it as a string
    # The UUID may match an actual User object, or it may just point to someone's local session.
    owner = models.CharField(max_length=36, default='')
    name = models.CharField(max_length=200, default='')
    is_public = models.BooleanField(default=True)
    is_protected = models.BooleanField(default=False)

    def save(self, *args, **kwargs):

        # Let's make sure the set has a name while we're here
        if not self.name.strip():
            self.name = "Unnamed set"

        super().save(*args, **kwargs)

    @property
    def user(self):
        try:
            return User.objects.get(uuid=self.owner)
        except User.DoesNotExist:
            return None

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


class User(models.Model):
    uuid = models.CharField(max_length=36, null=False, unique=True)
    name = models.CharField(max_length=64, null=False, unique=True)
    password = models.CharField(max_length=256, null=False)
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def set_password(self, plain_text_password):
        self.password = make_password(plain_text_password)

    def check_password(self, plain_text_attempt):
        return check_password(plain_text_attempt, self.password)

    @property
    def sets(self):
        return Set.objects.filter(owner=self.uuid)
