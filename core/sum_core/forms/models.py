"""
Name: Form configuration model
Path: core/sum_core/forms/models.py
Purpose: Per-site form settings for spam protection, rate limiting, and notifications.
Family: Forms, Leads, Spam Protection.
Dependencies: Django ORM, Wagtail Site.
"""

from __future__ import annotations

import logging
import re

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import EmailValidator
from django.db import IntegrityError, models, transaction
from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from sum_core.forms.fields import FormFieldsStreamBlock
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.admin.ui.tables import Column
from wagtail.fields import StreamField
from wagtail.models import Page, ReferenceIndex, Site
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.chooser import (
    ChooseResultsView,
    ChooseView,
    SnippetChooserViewSet,
)
from wagtail.snippets.views.snippets import SnippetViewSet

logger = logging.getLogger(__name__)


class FormConfiguration(models.Model):
    """
    Per-site form configuration for spam protection and behaviour.

    Each Wagtail Site can have its own FormConfiguration to control:
    - Honeypot field name
    - Rate limiting thresholds
    - Minimum submission time (anti-bot timing check)
    - Notification email address
    """

    site = models.OneToOneField(
        Site,
        on_delete=models.CASCADE,
        related_name="form_configuration",
        help_text="The site this configuration applies to.",
    )

    # Spam protection: Honeypot
    honeypot_field_name = models.CharField(
        max_length=50,
        default="company",
        help_text="Name of the honeypot field. If filled, submission is rejected as spam.",
    )

    # Spam protection: Rate limiting
    rate_limit_per_ip_per_hour = models.PositiveIntegerField(
        default=20,
        help_text="Maximum form submissions allowed per IP address per hour.",
    )

    # Spam protection: Timing
    min_seconds_to_submit = models.PositiveIntegerField(
        default=3,
        help_text="Minimum seconds between form render and submission. Faster submissions are rejected.",
    )

    # Notifications
    lead_notification_email = models.EmailField(
        blank=True,
        help_text="Email address for lead notifications. If blank, falls back to environment variable.",
    )

    # Presentation metadata
    default_form_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Default form type if not specified in submission.",
    )

    class Meta:
        verbose_name = "Form Configuration"
        verbose_name_plural = "Form Configurations"

    def __str__(self) -> str:
        return f"Form Configuration for {self.site.hostname}"

    @classmethod
    def get_for_site(cls, site: Site) -> FormConfiguration:
        """
        Get or create FormConfiguration for a site.

        Returns the existing configuration or a new instance with defaults.
        The returned instance is always saved to the database.
        """
        from typing import cast

        config, _created = cls.objects.get_or_create(site=site)
        return cast(FormConfiguration, config)

    @classmethod
    def get_defaults(cls) -> dict:
        """Return default configuration values for use when no config exists."""
        return {
            "honeypot_field_name": "company",
            "rate_limit_per_ip_per_hour": 20,
            "min_seconds_to_submit": 3,
        }


def validate_comma_separated_emails(value: str) -> None:
    """Validate comma-separated email addresses."""
    if not value:
        return

    validator = EmailValidator()
    errors: list[str] = []

    for raw_email in value.split(","):
        email = raw_email.strip()
        if not email:
            errors.append("Email addresses must not be empty when separated by commas.")
            continue

        try:
            validator(email)
        except ValidationError:
            errors.append(f"'{email}' is not a valid email address.")

    if errors:
        raise ValidationError(errors)


