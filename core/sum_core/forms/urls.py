"""
Name: Form URL configuration
Path: core/sum_core/forms/urls.py
Purpose: URL patterns for form submission endpoint.
Family: Forms, Leads.
Dependencies: Django URL routing.
"""

from __future__ import annotations

from django.urls import path
from sum_core.forms.views import form_submission_view

app_name = "sum_core_forms"

urlpatterns = [
    path("submit/", form_submission_view, name="form_submit"),
]
