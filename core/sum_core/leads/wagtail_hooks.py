"""
Name: Leads Wagtail hooks
Path: core/sum_core/leads/wagtail_hooks.py
Purpose: Register Leads admin viewsets in Wagtail so “Leads” appears in the admin UI.
Family: Lead management, admin UX.
Dependencies: Wagtail hooks, leads admin viewsets.
"""

from sum_core.leads.wagtail_admin import LeadViewSet
from wagtail import hooks


@hooks.register("register_admin_viewset")
def register_lead_viewset() -> LeadViewSet:
    """Register the Lead ViewSet with Wagtail admin."""
    return LeadViewSet("leads")
