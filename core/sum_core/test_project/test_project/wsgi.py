"""
Name: Test Project WSGI
Path: core/sum_core/test_project/test_project/wsgi.py
Purpose: WSGI entry point for the sum_core test project.
Family: Used by Django tooling and deployment-like scenarios during validation.
Dependencies: django.core.wsgi
"""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

application = get_wsgi_application()
