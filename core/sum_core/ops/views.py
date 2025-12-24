from django.http import JsonResponse
from django.views import View

from .health import get_health_status


class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        health_data = get_health_status()
        # Contract: only "unhealthy" is a hard failure (HTTP 503). "degraded" stays 200
        # so uptime monitors don't page on non-critical dependency outages (e.g. Celery).
        status_code = 503 if health_data.get("status") == "unhealthy" else 200
        return JsonResponse(health_data, status=status_code)
