from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^rechorder/', include('rechorder.urls')),
    url(r'^admin/', admin.site.urls),
]