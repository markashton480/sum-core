"""
Name: Form spam protection and configuration services
Path: core/sum_core/forms/services.py
Purpose: Spam protection checks (honeypot, rate limiting, timing) and configuration retrieval.
Family: Forms, Leads, Spam Protection.
Dependencies: Django cache, FormConfiguration model, Wagtail Site.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass
from typing import cast

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest
from sum_core.forms.models import FormConfiguration
from sum_core.ops.request_utils import get_client_ip as request_get_client_ip
from wagtail.models import Site

# Time token settings
TIME_TOKEN_LIFETIME_SECONDS = 3600  # 1 hour max validity
RATE_LIMIT_WINDOW_SECONDS = 3600
logger = logging.getLogger(__name__)


@dataclass
class SpamCheckResult:
    """Result of spam protection checks."""

    is_spam: bool
    reason: str = ""
    should_rate_limit: bool = False  # True if rate limit exceeded


def get_form_config(site: Site) -> FormConfiguration:
    """
    Get FormConfiguration for a site, creating with defaults if needed.

    Args:
        site: Wagtail Site instance

    Returns:
        FormConfiguration for the site
    """
    from sum_core.forms.models import FormConfiguration

    return FormConfiguration.get_for_site(site)


def get_rate_limit_cache_key(ip_address: str, site_id: int) -> str:
    """
    Generate a cache key for rate limiting.

    Keys are site-scoped to allow different limits per site.
    """
    return f"form_rate_limit:{site_id}:{ip_address}"


def check_honeypot(
    form_data: dict,
    honeypot_field_name: str,
) -> SpamCheckResult:
    """
    Check if the honeypot field contains a value (indicates bot).

    Args:
        form_data: Submitted form data dict
        honeypot_field_name: Name of the honeypot field to check

    Returns:
        SpamCheckResult indicating if this is spam
    """
    honeypot_value = form_data.get(honeypot_field_name, "")
    if honeypot_value:
        return SpamCheckResult(is_spam=True, reason="Honeypot field filled")
    return SpamCheckResult(is_spam=False)


def check_rate_limit(
    ip_address: str,
    site_id: int,
    max_per_hour: int,
) -> SpamCheckResult:
    """
    Check if IP address has exceeded rate limit for this site.

    Uses Django cache to track submission counts. The counter automatically
    expires after 1 hour and increments atomically to prevent race conditions.

    Args:
        ip_address: Client IP address
        site_id: Wagtail Site ID for site-scoped limits
        max_per_hour: Maximum allowed submissions per hour

    Returns:
        SpamCheckResult with should_rate_limit=True if limit exceeded
    """
    if max_per_hour <= 0:
        return SpamCheckResult(is_spam=False)

    cache_key = get_rate_limit_cache_key(ip_address, site_id)
    new_count = _increment_rate_limit_counter(cache_key)
    if new_count is None:
        return SpamCheckResult(is_spam=False)

    if new_count > max_per_hour:
        return SpamCheckResult(
            is_spam=False,
            reason="Rate limit exceeded",
            should_rate_limit=True,
        )

    return SpamCheckResult(is_spam=False)


def increment_rate_limit_counter(ip_address: str, site_id: int) -> None:
    """
    Increment the rate limit counter for an IP/site combination.

    Call this when you need to increment without running spam checks.
    """
    cache_key = get_rate_limit_cache_key(ip_address, site_id)
    _increment_rate_limit_counter(cache_key)


def _increment_rate_limit_counter(cache_key: str) -> int | None:
    """Increment the rate limit counter, returning the updated value."""
    try:
        if cache.add(cache_key, 1, timeout=RATE_LIMIT_WINDOW_SECONDS):
            return 1

        try:
            new_count = cast(int, cache.incr(cache_key))
        except (ValueError, NotImplementedError):
            current_count = cast(int, cache.get(cache_key, 0))
            new_count = current_count + 1
            cache.set(cache_key, new_count, timeout=RATE_LIMIT_WINDOW_SECONDS)
            return new_count

        try:
            cache.touch(cache_key, timeout=RATE_LIMIT_WINDOW_SECONDS)
        except NotImplementedError:
            pass

        return new_count
    except Exception:
        logger.warning("Rate limit counter update failed", exc_info=True)
        return None


def generate_time_token() -> str:
    """
    Generate a signed time token for form timing validation.

    The token contains the current timestamp, signed with the secret key.
    Format: timestamp:signature

    Returns:
        Signed time token string
    """
    timestamp = str(int(time.time()))
    signature = _sign_timestamp(timestamp)
    return f"{timestamp}:{signature}"


def _sign_timestamp(timestamp: str) -> str:
    """Create HMAC signature for a timestamp."""
    key = settings.SECRET_KEY.encode()
    message = timestamp.encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _log_time_token_issue(
    message: str,
    *,
    status: str,
    reason: str,
    min_seconds: int,
) -> None:
    extra = {
        "event": "form_time_token",
        "time_token_status": status,
        "time_token_reason": reason,
        "min_seconds": min_seconds,
        "metric_name": f"forms.time_token.{status}",
        "metric_value": 1,
    }
    logger.warning(message, extra=extra)


def check_timing(
    time_token: str,
    min_seconds: int,
) -> SpamCheckResult:
    """
    Check if enough time has passed since form was rendered.

    Args:
        time_token: Signed token from generate_time_token()
        min_seconds: Minimum seconds required between render and submit

    Returns:
        SpamCheckResult indicating if submission was too fast
    """
    if not time_token:
        # No token provided - could be legitimate (JS disabled, old cache)
        _log_time_token_issue(
            "Time token missing; timing check skipped",
            status="missing",
            reason="missing",
            min_seconds=min_seconds,
        )
        return SpamCheckResult(is_spam=False)

    parts = time_token.split(":", 1)
    if len(parts) != 2:
        # Malformed token - suspicious but not definitive
        _log_time_token_issue(
            "Time token malformed; rejecting submission",
            status="malformed",
            reason="format",
            min_seconds=min_seconds,
        )
        return SpamCheckResult(is_spam=True, reason="Invalid time token format")

    timestamp_str, signature = parts

    # Verify signature
    expected_signature = _sign_timestamp(timestamp_str)
    if not hmac.compare_digest(signature, expected_signature):
        _log_time_token_issue(
            "Time token signature mismatch; rejecting submission",
            status="invalid_signature",
            reason="signature",
            min_seconds=min_seconds,
        )
        return SpamCheckResult(is_spam=True, reason="Invalid time token signature")

    # Check token age
    try:
        token_time = int(timestamp_str)
    except ValueError:
        _log_time_token_issue(
            "Time token timestamp invalid; rejecting submission",
            status="malformed",
            reason="timestamp",
            min_seconds=min_seconds,
        )
        return SpamCheckResult(is_spam=True, reason="Invalid timestamp in time token")

    current_time = int(time.time())
    elapsed = current_time - token_time

    # Token too old (expired)
    if elapsed > TIME_TOKEN_LIFETIME_SECONDS:
        return SpamCheckResult(is_spam=True, reason="Time token expired")

    # Submitted too quickly
    if elapsed < min_seconds:
        return SpamCheckResult(
            is_spam=True,
            reason=f"Submitted too quickly ({elapsed}s < {min_seconds}s minimum)",
        )

    return SpamCheckResult(is_spam=False)


def run_spam_checks(
    *,
    form_data: dict,
    ip_address: str,
    site_id: int,
    time_token: str,
    honeypot_field_name: str,
    rate_limit_per_hour: int,
    min_seconds_to_submit: int,
) -> SpamCheckResult:
    """
    Run all spam protection checks.

    Checks are run in order of computational cost (cheapest first):
    1. Honeypot check (instant)
    2. Rate limit check (atomic cache increment)
    3. Timing check (crypto verification)

    Args:
        form_data: Submitted form data
        ip_address: Client IP address
        site_id: Wagtail Site ID
        time_token: Signed time token from form
        honeypot_field_name: Name of honeypot field
        rate_limit_per_hour: Max submissions per IP per hour
        min_seconds_to_submit: Min seconds between render and submit

    Returns:
        SpamCheckResult with first failure reason, or success
    """
    # 1. Honeypot check
    result = check_honeypot(form_data, honeypot_field_name)
    if result.is_spam:
        return result

    # 2. Rate limit check
    result = check_rate_limit(ip_address, site_id, rate_limit_per_hour)
    if result.should_rate_limit:
        return result

    # 3. Timing check
    result = check_timing(time_token, min_seconds_to_submit)
    if result.is_spam:
        return result

    return SpamCheckResult(is_spam=False)


def get_client_ip(request: HttpRequest) -> str:
    """
    Extract client IP address from request.

    Handles X-Forwarded-For header for proxied requests.
    """
    return cast(str, request_get_client_ip(request))
