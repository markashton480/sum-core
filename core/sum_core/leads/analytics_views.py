"""
Name: Lead analytics dashboard views
Path: core/sum_core/leads/analytics_views.py
Purpose: Provide analytics dashboard for lead metrics and insights.
Family: Lead management, analytics, reporting.
Dependencies: Django views, Lead model.
"""

from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from .constants import SCORE_HIGH_THRESHOLD, SCORE_MEDIUM_THRESHOLD
from .models import Lead
from .scoring import get_score_breakdown


def get_time_series_data(days: int = 30) -> dict[str, list]:
    """
    Generate time-series data for lead volume over the last N days.

    Args:
        days: Number of days to include in the time-series.

    Returns:
        dict with 'labels' (dates) and 'datasets' (lead counts per day).
    """
    today = timezone.now().date()
    start_date = today - timedelta(days=days - 1)

    # Single aggregated query instead of N queries
    daily_counts = (
        Lead.objects.filter(submitted_at__date__gte=start_date)
        .annotate(date=TruncDate("submitted_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    # Build dict for O(1) lookup
    counts_by_date = {item["date"]: item["count"] for item in daily_counts}

    # Fill in all days (including zeros)
    labels = []
    data = []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        labels.append(day.strftime("%Y-%m-%d"))
        data.append(counts_by_date.get(day, 0))

    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Leads",
                "data": data,
                "borderColor": "rgb(59, 130, 246)",
                "backgroundColor": "rgba(59, 130, 246, 0.1)",
                "tension": 0.1,
            }
        ],
    }


def get_score_distribution_data() -> dict[str, list]:
    """
    Generate score distribution data for pie/doughnut chart.

    Returns:
        dict with 'labels' and 'data' for high/medium/low priority counts.
    """
    leads = Lead.objects.all()
    high_count = leads.filter(score__gte=SCORE_HIGH_THRESHOLD).count()
    medium_count = leads.filter(
        score__gte=SCORE_MEDIUM_THRESHOLD, score__lt=SCORE_HIGH_THRESHOLD
    ).count()
    low_count = leads.filter(score__lt=SCORE_MEDIUM_THRESHOLD).count()

    return {
        "labels": [
            f"High ({SCORE_HIGH_THRESHOLD}+)",
            f"Medium ({SCORE_MEDIUM_THRESHOLD}-{SCORE_HIGH_THRESHOLD - 1})",
            f"Low (<{SCORE_MEDIUM_THRESHOLD})",
        ],
        "data": [high_count, medium_count, low_count],
        "backgroundColor": [
            "rgb(34, 197, 94)",  # Green for high
            "rgb(251, 146, 60)",  # Orange for medium
            "rgb(239, 68, 68)",  # Red for low
        ],
    }


def get_average_score_breakdown() -> dict[str, float]:
    """
    Calculate average score component values across recent leads (last 90 days).

    Performance optimization: Instead of processing all leads (O(N) with large datasets),
    we limit to the last 90 days. This provides relevant scoring trends while maintaining
    fast dashboard performance.

    Returns:
        dict with average values for each score component.
    """
    cache_key = "leads:average_score_breakdown"
    cached_breakdown = cache.get(cache_key)
    if cached_breakdown is not None:
        return cached_breakdown

    # Limit to last 90 days for performance
    cutoff_date = timezone.now() - timedelta(days=90)
    leads = Lead.objects.filter(submitted_at__gte=cutoff_date)

    if not leads.exists():
        empty_breakdown = {
            "data_completeness": 0.0,
            "source_quality": 0.0,
            "attribution_quality": 0.0,
            "engagement_signals": 0.0,
        }
        cache.set(cache_key, empty_breakdown, timeout=300)
        return empty_breakdown

    totals = {
        "data_completeness": 0,
        "source_quality": 0,
        "attribution_quality": 0,
        "engagement_signals": 0,
    }
    count = 0
    for lead in leads.iterator():
        breakdown = get_score_breakdown(lead)
        for key in totals:
            totals[key] += breakdown[key]
        count += 1

    breakdown = {key: round(value / count, 1) for key, value in totals.items()}
    cache.set(cache_key, breakdown, timeout=300)
    return breakdown


@staff_member_required
def lead_analytics_dashboard(request):
    """
    Analytics dashboard for lead metrics.

    Displays:
    - Total, weekly, and monthly lead counts
    - Average score and conversion rate
    - Priority distribution (high/medium/low)
    - Status and source distributions
    - Chart data for visualizations
    """
    # Date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Base queryset
    leads = Lead.objects.all()

    # Calculate conversion rate
    total = leads.count()
    won = leads.filter(status=Lead.Status.WON).count()
    conversion_rate = round((won / total) * 100, 1) if total > 0 else 0

    # Chart data
    chart_data = {
        "time_series": get_time_series_data(days=30),
        "score_distribution": get_score_distribution_data(),
    }

    # Status distribution with percentages
    status_distribution = list(leads.values("status").annotate(count=Count("id")))
    for item in status_distribution:
        item["percentage"] = round((item["count"] / total) * 100, 1) if total > 0 else 0

    # Source distribution with percentages
    source_distribution = list(leads.values("lead_source").annotate(count=Count("id")))
    for item in source_distribution:
        item["percentage"] = round((item["count"] / total) * 100, 1) if total > 0 else 0

    # Metrics
    context = {
        "total_leads": total,
        "weekly_leads": leads.filter(submitted_at__date__gte=week_ago).count(),
        "monthly_leads": leads.filter(submitted_at__date__gte=month_ago).count(),
        "average_score": round(leads.aggregate(avg=Avg("score"))["avg"] or 0, 1),
        "high_priority_count": leads.filter(score__gte=SCORE_HIGH_THRESHOLD).count(),
        "medium_priority_count": leads.filter(
            score__gte=SCORE_MEDIUM_THRESHOLD, score__lt=SCORE_HIGH_THRESHOLD
        ).count(),
        "low_priority_count": leads.filter(score__lt=SCORE_MEDIUM_THRESHOLD).count(),
        "conversion_rate": conversion_rate,
        # Threshold constants for template
        "score_high_threshold": SCORE_HIGH_THRESHOLD,
        "score_medium_threshold": SCORE_MEDIUM_THRESHOLD,
        # Distributions
        "status_distribution": status_distribution,
        "source_distribution": source_distribution,
        # Score breakdown
        "score_breakdown": get_average_score_breakdown(),
        # Chart data (for both template access and JSON serialization)
        "chart_data": chart_data,
    }

    return render(request, "sum_core/admin/lead_analytics_dashboard.html", context)
