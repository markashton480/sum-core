"""
Name: Lead scoring algorithm
Path: core/sum_core/leads/scoring.py
Purpose: Calculate lead priority scores based on data completeness, source quality, attribution, and engagement.
Family: Lead management, analytics, prioritization.
Dependencies: Lead model.

Scoring weights can be customized via Django settings:
    LEAD_SCORING_SOURCE_WEIGHTS = {...}
    LEAD_SCORING_FORM_TYPE_WEIGHTS = {...}
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from .models import Lead


# Default weights (used if not overridden in settings)
DEFAULT_SOURCE_WEIGHTS = {
    "google_ads": 25,
    "meta_ads": 20,
    "bing_ads": 20,
    "offline": 25,
    "seo": 15,
    "referral": 15,
    "direct": 10,
    "unknown": 5,
}

DEFAULT_FORM_TYPE_WEIGHTS = {
    "quote": 15,
    "dynamic": 10,
    "contact": 5,
}


def get_source_weights() -> dict:
    """Get source weights from settings or use defaults."""
    return getattr(settings, "LEAD_SCORING_SOURCE_WEIGHTS", DEFAULT_SOURCE_WEIGHTS)


def get_form_type_weights() -> dict:
    """Get form type weights from settings or use defaults."""
    return getattr(
        settings, "LEAD_SCORING_FORM_TYPE_WEIGHTS", DEFAULT_FORM_TYPE_WEIGHTS
    )


def calculate_lead_score(lead: Lead) -> int:
    """
    Calculate lead score based on documented algorithm.

    Scoring criteria:
    - Data Completeness (0-30): name, email, phone, message, form_data
    - Source Quality (0-30): lead_source value
    - Attribution Quality (0-20): UTM parameters, referrer, landing page
    - Engagement Signals (0-20): form_type

    Returns:
        int: Score between 0 and 100
    """
    score = 0

    # 1. Data Completeness (0-30)
    if lead.name:
        score += 5
    if lead.email:
        score += 5
    if lead.phone:
        score += 10
    if lead.message:
        score += 5
    if lead.form_data:
        score += 5

    # 2. Source Quality (0-30)
    source_scores = get_source_weights()
    score += source_scores.get(lead.lead_source, 5)

    # 3. Attribution Quality (0-20)
    if lead.utm_source:
        score += 5
    if lead.utm_campaign:
        score += 5
    if lead.referrer_url:
        score += 5
    if lead.landing_page_url:
        score += 5

    # 4. Engagement Signals (0-20)
    form_type_scores = get_form_type_weights()
    score += form_type_scores.get(lead.form_type, 5)

    return min(score, 100)  # Cap at 100


def get_score_breakdown(lead: Lead) -> dict:
    """
    Return detailed breakdown of lead score components.

    Returns dict with:
        - data_completeness: int (0-30)
        - source_quality: int (0-30)
        - attribution_quality: int (0-20)
        - engagement_signals: int (0-20)
        - total: int (0-100)
    """
    data_completeness = 0
    if lead.name:
        data_completeness += 5
    if lead.email:
        data_completeness += 5
    if lead.phone:
        data_completeness += 10
    if lead.message:
        data_completeness += 5
    if lead.form_data:
        data_completeness += 5

    source_weights = get_source_weights()
    source_quality = source_weights.get(lead.lead_source, 5)

    attribution_quality = 0
    if lead.utm_source:
        attribution_quality += 5
    if lead.utm_campaign:
        attribution_quality += 5
    if lead.referrer_url:
        attribution_quality += 5
    if lead.landing_page_url:
        attribution_quality += 5

    form_type_weights = get_form_type_weights()
    engagement_signals = form_type_weights.get(lead.form_type, 5)

    return {
        "data_completeness": data_completeness,
        "source_quality": source_quality,
        "attribution_quality": attribution_quality,
        "engagement_signals": engagement_signals,
        "total": min(
            data_completeness
            + source_quality
            + attribution_quality
            + engagement_signals,
            100,
        ),
    }
