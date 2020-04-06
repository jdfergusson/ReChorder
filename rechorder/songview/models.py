from django.db import models
from django.urls import reverse
from django.contrib.postgres.fields import JSONField

class Song(models.Model):
    title = models.CharField(max_length=200)
    raw = models.TextField()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('song', args=[str(self.id)])


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
