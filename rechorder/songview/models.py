from django.db import models
from django.urls import reverse


class Song(models.Model):
    title = models.CharField(max_length=200)
    raw = models.TextField()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('song', args=[str(self.id)])


class BeamMaster(models.Model):
    last_updated = models.DateTimeField(auto_now=True)
    current_song = models.ForeignKey(Song, null=True, on_delete=models.SET_NULL, default=None)
    current_key_index = models.IntegerField(default=-1)
    has_changed_count = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        self.has_changed_count = self.has_changed_count + 1 % 10000
        super().save(*args, **kwargs)
