# Generated by Django 3.0.4 on 2020-04-06 12:05

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rechorder', '0002_beammaster'),
    ]

    operations = [
        migrations.CreateModel(
            name='Set',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('song_list', django.contrib.postgres.fields.jsonb.JSONField(null=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('beamed_song_index', models.IntegerField(default=None, null=True)),
                ('has_changed_count', models.IntegerField(default=0)),
            ],
        ),
        migrations.DeleteModel(
            name='BeamMaster',
        ),
    ]
