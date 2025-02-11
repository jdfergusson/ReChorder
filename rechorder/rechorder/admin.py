from django.contrib import admin

from .models import Song, Set, User, ItemInSet, Tag

admin.site.register(Song)
admin.site.register(Set)
admin.site.register(User)
admin.site.register(ItemInSet)
admin.site.register(Tag)
