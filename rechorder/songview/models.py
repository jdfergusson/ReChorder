from django.db import models

class Song(models.Model):
    title = models.CharField(max_length=200)
    raw = models.TextField()

    def __str__(self):
        return self.title