class FormDefinition(models.Model):
    """
    Reusable form definition for dynamic forms.

    Supports multi-site configuration, notifications, and webhook delivery.
    """

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="form_definitions",
        help_text="Site this form definition belongs to.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Reference name used in the admin.",
    )
    slug = models.SlugField(
        max_length=100,
        help_text="Unique identifier for this form within the site.",
    )
    fields = StreamField(
        FormFieldsStreamBlock(required=False),
        blank=True,
        use_json_field=True,
        help_text="Form field blocks for dynamic forms.",
    )
    success_message = models.TextField(
        default="Thank you for your submission!",
        help_text="Message shown after successful submission.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Deactivate to hide this form without deleting it.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Notifications
    email_notification_enabled = models.BooleanField(
        default=True,
        help_text="Send notification emails on submission.",
    )
    notification_emails = models.TextField(
        blank=True,
        validators=[validate_comma_separated_emails],
        help_text="Comma-separated list of recipient emails.",
    )
    auto_reply_enabled = models.BooleanField(
        default=False,
        help_text="Send auto-reply to the submitter.",
    )
    auto_reply_subject = models.CharField(
        max_length=255,
        blank=True,
        help_text="Subject for auto-reply emails.",
    )
    auto_reply_body = models.TextField(
        blank=True,
        help_text="Body content for auto-reply emails.",
    )

    # Webhooks
    webhook_enabled = models.BooleanField(
        default=False,
        help_text="Send webhook on submission.",
    )
    webhook_url = models.URLField(
        blank=True,
        help_text="Endpoint to receive submission payloads.",
    )
    webhook_signing_secret = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional shared secret used to sign webhook payloads.",
    )
    webhook_field_allowlist = models.TextField(
        blank=True,
        help_text=(
            "Comma-separated list of form field keys allowed in webhook payloads."
        ),
    )
    webhook_field_denylist = models.TextField(
        blank=True,
        help_text=(
            "Comma-separated list of form field keys to exclude from webhook payloads."
        ),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("site"),
                FieldPanel("name"),
                FieldPanel("slug"),
            ],
            heading="Basic Settings",
        ),
        MultiFieldPanel(
            [FieldPanel("fields")],
            heading="Form Fields",
        ),
        MultiFieldPanel(
            [FieldPanel("success_message")],
            heading="Submission Settings",
        ),
        MultiFieldPanel(
            [
                FieldPanel("email_notification_enabled"),
                FieldPanel("notification_emails"),
                FieldPanel("auto_reply_enabled"),
                FieldPanel("auto_reply_subject"),
                FieldPanel("auto_reply_body"),
            ],
            heading="Notifications",
        ),
        MultiFieldPanel(
            [
                FieldPanel("webhook_enabled"),
                FieldPanel("webhook_url"),
                FieldPanel("webhook_signing_secret"),
                FieldPanel("webhook_field_allowlist"),
                FieldPanel("webhook_field_denylist"),
            ],
            heading="Webhooks",
        ),
        MultiFieldPanel(
            [
                FieldPanel("is_active"),
            ],
            heading="Status",
        ),
    ]

    class Meta:
        verbose_name = "Form Definition"
        verbose_name_plural = "Form Definitions"
        unique_together = [("site", "slug")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return str(self.name)

    def _build_unique_slug(self, base_slug: str) -> str:
        slug_field = self._meta.get_field("slug")
        max_length = slug_field.max_length or 100
        trimmed_base = base_slug[:max_length].rstrip("-")
        slug = trimmed_base
        counter = 1

        while FormDefinition.objects.filter(site=self.site, slug=slug).exists():
            suffix = f"-{counter}"
            if len(trimmed_base) + len(suffix) > max_length:
                trimmed_base = trimmed_base[: max_length - len(suffix)].rstrip("-")
            slug = f"{trimmed_base}{suffix}"
            counter += 1

        return slug

    def clone(self) -> FormDefinition:
        """
        Create a duplicate of this FormDefinition with a unique slug.

        The cloned form starts inactive for safety.
        """
        base_slug = f"{self.slug}-copy"
        for _ in range(5):
            cloned = FormDefinition(
                site=self.site,
                name=f"{self.name} (Copy)",
                slug=self._build_unique_slug(base_slug),
                fields=self.fields.raw_data if self.fields else [],
                success_message=self.success_message,
                is_active=False,
                email_notification_enabled=self.email_notification_enabled,
                notification_emails=self.notification_emails,
                auto_reply_enabled=self.auto_reply_enabled,
                auto_reply_subject=self.auto_reply_subject,
                auto_reply_body=self.auto_reply_body,
                webhook_enabled=self.webhook_enabled,
                webhook_url=self.webhook_url,
                webhook_signing_secret=self.webhook_signing_secret,
                webhook_field_allowlist=self.webhook_field_allowlist,
                webhook_field_denylist=self.webhook_field_denylist,
            )

            try:
                with transaction.atomic():
                    cloned.full_clean()
                    cloned.save()
                return cloned
            except IntegrityError:
                continue

        raise IntegrityError("Failed to generate unique slug for cloned form.")

    def clean(self) -> None:
        """Validate notification emails and webhook configuration."""
        errors = {}

        if self.webhook_enabled and not self.webhook_url:
            errors["webhook_url"] = ValidationError(
                "Webhook URL is required when webhooks are enabled."
            )

        allowlist = self._parse_webhook_field_list(self.webhook_field_allowlist)
        denylist = self._parse_webhook_field_list(self.webhook_field_denylist)
        overlap = allowlist.intersection(denylist)
        if overlap:
            errors["webhook_field_denylist"] = ValidationError(
                "Fields cannot be both allowed and denied.",
            )

        if errors:
            raise ValidationError(errors)

        super().clean()

    @staticmethod
    def _parse_webhook_field_list(value: str) -> set[str]:
        return {
            item.strip() for item in re.split(r"[,\n]+", value or "") if item.strip()
        }

    def get_webhook_allowlist(self) -> set[str]:
        return self._parse_webhook_field_list(self.webhook_field_allowlist)

    def get_webhook_denylist(self) -> set[str]:
        return self._parse_webhook_field_list(self.webhook_field_denylist)

    def get_usage_pages(self) -> list:
        """Return pages that reference this form definition."""
        page_content_type_id = ContentType.objects.get_for_model(
            Page, for_concrete_model=False
        ).id
        form_content_type_id = ContentType.objects.get_for_model(
            FormDefinition, for_concrete_model=False
        ).id
        page_ids = (
            ReferenceIndex.objects.filter(
                to_content_type_id=form_content_type_id,
                to_object_id=self.pk,
                base_content_type_id=page_content_type_id,
            )
            .values_list("object_id", flat=True)
            .distinct()
        )
        return list(Page.objects.filter(pk__in=page_ids).specific())

    @property
    def usage_count(self) -> int:
        """Number of pages using this form."""
        cached = getattr(self, "_usage_count", None)
        if cached is not None:
            return int(cached)
        page_content_type_id = ContentType.objects.get_for_model(
            Page, for_concrete_model=False
        ).id
        form_content_type_id = ContentType.objects.get_for_model(
            FormDefinition, for_concrete_model=False
        ).id
        return int(
            ReferenceIndex.objects.filter(
                to_content_type_id=form_content_type_id,
                to_object_id=self.pk,
                base_content_type_id=page_content_type_id,
            )
            .values("object_id")
            .distinct()
            .count()
        )

    @property
    def submission_count(self) -> int:
        """Number of submissions for this form."""
        from sum_core.leads.models import Lead

        cached = getattr(self, "_submission_count", None)
        if cached is not None:
            return int(cached)
        return int(Lead.objects.filter(form_type=self.slug).count())


class ActiveFormDefinitionChooseView(ChooseView):
    """Limit chooser options to active forms on the current site."""

    def get_object_list(self):
        queryset = super().get_object_list().filter(is_active=True)

        current_site = getattr(self.request, "site", None) or Site.find_for_request(
            self.request
        )
        if current_site:
            queryset = queryset.filter(site=current_site)

        return queryset


class ActiveFormDefinitionChooseResultsView(ChooseResultsView):
    """Ensure chooser search/results use the same filtering rules."""

    def get_object_list(self):
        queryset = super().get_object_list().filter(is_active=True)

        current_site = getattr(self.request, "site", None) or Site.find_for_request(
            self.request
        )
        if current_site:
            queryset = queryset.filter(site=current_site)

        return queryset


class ActiveFormDefinitionChooserViewSet(SnippetChooserViewSet):
    """Chooser viewset limited to active forms for the current site."""

    choose_view_class = ActiveFormDefinitionChooseView
    choose_results_view_class = ActiveFormDefinitionChooseResultsView


class FormDefinitionViewSet(SnippetViewSet):
    """Wagtail Snippet viewset for managing form definitions."""

    model = FormDefinition
    icon = "form"
    menu_label = "Form Definitions"
    list_display = [
        "name",
        "slug",
        "is_active",
        Column("submission_count", label="Submissions"),
        Column("usage_count", label="Usage"),
        "created_at",
    ]
    list_filter = ["is_active", "site", "created_at"]
    search_fields = ["name", "slug"]
    panels = FormDefinition.panels
    chooser_viewset_class = ActiveFormDefinitionChooserViewSet

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if queryset is None:
            queryset = self.model.objects.all()

        from sum_core.leads.models import Lead

        form_content_type_id = ContentType.objects.get_for_model(
            self.model, for_concrete_model=False
        ).id
        page_content_type_id = ContentType.objects.get_for_model(
            Page, for_concrete_model=False
        ).id

        submission_counts = (
            Lead.objects.filter(form_type=OuterRef("slug"))
            .values("form_type")
            .annotate(count=Count("pk"))
            .values("count")
        )
        usage_counts = (
            ReferenceIndex.objects.filter(
                to_content_type_id=form_content_type_id,
                to_object_id=OuterRef("pk"),
                base_content_type_id=page_content_type_id,
            )
            .values("to_object_id")
            .annotate(count=Count("object_id", distinct=True))
            .values("count")
        )

        return queryset.annotate(
            _submission_count=Coalesce(
                Subquery(submission_counts, output_field=IntegerField()),
                Value(0),
            ),
            _usage_count=Coalesce(
                Subquery(usage_counts, output_field=IntegerField()),
                Value(0),
            ),
        )

    def get_urlpatterns(self):
        urlpatterns = super().get_urlpatterns()
        return [
            *urlpatterns,
            path("clone/<int:pk>/", self.clone_view, name="clone"),
            path("preview/<int:pk>/", self.preview_view, name="preview"),
            path("usage-report/<int:pk>/", self.usage_report_view, name="usage_report"),
        ]

    def preview_view(self, request, pk):
        if not self.permission_policy.user_has_permission(request.user, "change"):
            raise PermissionDenied

        form_def = get_object_or_404(self.model, pk=pk)
        edit_url = reverse(self.get_url_name("edit"), args=[form_def.pk])
        return render(
            request,
            "sum_core/admin/form_preview.html",
            {
                "form_definition": form_def,
                "edit_url": edit_url,
            },
        )

    def usage_report_view(self, request, pk):
        if not self.permission_policy.user_has_permission(request.user, "change"):
            raise PermissionDenied

        form_def = get_object_or_404(self.model, pk=pk)
        edit_url = reverse(self.get_url_name("edit"), args=[form_def.pk])
        usage_pages = form_def.get_usage_pages()
        return render(
            request,
            "sum_core/admin/form_usage.html",
            {
                "form_definition": form_def,
                "edit_url": edit_url,
                "usage_pages": usage_pages,
            },
        )

    @method_decorator(require_POST)
    def clone_view(self, request, pk):
        if not (
            self.permission_policy.user_has_permission(request.user, "add")
            and self.permission_policy.user_has_permission(request.user, "change")
        ):
            raise PermissionDenied

        form_def = get_object_or_404(self.model, pk=pk)
        try:
            with transaction.atomic():
                cloned = form_def.clone()
        except (IntegrityError, ValidationError):
            logger.exception("Failed to clone form definition %s", form_def.pk)
            messages.error(
                request,
                "Unable to clone this form right now. Please try again.",
            )
            return redirect(reverse(self.get_url_name("edit"), args=[form_def.pk]))

        messages.success(request, f"Form '{form_def.name}' cloned successfully.")
        return redirect(reverse(self.get_url_name("edit"), args=[cloned.pk]))


register_snippet(FormDefinitionViewSet)
