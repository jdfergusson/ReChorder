# Generated by Django 4.0.6 on 2023-06-06 20:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rechorder', '0014_user_alter_set_song_list'),
    ]

    operations = [
        migrations.AddField(
            model_name='song',
            name='ccli_number',
            field=models.IntegerField(default=None, null=True),
        ),
    ]
