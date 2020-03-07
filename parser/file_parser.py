import re


class FileParser:
    @staticmethod
    def _extract_keyword(keyword, text):
        try:
            return re.search(r'^{}: (.*)'.format(keyword), text, re.IGNORECASE).group(1)
        except AttributeError:
            return ''

    def _extract_sections(self, text):
        section_header_re = re.compile(r'^([a-zA-Z0-9 \.\-\+_~#]+):[ \t]*\n', flags=re.MULTILINE)

        sections = []
        remaining_text = text
        while True:
            title = section_header_re.search(remaining_text)

            if title is None:
                sections.append({'section_title': '', 'body': remaining_text})
                break

            remaining_text = remaining_text[title.end():]
            next_break = section_header_re.search(remaining_text)
            if next_break is None:
                sections.append({'section_title': title.group(0).strip(), 'body': remaining_text})
                break
            else:
                sections.append({'section_title': title.group(0).strip(), 'body': remaining_text[:next_break.start()]})

        for section in sections:
            self._parse_section(section)

        return sections

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
            blocks.append({'chord': chord, 'lyric': lyric})
        return blocks

    def _parse_section(self, section):
        section['lines'] = []
        for line in section['body'].split('\n'):
            section['lines'].append(self._parse_line(line))

    def parse(self, text):
        print("Parsing")

        song = {}

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

        for word in metadata_keywords:
            song[word] = self._extract_keyword(word, header)

        if song['title'] == '':
            song['title'] = lines[0]

        if song['artist'] == '':
            song['artist'] = lines[1]

        # Extract key
        if song['key'] == '':
            try:
                song['key'] = body.split('[')[1].split[


        sections = self._extract_sections(body)
        print(sections)

