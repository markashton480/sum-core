"""
Name: SEO URLs
Path: core/sum_core/seo/urls.py
Purpose: URL routing for SEO endpoints (sitemap.xml, robots.txt).
Family: Technical SEO (M4-006)
Dependencies: Django, sitemap.py, robots.py
"""

from __future__ import annotations

from django.urls import path
from sum_core.seo.robots import robots_view
from sum_core.seo.sitemap import sitemap_view

app_name = "seo"

urlpatterns = [
    path("sitemap.xml", sitemap_view, name="sitemap"),
    path("robots.txt", robots_view, name="robots"),
]
