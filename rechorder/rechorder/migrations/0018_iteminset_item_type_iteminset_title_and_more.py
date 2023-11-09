# Generated by Django 4.0.6 on 2023-11-07 17:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rechorder', '0017_remove_beam_current_song_index_remove_beam_set_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='iteminset',
            name='item_type',
            field=models.IntegerField(choices=[(1, 'Song'), (2, 'Text')], default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='iteminset',
            name='title',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='iteminset',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='iteminset',
            name='song',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rechorder.song'),
        ),
        migrations.AlterField(
            model_name='iteminset',
            name='sounding_key_index',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]