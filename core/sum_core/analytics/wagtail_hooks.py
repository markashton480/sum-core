from django.forms import Media
from django.template.loader import render_to_string
from wagtail import hooks
from wagtail.models import Site

from .dashboard import get_lead_analytics


class LeadAnalyticsPanel:
    """
    Read-only analytics panel for the Wagtail admin dashboard.
    Shows summary of leads for the last 30 days scoped to the current site.
    """

    name = "lead_analytics"
    order = 200  # Adjust order to place it appropriately

    def __init__(self, request):
        self.request = request

    @property
    def media(self):
        return Media()

    def render(self):
        # Scope to the current site from the request
        site = Site.find_for_request(self.request)

        analytics_data = get_lead_analytics(site)

        context = {
            "request": self.request,
            **analytics_data,
        }
        return render_to_string("sum_core/admin/lead_analytics_panel.html", context)


@hooks.register("construct_homepage_panels")
def add_lead_analytics_panel(request, panels):
    panels.append(LeadAnalyticsPanel(request))
