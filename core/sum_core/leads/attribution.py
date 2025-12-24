"""
Name: Lead attribution & source derivation
Path: core/sum_core/leads/attribution.py
Purpose: Derive lead_source from UTMs/referrer using rules + defaults.
Family: Leads, attribution, reporting, integrations.
Dependencies: LeadSourceRule, URL parsing helpers (if used).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sum_core.leads.models import LeadSourceRule


def derive_lead_source(
    *,
    utm_source: str = "",
    utm_medium: str = "",
    utm_campaign: str = "",
    referrer_url: str = "",
) -> tuple[str, str]:
    """
    Derive lead_source and lead_source_detail from attribution inputs.

    The derivation follows this priority:
    1. Match against active LeadSourceRule records (by priority order)
    2. Fall back to SSOT default attribution rules (8.2)

    Args:
        utm_source: UTM source parameter value
        utm_medium: UTM medium parameter value
        utm_campaign: UTM campaign parameter value (used for detail)
        referrer_url: HTTP referer URL

    Returns:
        Tuple of (lead_source, lead_source_detail)
    """
    # Normalize inputs
    source = (utm_source or "").strip().lower()
    medium = (utm_medium or "").strip().lower()
    campaign = (utm_campaign or "").strip()
    referrer = (referrer_url or "").strip().lower()

    # 1. Try custom LeadSourceRule matches first
    rule_result = _match_lead_source_rules(
        utm_source=source,
        utm_medium=medium,
        referrer_url=referrer,
    )
    if rule_result:
        lead_source, rule_detail = rule_result
        # Append campaign to detail if present
        detail_parts = [rule_detail] if rule_detail else []
        if campaign:
            detail_parts.append(f"campaign={campaign}")
        return lead_source, "; ".join(detail_parts)

    # 2. Fall back to SSOT default rules (8.2)
    return _apply_ssot_defaults(
        utm_source=source,
        utm_medium=medium,
        utm_campaign=campaign,
        referrer_url=referrer,
    )


def _match_lead_source_rules(
    *,
    utm_source: str,
    utm_medium: str,
    referrer_url: str,
) -> tuple[str, str] | None:
    """
    Match attribution inputs against active LeadSourceRule records.

    Rules are evaluated in priority order (lower = higher priority).
    Returns the first matching rule's (derived_source, derived_source_detail),
    or None if no rules match.
    """
    # Import here to avoid circular import
    from sum_core.leads.models import LeadSourceRule

    rules: list[LeadSourceRule] = list(
        LeadSourceRule.objects.filter(is_active=True).order_by("priority", "id")
    )

    for rule in rules:
        if rule.matches(
            utm_source=utm_source,
            utm_medium=utm_medium,
            referrer_url=referrer_url,
        ):
            return rule.derived_source, rule.derived_source_detail

    return None


def _apply_ssot_defaults(
    *,
    utm_source: str,
    utm_medium: str,
    utm_campaign: str,
    referrer_url: str,
) -> tuple[str, str]:
    """
    Apply SSOT 8.2 default attribution rules.

    | Condition | Derived Source |
    |-----------|----------------|
    | utm_source=google + utm_medium=cpc | google_ads |
    | utm_source=facebook/instagram + utm_medium=cpc | meta_ads |
    | utm_source=bing + utm_medium=cpc | bing_ads |
    | referrer contains google.com + no utm | seo |
    | No referrer + no utm | direct |
    | Has referrer + no utm | referral |
    | utm_source starts with offline | offline |
    | All else | unknown |
    """
    has_utm = bool(utm_source or utm_medium)

    # Build detail string from campaign if present
    detail = f"campaign={utm_campaign}" if utm_campaign else ""

    # Rule: utm_source=google + utm_medium=cpc → google_ads
    if utm_source == "google" and utm_medium == "cpc":
        return "google_ads", detail

    # Rule: utm_source=facebook/instagram + utm_medium=cpc → meta_ads
    if utm_source in ("facebook", "instagram", "fb", "ig") and utm_medium == "cpc":
        return "meta_ads", detail

    # Rule: utm_source=bing + utm_medium=cpc → bing_ads
    if utm_source == "bing" and utm_medium == "cpc":
        return "bing_ads", detail

    # Rule: utm_source starts with offline → offline
    if utm_source.startswith("offline"):
        return "offline", detail

    # Rule: referrer contains google.com + no utm → seo
    if not has_utm and "google.com" in referrer_url:
        return "seo", f"referrer={referrer_url}" if referrer_url else ""

    # Rule: No referrer + no utm → direct
    if not has_utm and not referrer_url:
        return "direct", ""

    # Rule: Has referrer + no utm → referral
    if not has_utm and referrer_url:
        return "referral", f"referrer={referrer_url}"

    # All else → unknown
    detail_parts = []
    if utm_source:
        detail_parts.append(f"utm_source={utm_source}")
    if utm_medium:
        detail_parts.append(f"utm_medium={utm_medium}")
    if utm_campaign:
        detail_parts.append(f"campaign={utm_campaign}")
    return "unknown", "; ".join(detail_parts)
