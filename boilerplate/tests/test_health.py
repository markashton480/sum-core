"""
Integration tests for the /health/ endpoint.

This test verifies that sum_core endpoints are correctly wired into this client project.
It validates the actual health check contract without mocking core internals.
"""
from __future__ import annotations

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_endpoint_returns_200_with_json(client) -> None:
    """
    Integration test: /health/ returns HTTP 200 with JSON in the healthy baseline.

    This test proves that the client project correctly wires the sum_core ops endpoint
    and validates the real health check contract (ok/degraded=200, unhealthy=503).
    """
    response = client.get(reverse("health_check"))

    # In the baseline/healthy state, expect HTTP 200
    assert response.status_code == 200

    # Response should be JSON
    data = response.json()
    assert isinstance(data, dict), "Health endpoint must return JSON object"


@pytest.mark.django_db
def test_health_endpoint_has_required_keys(client) -> None:
    """
    Integration test: /health/ JSON response has required structure.

    Verifies the endpoint returns 'status' and 'checks' keys without asserting
    exact check ordering or exhaustive payload contents.
    """
    response = client.get(reverse("health_check"))
    data = response.json()

    # Verify required keys are present
    assert "status" in data, "Response JSON must have 'status' key"
    assert "checks" in data, "Response JSON must have 'checks' key"

    # Verify status is a valid string (don't hardcode exact value)
    assert isinstance(data["status"], str), "'status' must be a string"

    # Verify checks is a dict (don't assert specific checks or ordering)
    assert isinstance(data["checks"], dict), "'checks' must be a dictionary"
