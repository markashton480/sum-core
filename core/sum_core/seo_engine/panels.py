"""
Name: SEO Engine Dashboard Panels
Path: core/sum_core/seo_engine/panels.py
Purpose: Dashboard panels for SEO overview in Wagtail admin.
Family: SEO Engine
Dependencies: Wagtail admin, SEO models, Django template rendering.
"""

from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist
from django.forms import Media
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.safestring import mark_safe
from wagtail.admin.panels import Panel
from wagtail.models import Page, Site


def render_seo_analysis_html(analysis_instance):
    """Format analysis_data as readable HTML. Shared between InspectView and Page Editor Panel."""
    import json

    if not analysis_instance or not analysis_instance.analysis_data:
        return mark_safe(
            '<div class="help-block help-info" style="padding: 1rem;">No analysis data available. Save the page to generate a report.</div>'
        )

    data = analysis_instance.analysis_data

    # CSS Variables for colors (Wagtail 4.0+ dark mode compatible)
    color_success = "var(--w-color-positive-100)"
    color_warning = "var(--w-color-warning-100)"
    color_error = "var(--w-color-critical-200)"
    color_text = "var(--w-color-text-context)"
    color_text_muted = "var(--w-color-text-label)"
    color_bg = "var(--w-color-surface-field)"
    color_border = "var(--w-color-border-furniture)"

    def get_status_props(val):
        if val >= 80:
            return color_success, "✓", "Good"
        if val >= 50:
            return color_warning, "⚠", "Needs Work"
        return color_error, "✗", "Poor"

    def normalize_score(value):
        try:
            normalized = float(value)
        except (TypeError, ValueError):
            return 0
        return max(0, min(100, int(normalized)))

    # Health section
    health = data.get("health", {})
    score = normalize_score(health.get("score", 0))
    score_color, score_icon, score_label = get_status_props(score)

    # Build HTML
    html_parts = []

    # Wrapper
    html_parts.append(
        f'<div style="font-family: system-ui, -apple-system, sans-serif; max-width: 1000px; color: {color_text};">'
    )

    # 1. Header Card with Score
    analyzed_date = escape(
        analysis_instance.analyzed_at.strftime("%Y-%m-%d %H:%M")
        if getattr(analysis_instance, "analyzed_at", None)
        else "Unknown date"
    )

    html_parts.append(f"""
        <div style="background: {color_bg}; border: 1px solid {color_border}; border-radius: 8px; padding: 24px; margin-bottom: 24px; display: flex; align-items: center; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">
            <div style="position: relative; width: 80px; height: 80px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                <svg viewBox="0 0 36 36" style="width: 100%; height: 100%; transform: rotate(-90deg);">
                    <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="{color_border}" stroke-width="3" />
                    <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="{score_color}" stroke-width="3" stroke-dasharray="{score}, 100" />
                </svg>
                <div style="position: absolute; text-align: center;">
                    <div style="font-size: 20px; font-weight: bold; color: {score_color};">{score}</div>
                    <div style="font-size: 10px; font-weight: 600; color: {score_color};">{score_label}</div>
                </div>
            </div>
            <div style="margin-left: 24px;">
                <h2 style="margin: 0; font-size: 20px; font-weight: 600; color: {color_text};">
                    SEO Health Score <span style="font-size: 16px; margin-left: 8px; color: {score_color};">{score_icon}</span>
                </h2>
                <p style="margin: 4px 0 0; color: {color_text_muted}; font-size: 14px;">
                    Analyzed on {analyzed_date}
                </p>
            </div>
        </div>
    """)

    # 2. Grid Layout for Details
    html_parts.append(
        '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px;">'
    )

    # Left Column: Breakdown
    breakdown = health.get("breakdown", {})
    if breakdown:
        html_parts.append(f"""
            <div style="background: {color_bg}; border: 1px solid {color_border}; border-radius: 8px; padding: 20px;">
                <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: {color_text}; border-bottom: 1px solid {color_border}; padding-bottom: 12px;">Metric Breakdown</h3>
                <div style="display: flex; flex-direction: column; gap: 16px;">
        """)
        for key, value in breakdown.items():
            label = escape(key.replace("_", " ").title())
            normalized_value = normalize_score(value)
            bar_color, bar_icon, _ = get_status_props(normalized_value)
            html_parts.append(f"""
                <div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px; font-weight: 500; color: {color_text_muted};">
                        <span>{label}</span>
                        <span style="color: {bar_color};">{normalized_value}/100 {bar_icon}</span>
                    </div>
                    <div style="width: 100%; height: 6px; background: {color_border}; border-radius: 3px; overflow: hidden;">
                        <div style="width: {normalized_value}%; height: 100%; background: {bar_color}; border-radius: 3px;"></div>
                    </div>
                </div>
            """)
        html_parts.append("</div></div>")

    # Right Column: Recommendations & Issues
    html_parts.append('<div style="display: flex; flex-direction: column; gap: 24px;">')

    # Content Issues (Warnings)
    content_issues = data.get("content", [])
    if content_issues:
        html_parts.append(f"""
            <div style="background: {color_bg}; border: 1px solid {color_error}; border-radius: 8px; padding: 16px;">
                <h3 style="margin: 0 0 12px 0; font-size: 15px; font-weight: 600; color: {color_error}; display: flex; align-items: center;">
                    <span style="margin-right: 8px;">⚠️</span> Critical Content Issues
                </h3>
                <ul style="margin: 0; padding: 0; list-style: none;">
        """)
        for issue in content_issues:
            title = escape(issue.get("title", "Issue"))
            desc = escape(issue.get("description", ""))
            html_parts.append(f"""
                <li style="margin-bottom: 12px; font-size: 13px; color: {color_text}; border-bottom: 1px solid {color_border}; padding-bottom: 8px;">
                    <strong style="display: block; margin-bottom: 2px; color: {color_error};">{title}</strong>
                    <span style="opacity: 0.9;">{desc}</span>
                </li>
            """)
        html_parts.append("</ul></div>")

    # Recommendations
    recommendations = health.get("recommendations", [])
    if recommendations:
        html_parts.append(f"""
            <div style="background: {color_bg}; border: 1px solid {color_border}; border-radius: 8px; padding: 20px;">
                <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: {color_text}; border-bottom: 1px solid {color_border}; padding-bottom: 12px;">Recommendations</h3>
                <ul style="margin: 0; padding: 0; list-style: none;">
        """)
        for rec in recommendations:
            safe_rec = escape(rec)
            html_parts.append(f"""
                <li style="margin-bottom: 12px; padding-left: 24px; position: relative; font-size: 13px; color: {color_text_muted}; line-height: 1.5;">
                    <span style="position: absolute; left: 0; top: 0; color: {color_warning};">➜</span>
                    {safe_rec}
                </li>
            """)
        html_parts.append("</ul></div>")

    html_parts.append("</div>")  # End Right Column
    html_parts.append("</div>")  # End Grid

    # Keywords Section (Full Width)
    keywords = data.get("keywords", {})
    if keywords and keywords.get("current_title"):
        page_type = escape(keywords.get("page_type", "Unknown"))
        importance = escape(keywords.get("importance", "Unknown"))
        focus_keywords = ", ".join(keywords.get("focus_keywords", []))
        focus_keywords = escape(focus_keywords) if focus_keywords else "None"
        html_parts.append(f"""
            <div style="background: {color_bg}; border: 1px solid {color_border}; border-radius: 8px; padding: 20px; margin-top: 24px;">
                <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: {color_text};">Keyword Context</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; font-size: 13px;">
                    <div style="padding: 12px; border: 1px solid {color_border}; border-radius: 6px;">
                        <span style="display: block; color: {color_text_muted}; margin-bottom: 4px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">Page Type</span>
                        <span style="font-weight: 500; color: {color_text};">{page_type}</span>
                    </div>
                    <div style="padding: 12px; border: 1px solid {color_border}; border-radius: 6px;">
                        <span style="display: block; color: {color_text_muted}; margin-bottom: 4px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">Importance</span>
                        <span style="font-weight: 500; color: {color_text};">{importance}</span>
                    </div>
                    <div style="padding: 12px; border: 1px solid {color_border}; border-radius: 6px;">
                        <span style="display: block; color: {color_text_muted}; margin-bottom: 4px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">Focus Keywords</span>
                        <span style="font-weight: 500; color: {color_text};">{focus_keywords}</span>
                    </div>
                </div>
            </div>
        """)

    # Raw Data (Collapsible)
    json_str = escape(json.dumps(data, indent=2))
    html_parts.append(f"""
        <details style="margin-top: 24px; border-top: 1px solid {color_border}; padding-top: 16px;">
            <summary style="cursor: pointer; color: {color_text_muted}; font-size: 13px; font-weight: 500;">View Raw Analysis Data</summary>
            <pre style="background: {color_bg}; color: {color_text}; padding: 16px; border-radius: 8px; border: 1px solid {color_border}; overflow: auto; font-size: 12px; margin-top: 12px; max-height: 400px;">{json_str}</pre>
        </details>
    """)

    html_parts.append("</div>")  # End Wrapper

    return mark_safe("".join(html_parts))


