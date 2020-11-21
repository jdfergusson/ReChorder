from django.core.management.base import BaseCommand
from ...models import Song

import re


class Command(BaseCommand):
    help = 'Updates the verse labelling from "Verse 1:" to "{v1}" format'

    def add_arguments(self, parser):
        parser.add_argument('forreal', nargs='?')

    def handle(self, *args, **options):
        flags = re.IGNORECASE | re.MULTILINE

        if options.get('forreal'):
            "Modifying the database..."
        else:
            "Dry run..."

        for song in Song.objects.all():
            song_content = song.raw
            song_content = re.sub(r"verse:", r"{v1}", song_content, flags=flags)
            song_content = re.sub(r"verse ([0-9]):", r"{v\1}", song_content, flags=flags)

            song_content = re.sub(r"chorus ([0-9]):", r"{c\1}", song_content, flags=flags)
            song_content = re.sub(r"chorus:", r"{c}", song_content, flags=flags)

            song_content = re.sub(r"bridge ([0-9]):", r"{b\1}", song_content, flags=flags)
            song_content = re.sub(r"bridge:", r"{b}", song_content, flags=flags)

            song_content = re.sub(r"pre ?chorus ([0-9]):", r"{p\1}", song_content, flags=flags)
            song_content = re.sub(r"pre ?chorus:", r"{p}", song_content, flags=flags)

            song_content = re.sub(r"intro[a-z]*:", r"{i}", song_content, flags=flags)
            song_content = re.sub(r"(out|end)[a-z]*:", r"{o}", song_content, flags=flags)
            song_content = re.sub(r"(instr|interlude)[a-z]*:", r"{m}", song_content, flags=flags)

            if ":" in song_content:
                print("Colon remaining in {}, ID: {}".format(song.title, song.pk))
                [print("   ", line) for line in song_content.split("\n") if ":" in line]

            if options.get('forreal'):
                song.raw = song_content
                song.save()
