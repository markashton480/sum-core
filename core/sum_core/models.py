"""
Name: sum_core Models Aggregator
Path: core/sum_core/models.py
Purpose: Register models defined in submodules (e.g., branding SiteSettings) with Django.
Family: Loaded by Django when initializing the sum_core app.
Dependencies: sum_core.branding.models.
"""

from __future__ import annotations

from sum_core.branding.models import SiteSettings

__all__ = ["SiteSettings"]
