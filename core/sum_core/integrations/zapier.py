"""
Name: Zapier Integration Helper
Path: core/sum_core/integrations/zapier.py
Purpose: Build JSON payloads and perform HTTP requests for Zapier webhook delivery.
Family: Integrations, Leads, async tasks.
Dependencies: requests, Lead model, Wagtail Site model.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import requests

if TYPE_CHECKING:
    from sum_core.leads.models import Lead
    from wagtail.models import Site

logger = logging.getLogger(__name__)

# HTTP request configuration
ZAPIER_TIMEOUT_SECONDS = 10


@dataclass
class ZapierResult:
    """Result of a Zapier webhook request."""

    success: bool
    status_code: int | None = None
    error_message: str = ""


def build_zapier_payload(lead: Lead, site: Site) -> dict[str, Any]:
    """
    Build JSON payload for Zapier webhook matching SSOT schema.

    Args:
        lead: The Lead instance to build payload for.
        site: The Wagtail Site the lead belongs to.

    Returns:
        Dictionary with all required fields for Zapier webhook.
    """
    return {
        # Lead identification
        "lead_id": lead.id,
        "submitted_at": lead.submitted_at.isoformat() if lead.submitted_at else None,
        # Site context
        "site_hostname": site.hostname,
        "site_name": site.site_name,
        # Source information
        "page_url": lead.page_url,
        "lead_source": lead.lead_source,
        # Contact fields
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "message": lead.message,
        "form_type": lead.form_type,
        "form_data": lead.form_data,
        # Attribution fields
        "utm_source": lead.utm_source,
        "utm_medium": lead.utm_medium,
        "utm_campaign": lead.utm_campaign,
        "utm_term": lead.utm_term,
        "utm_content": lead.utm_content,
        "landing_page_url": lead.landing_page_url,
        "referrer_url": lead.referrer_url,
    }


def send_zapier_request(
    url: str,
    payload: dict[str, Any],
    timeout: int = ZAPIER_TIMEOUT_SECONDS,
) -> ZapierResult:
    """
    Perform HTTP POST to Zapier webhook URL.

    Args:
        url: The Zapier webhook URL.
        payload: JSON payload to send.
        timeout: Request timeout in seconds.

    Returns:
        ZapierResult indicating success/failure with status code and error message.
    """
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

        if response.ok:
            return ZapierResult(success=True, status_code=response.status_code)
        else:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            return ZapierResult(
                success=False,
                status_code=response.status_code,
                error_message=error_msg,
            )

    except requests.Timeout as e:
        return ZapierResult(
            success=False,
            error_message=f"Request timeout: {str(e)[:200]}",
        )

    except requests.ConnectionError as e:
        return ZapierResult(
            success=False,
            error_message=f"Connection error: {str(e)[:200]}",
        )

    except requests.RequestException as e:
        return ZapierResult(
            success=False,
            error_message=f"Request failed: {str(e)[:200]}",
        )
