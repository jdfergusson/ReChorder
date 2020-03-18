from django.db import models
from django.urls import reverse

class Song(models.Model):
    title = models.CharField(max_length=200)
    raw = models.TextField()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('song', args=[str(self.id)])