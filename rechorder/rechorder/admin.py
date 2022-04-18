from django.contrib import admin

from .models import Song, Set, User

admin.site.register(Song)
admin.site.register(Set)
admin.site.register(User)