def render_link_suggestions_html(suggestions):
    """Render HTML for internal link suggestions (page editor only)."""

    if not suggestions:
        return ""

    suggestion_items = []
    for suggestion in suggestions:
        target_title = escape(suggestion.target_page.title)
        anchor_text = escape(suggestion.anchor_text)
        status_label = escape(suggestion.get_status_display())
        status_raw = escape(suggestion.status)
        status_class = escape(suggestion.status.lower())
        relevance_score = escape(f"{suggestion.relevance_score:.2f}")
        suggestion_items.append(f"""
            <li class="seo-link-suggestion" style="margin-bottom: 0.75rem; padding: 0.75rem; border: 1px solid var(--w-color-border-furniture); border-radius: 0.5rem; background: var(--w-color-surface);">
                <div style="display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap;">
                    <div>
                        <strong style="font-size: 1rem; color: var(--w-color-text-context);">{target_title}</strong>
                        <p style="margin: 0.25rem 0 0; color: var(--w-color-text-label);">Anchor text: &ldquo;{anchor_text}&rdquo;</p>
                    </div>
                    <div style="text-align: right; font-size: 0.85rem; color: var(--w-color-text-context);">
                        <span style="display: block; font-weight: 600;">Status: <span class="seo-link-status seo-link-status--{status_class}" style="color: var(--w-color-text-context);">{status_label}</span></span>
                        <span style="opacity: 0.8;">({status_raw})</span>
                        <span style="display:block; font-size:0.8rem; color:var(--w-color-text-label);">Relevance: {relevance_score}</span>
                    </div>
                </div>
            </li>
            """)

    return mark_safe(f"""
        <div class="seo-link-suggestions" style="margin-top: 1.5rem;">
            <h3 style="margin: 0 0 0.75rem 0; font-size: 1.125rem; color: var(--w-color-text-context);">Internal Link Suggestions ({len(suggestions)})</h3>
            <ul style="list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.5rem;">
                {"".join(suggestion_items)}
            </ul>
        </div>
        """)


