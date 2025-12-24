from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from sum_core.leads.models import Lead
from wagtail.models import Site


def get_lead_analytics(site: Site, days: int = 30) -> dict:
    """
    Aggregate lead data for the given site over the last N days.

    Args:
        site: The Wagtail Site to scope analytics to.
        days: Number of days to look back.

    Returns:
        dict: {
            "total": int,
            "by_status": dict[str, int],  # { "New": 10, "Won": 5 }
            "by_source": dict[str, int],  # { "Google Ads": 10, "SEO": 5 }
        }
    """
    if not site or not site.root_page:
        return {
            "total": 0,
            "by_status": {},
            "by_source": {},
        }

    cutoff = timezone.now() - timedelta(days=days)

    # Filter leads by date and site scope
    # source_page is a Page, and we want pages belonging to this site.
    # Site.root_page is the root of the site's operations.
    # We query using path__startswith to include the root and all descendants.
    leads = Lead.objects.filter(
        submitted_at__gte=cutoff,
        source_page__path__startswith=site.root_page.path,
    )

    # Aggregations
    # 1. Total count
    total_leads = leads.count()

    # 2. Group by status
    # .values('status') groups by status
    # .annotate(count=Count('id')) counts items in group
    status_counts_qs = leads.values("status").annotate(count=Count("id")).order_by()
    # Map status codes to labels? The requirement shows "New", "Contacted", etc.
    # Lead.Status.choices gives us the map.
    status_labels = dict(Lead.Status.choices)
    by_status = {}

    # Initialize all statuses with 0 to match Expected UI Output "Leads by status" list
    # Requirement: "Leads by status: New: N, Contacted: N..."
    # It implies we should list all of them preferably, or at least the ones with counts.
    # "Handle empty datasets cleanly (show zeroes...)" suggests showing zeroes for known statuses is good.
    for code, label in Lead.Status.choices:
        by_status[label] = 0

    for item in status_counts_qs:
        label = status_labels.get(item["status"], item["status"])
        by_status[label] = item["count"]

    # 3. Group by source
    source_counts_qs = (
        leads.values("lead_source").annotate(count=Count("id")).order_by()
    )

    from sum_core.leads.models import LeadSource

    source_labels = dict(LeadSource.choices)

    by_source = {}

    # Initialize all defined sources as 0.
    for code, label in LeadSource.choices:
        by_source[label] = 0

    for item in source_counts_qs:
        s_code = item["lead_source"]
        # Handle empty source (though model field is blank=True)
        if not s_code:
            label = "Unknown"
        else:
            label = source_labels.get(s_code, s_code)

        # If "Unknown" shows up and we want to track it
        if label not in by_source:
            by_source[label] = 0
        by_source[label] += item["count"]

    return {
        "total": total_leads,
        "by_status": by_status,
        "by_source": by_source,
    }
