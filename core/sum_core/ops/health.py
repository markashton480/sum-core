"""
Name: health
Path: core/sum_core/ops/health.py
Purpose: Runtime health checks for monitoring (/health/).
Family: Ops/Monitoring (Milestone 4)
Dependencies: Django DB connection, cache backend, optional Celery app config

Health contract (authoritative):
- Overall `status` is one of: `ok`, `degraded`, `unhealthy`
- HTTP mapping (implemented in `sum_core.ops.views.HealthCheckView`):
  - `ok`        -> 200
  - `degraded`  -> 200 (service is up but some non-critical dependency is down)
  - `unhealthy` -> 503 (service cannot safely operate)

Severity rules (current baseline):
- Critical checks: DB, cache. If either fails => overall `unhealthy`.
- Non-critical check: Celery. If it fails (and is configured) => overall `degraded`.
"""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from typing import Any, cast

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from kombu import Connection


@dataclass
class CheckResult:
    status: str  # "ok" or "fail"
    latency_ms: float | None = None
    detail: str | None = None


def measure_latency(func) -> CheckResult:
    start = time.perf_counter()
    try:
        func()
        status = "ok"
        detail = None
    except Exception as e:
        status = "fail"
        detail = str(e)
    end = time.perf_counter()
    latency = (end - start) * 1000.0
    return CheckResult(
        status=status, latency_ms=latency if status == "ok" else None, detail=detail
    )


def check_db() -> CheckResult:
    def _run():
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

    return measure_latency(_run)


def check_cache() -> CheckResult:
    def _run():
        test_key = "health_check_probe"
        cache.set(test_key, 1, timeout=5)
        val = cache.get(test_key)
        if val != 1:
            raise Exception("Cache set/get mismatch")
        cache.delete(test_key)

    return measure_latency(_run)


def check_celery() -> CheckResult:
    # Check if Celery is required/enabled. Default to assuming it is part of the stack
    # unless explicitly disabled or if we want to be linient in dev.
    # The requirement says: "If celery is optional in local dev... treat it as required in production-like settings"
    # For now, we will attempt checks if a broker is configured.

    broker_url = getattr(settings, "CELERY_BROKER_URL", None)
    if not broker_url:
        return CheckResult(status="ok", detail="Not configured (skipped)")

    try:
        # Prefer a lightweight broker reachability check.
        # This intentionally checks "broker is reachable", not "workers are running".
        #
        # Use kombu Connection directly with the configured broker URL so behaviour is
        # deterministic even if a Celery app hasn't been fully configured/imported.
        conn = Connection(broker_url, connect_timeout=0.5)
        conn.connect()
        conn.release()
        return CheckResult(status="ok")
    except Exception as e:
        return CheckResult(status="fail", detail=str(e))


def get_health_status() -> dict[str, Any]:
    checks = {
        "db": check_db(),
        "cache": check_cache(),
        "celery": check_celery(),
    }

    # Determine overall status.
    # NOTE: checks expose "ok"/"fail", while overall status uses the broader contract:
    # ok/degraded/unhealthy (see module docstring).
    critical_checks = ("db", "cache")
    non_critical_checks = ("celery",)

    is_unhealthy = any(checks[name].status == "fail" for name in critical_checks)
    is_degraded = any(checks[name].status == "fail" for name in non_critical_checks)

    overall_status = (
        "unhealthy" if is_unhealthy else "degraded" if is_degraded else "ok"
    )

    # Format response
    response = {
        "status": overall_status,
        "version": {
            "git_sha": os.environ.get("GIT_SHA", "unknown"),
            "build": os.environ.get("BUILD_ID", "unknown"),
        },
        "checks": {k: asdict(v) for k, v in checks.items()},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Clean up empty optional fields for cleaner JSON
    checks_data = cast(dict[str, dict[str, Any]], response["checks"])
    for check_data in checks_data.values():
        if check_data.get("detail") is None:
            del check_data["detail"]
        if check_data.get("latency_ms") is None:
            del check_data["latency_ms"]

    return response