class SEOAnalysisPanel(Panel):
    """
    Custom Wagtail Panel to display SEO analysis results in the Page Editor.
    """

    class BoundPanel(Panel.BoundPanel):
        def render_html(self, parent_context):
            instance = self.instance
            # If the instance is not saved yet, we can't show analysis
            if not instance or not instance.pk:
                return mark_safe(
                    '<div class="help-block help-info" style="padding: 1rem;">Please save the page to generate an SEO analysis report.</div>'
                )

            # Try to fetch analysis
            analysis = None
            try:
                from .models import PageSEOAnalysis

                analysis = PageSEOAnalysis.objects.get(page=instance)
            except (ImportError, ObjectDoesNotExist):
                analysis = None

            from .models import InternalLinkSuggestion

            suggestions = InternalLinkSuggestion.objects.filter(
                source_page=instance
            ).select_related("target_page")

            analysis_html = render_seo_analysis_html(analysis)
            suggestions_html = render_link_suggestions_html(suggestions)

            if not analysis and not suggestions.exists():
                return mark_safe(
                    '<div class="help-block help-info" style="padding: 1rem;">No SEO analysis or link suggestions available yet. Save the page to generate a report.</div>'
                )

            return mark_safe(f"{analysis_html}{suggestions_html}")

    def clone(self):
        return self.__class__(heading=self.heading)


class SEODashboardPanel:
    """
    SEO dashboard panel for Wagtail admin homepage.

    Shows:
    - Worst-scoring pages (lowest health scores)
    - Orphan pages (pages with no incoming links)
    - Content gaps count
    """

    name = "seo_dashboard"
    order = 250

    def __init__(self, request):
        self.request = request

    @property
    def media(self):
        return Media()

    def render(self):
        """Render the SEO dashboard panel."""
        site = Site.find_for_request(self.request)

        # Lazy import to avoid circular dependency
        from .analysis import PageSEOAnalysis
        from .gaps import ContentGap
        from .suggestions import InternalLinkSuggestion

        # Get worst-scoring pages (limit to 5)
        worst_pages = (
            PageSEOAnalysis.objects.filter(page__live=True)
            .select_related("page")
            .order_by("health_score")[:5]
        )

        # Count orphan pages (pages with no accepted incoming link suggestions)
        # A page is an orphan if it has no incoming_link_suggestions with status='accepted'
        all_live_pages = Page.objects.filter(live=True).exclude(depth__lte=1).count()
        pages_with_incoming_links = (
            InternalLinkSuggestion.objects.filter(status="accepted")
            .values_list("target_page_id", flat=True)
            .distinct()
            .count()
        )
        orphan_count = all_live_pages - pages_with_incoming_links

        # Count active content gaps (not dismissed)
        content_gaps_count = ContentGap.objects.filter(
            site=site, dismissed=False
        ).count()

        context = {
            "request": self.request,
            "worst_pages": worst_pages,
            "orphan_count": orphan_count,
            "content_gaps_count": content_gaps_count,
        }

        return render_to_string("sum_core/admin/seo_dashboard_panel.html", context)
