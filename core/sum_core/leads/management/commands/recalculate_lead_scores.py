"""
Management command to recalculate lead scores for all existing leads.

Usage:
    python manage.py recalculate_lead_scores
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from sum_core.leads.models import Lead
from sum_core.leads.scoring import calculate_lead_score


class Command(BaseCommand):
    """Recalculate scores for all leads."""

    help = "Recalculate scores for all leads"

    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write("Starting lead score recalculation...")

        leads_queryset = Lead.objects.all()
        total_leads = leads_queryset.count()
        self.stdout.write(f"Processing {total_leads} leads...")

        now = timezone.now()
        leads_to_update = []

        for lead in leads_queryset.iterator(chunk_size=1000):
            old_score = lead.score
            new_score = calculate_lead_score(lead)

            if old_score != new_score:
                lead.score = new_score
                lead.score_updated_at = now
                leads_to_update.append(lead)

        if leads_to_update:
            Lead.objects.bulk_update(
                leads_to_update, fields=["score", "score_updated_at"], batch_size=500
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {len(leads_to_update)} lead scores (out of {total_leads} total leads)"
            )
        )
