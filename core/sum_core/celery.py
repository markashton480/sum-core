"""
Name: Celery app configuration
Path: core/sum_core/celery.py
Purpose: Configure Celery for async task processing in sum_core.
Family: Leads, integrations, async processing.
Dependencies: Celery, Django settings.
"""

from __future__ import annotations

from celery import Celery

# Note: DJANGO_SETTINGS_MODULE must be configured by the client project before
# importing this module. This is typically done in the client's celery.py or
# when starting the Celery worker (e.g., `celery -A myproject worker`).
# We do NOT set a default here to avoid coupling to test_project.

app = Celery("sum_core")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery connectivity."""
    print(f"Request: {self.request!r}")
