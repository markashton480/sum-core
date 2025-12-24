"""
WSGI application entry point.

Replace 'project_name' with your actual project name after copying.
For production, ensure DJANGO_SETTINGS_MODULE points to production settings.
"""
from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_name.settings.local")

application = get_wsgi_application()
