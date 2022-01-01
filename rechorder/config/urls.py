from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic.base import TemplateView

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^', include('rechorder.urls')),
    url(r'robots.txt', TemplateView.as_view(template_name="rechorder/robots.txt", content_type="text/plain"))
]