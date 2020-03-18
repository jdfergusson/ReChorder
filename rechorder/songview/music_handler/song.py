
import re

from .key import Key
from .chord import Chord
from .interpret import interpret_absolute_chord



class Song:
    def __init__(self, text=''):
        if text:
            self.from_text(text)

    def transpose(self, target_key):
        try:
            target_index = int(target_key) % 12
        except ValueError:
            target_index, _, _ = interpret_absolute_chord(target_key)

        if target_index is not None:
            self.key.index = target_index

    @staticmethod
    def _extract_keyword(keyword, text):
        try:
            return re.search(r'^{}: (.*)'.format(keyword), text, re.IGNORECASE | re.MULTILINE).group(1)
        except AttributeError:
            return ''

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
        section = {}
        section['title'] = title

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
            blocks.append({'chord': Chord(chord, self.key), 'lyric': lyric})
        return blocks

    def from_text(self, text):
        # line breaks
        text = text.replace('\r', '')

        # strip comments
        lines = text.split('\n')
        text = '\n'.join([line for line in lines if  not line.strip().startswith('#')])
        lines = text.split('\n')

        split = re.split(r'\n[ \t]*\n', text, maxsplit=1)

        header = split[0]
        body = split[1]

        metadata_keywords = [
            'title',
            'artist',
            'author',
            'key',
            'transposedkey',
            'in',
            'capo',
            'tempo',
            'time',
            'duration',
            'book',
            'number',
            'flow',
            'midi',
            'midi-index',
            'keywords',
            'index',
            'copyright',
            'footer',
            'ccli',
            'restrictions',
            'pitch',
            'subdivision',
            'beat',
            'transpose',
            'scene',
        ]

        metadata = {}

        for word in metadata_keywords:
            metadata[word] = self._extract_keyword(word, header)

        self.title = metadata.pop('title')
        if self.title == '':
            self.title = lines[0]

        self.artist = metadata.pop('artist')
        if self.artist == '':
            self.artist = lines[1]

        # Extract key
        if metadata['key'] == '':
            try:
                # Extract the first chord of the song (just a guess!)
                metadata['key'] = body.split('[')[1].split(']')[0]
            except IndexError:
                # Failing that, it's in C. This shouldn't matter as we've established it has no chords anyway!
                metadata['key'] = 'C'

        # key is the currently displayed key. Modifying that object changes the key of the song as displayed
        self.original_key = Key(metadata['key'])
        self.key = Key(metadata['key'])

        self.sections = self._extract_sections(body)

    def __str__(self):
        return '{} ({})'.format(self.title, self.artist)

    def __repr__(self):
        return repr({
            'title': self.title,
            'artist': self.artist,
            'key': repr(self.key),
            'sections': self.sections
        })
