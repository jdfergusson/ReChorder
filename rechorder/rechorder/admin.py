from django.contrib import admin

from .models import Song, Set, User, ItemInSet

admin.site.register(Song)
admin.site.register(Set)
admin.site.register(User)
admin.site.register(ItemInSet)
