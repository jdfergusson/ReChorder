# Generated by Django 5.1.6 on 2025-03-17 17:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rechorder', '0019_tag_song_tags'),
    ]

    operations = [
        migrations.AddField(
            model_name='set',
            name='collaborators',
            field=models.ManyToManyField(to='rechorder.user'),
        ),
    ]
