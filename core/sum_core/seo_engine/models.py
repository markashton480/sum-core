"""
Name: SEO Engine Models
Path: core/sum_core/seo_engine/models.py
Purpose: Re-export aggregator for all SEO engine models.
Family: SEO Engine
Dependencies: analysis, suggestions, gaps modules.
"""

from __future__ import annotations

from .analysis import PageSEOAnalysis
from .gaps import ContentGap, GapType
from .location import AreaType, GenerationStatus, LocationPage, ServiceAreaConfig
from .suggestions import InternalLinkSuggestion, SuggestionStatus

__all__ = [
    "PageSEOAnalysis",
    "InternalLinkSuggestion",
    "SuggestionStatus",
    "ContentGap",
    "GapType",
    "ServiceAreaConfig",
    "LocationPage",
    "AreaType",
    "GenerationStatus",
]
