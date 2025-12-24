"""
Name: Pages Models Aggregator
Path: core/sum_core/pages/models.py
Purpose: Register page models for Django model discovery.
Family: SUM Platform – Page Types
Dependencies: sum_core.pages.standard.StandardPage, sum_core.pages.services
"""

from __future__ import annotations

from sum_core.pages.services import ServiceIndexPage, ServicePage
from sum_core.pages.standard import StandardPage

__all__ = ["StandardPage", "ServiceIndexPage", "ServicePage"]
