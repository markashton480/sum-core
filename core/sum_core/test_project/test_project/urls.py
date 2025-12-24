"""
Name: Test Project URL Configuration
Path: core/sum_core/test_project/test_project/urls.py
Purpose: Minimal URL configuration to expose Wagtail admin and the site root.
Family: Used by test_project when running the development server or checks.
Dependencies: Django, Wagtail
"""

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("forms/", include("sum_core.forms.urls")),
    path("", include("sum_core.ops.urls")),
    path("", include("sum_core.seo.urls")),
    path("", include(wagtail_urls)),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
