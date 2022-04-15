from django.urls import include, re_path
from django.contrib import admin
from django.views.generic.base import TemplateView

urlpatterns = [
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^', include('rechorder.urls')),
    re_path(r'robots.txt', TemplateView.as_view(template_name="rechorder/robots.txt", content_type="text/plain"))
]
