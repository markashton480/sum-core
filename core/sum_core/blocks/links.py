"""
Name: Link Blocks
Path: core/sum_core/blocks/links.py
Purpose: Define UniversalLinkBlock - a reusable link primitive supporting page,
         URL, email, phone, and anchor link types.
Family: Foundation block for navigation, CTAs, and any link-based content.
Dependencies: wagtail.blocks, django.core.exceptions, sum_core.utils
"""

import logging
import re
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from sum_core.utils.contact import normalize_phone_href
from wagtail import blocks

logger = logging.getLogger(__name__)

# =============================================================================
# Link Type Choices
# =============================================================================

LINK_TYPE_CHOICES = [
    ("page", "Page"),
    ("url", "External URL"),
    ("path", "Internal path"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("anchor", "Anchor"),
]


# =============================================================================
# Regex Patterns for Validation
# =============================================================================

# Anchor must start with a letter, then letters/numbers/hyphen/underscore
ANCHOR_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")

# Phone number cleaning uses shared utility from sum_core.utils.contact


# =============================================================================
# UniversalLinkValue (StructValue with computed properties)
# =============================================================================


class UniversalLinkValue(blocks.StructValue):
    """
    Custom StructValue that provides computed properties for link handling.

    Computed Properties:
        href: Normalized link URL (mailto:, tel:, #, page.url, or raw URL)
        text: Display text (custom or fallback based on link type)
        is_external: True only for 'url' type links
        opens_new_tab: Whether link should open in new tab
        attrs: Dict of HTML attributes for the link
        attrs_str: String form of attrs for template interpolation
    """

    @property
    def href(self) -> str:
        """
        Returns the normalized href based on link type.

        - page: page.url (or '#' if page not set), with optional #anchor
        - url: raw URL
        - path: root-relative internal path
        - email: mailto:address
        - phone: tel:+number (strips formatting, preserves leading +)
        - anchor: #anchor-id (strips leading # if present in input)
        """
        link_type = self.get("link_type")

        if link_type == "page":
            page = self.get("page")
            if not page:
                return "#"
            anchor = (self.get("anchor") or "").lstrip("#")
            return f"{page.url}#{anchor}" if anchor else page.url

        elif link_type == "url":
            return self.get("url") or "#"

        elif link_type == "path":
            return self.get("path") or "#"

        elif link_type == "email":
            email = self.get("email") or ""
            return f"mailto:{email}" if email else "#"

        elif link_type == "phone":
            phone = self.get("phone") or ""
            # Use shared utility for phone normalization
            href = normalize_phone_href(phone)
            return href if href else "#"

        elif link_type == "anchor":
            anchor = self.get("anchor") or ""
            # Strip leading # if present
            anchor = anchor.lstrip("#")
            return f"#{anchor}" if anchor else "#"

        return "#"

    @property
    def text(self) -> str:
        """
        Returns display text for the link.

        Priority:
        1. Custom link_text if provided
        2. Fallback based on link type:
           - page: page.title
           - url: domain extracted from URL
           - path: path string
           - email: email address
           - phone: phone number
           - anchor: anchor ID
        """
        custom_text = self.get("link_text")
        if custom_text:
            return str(custom_text)

        link_type = self.get("link_type")

        if link_type == "page":
            page = self.get("page")
            return page.title if page else "Link"

        elif link_type == "url":
            url = self.get("url") or ""
            if url:
                try:
                    parsed = urlparse(url)
                    # Return domain without www. prefix
                    domain = parsed.netloc
                    if domain.startswith("www."):
                        domain = domain[4:]
                    return domain or url
                except Exception as e:
                    logger.debug("Failed to parse URL for link text '%s': %s", url, e)
                    return url
            return "Link"

        elif link_type == "path":
            return self.get("path") or "Link"

        elif link_type == "email":
            return self.get("email") or "Email"

        elif link_type == "phone":
            return self.get("phone") or "Phone"

        elif link_type == "anchor":
            anchor = self.get("anchor") or ""
            return anchor.lstrip("#") or "Link"

        return "Link"

    @property
    def is_external(self) -> bool:
        """Returns True only for 'url' type links."""
        return bool(self.get("link_type") == "url")

    @property
    def opens_new_tab(self) -> bool:
        """
        Returns True if the link should open in a new tab.

        Behavior:
        - If open_in_new_tab is explicitly True: opens in new tab
        - If open_in_new_tab is explicitly False: does NOT open in new tab
        - If open_in_new_tab is None (unset): defaults True for external URLs only

        Note: We use a tri-state approach where None means "auto" (use default).
        The BooleanBlock with required=False produces None when unchecked.
        """
        override = self.get("open_in_new_tab")

        # Explicit True or False takes precedence
        if override is True:
            return True
        if override is False:
            return False

        # Default: open in new tab only for external URLs
        return self.is_external

    @property
    def attrs(self) -> dict:
        """
        Returns a dict of HTML attributes for the link element.

        Includes:
        - target="_blank" if opens_new_tab
        - rel="noopener noreferrer" if opens_new_tab
        - data-contact-type for analytics (phone/email)
        """
        attrs = {}

        if self.opens_new_tab:
            attrs["target"] = "_blank"
            attrs["rel"] = "noopener noreferrer"

        link_type = self.get("link_type")
        if link_type == "phone":
            attrs["data-contact-type"] = "phone"
        elif link_type == "email":
            attrs["data-contact-type"] = "email"

        return attrs

    @property
    def attrs_str(self) -> str:
        """
        Returns attrs as a string suitable for template interpolation.

        Example: 'target="_blank" rel="noopener noreferrer"'
        Returns empty string if no attributes.
        """
        attrs = self.attrs
        if not attrs:
            return ""

        parts = [f'{key}="{value}"' for key, value in attrs.items()]
        return " ".join(parts)


# =============================================================================
# UniversalLinkBlock
# =============================================================================


class UniversalLinkBlock(blocks.StructBlock):
    """
    A universal link block that supports multiple link types with validation.

    Supported Types:
        - page: Internal Wagtail page link
        - url: External URL
        - path: Internal path (root-relative)
        - email: Email address (produces mailto: link)
        - phone: Phone number (produces tel: link)
        - anchor: Anchor/hash link within the page

    Validation:
        - Exactly one destination field must be populated based on link_type
        - Phone must contain at least one digit
        - Anchor must be a valid HTML ID (letter first, then alphanumeric/-/_)

    Usage in templates:
        <a href="{{ link.href }}" {{ link.attrs_str }}>{{ link.text }}</a>
    """

    link_type = blocks.ChoiceBlock(
        choices=LINK_TYPE_CHOICES,
        default="page",
        required=False,
        help_text="Select the type of link.",
    )

    # Destination fields - conditionally required based on link_type
    page = blocks.PageChooserBlock(
        required=False,
        help_text="Select an internal page.",
    )

    url = blocks.URLBlock(
        required=False,
        help_text="Enter an external URL (include https://).",
    )

    path = blocks.CharBlock(
        required=False,
        max_length=500,
        help_text="Enter an internal path starting with / (e.g., /portfolio/?type=bootroom).",
    )

    email = blocks.EmailBlock(
        required=False,
        help_text="Enter an email address.",
    )

    phone = blocks.CharBlock(
        required=False,
        max_length=30,
        help_text="Enter a phone number (e.g., +44 20 7946 0958).",
    )

    anchor = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Enter an anchor ID (e.g., 'contact' or '#contact').",
    )

    # Optional overrides
    link_text = blocks.CharBlock(
        required=False,
        max_length=255,
        help_text="Custom display text for the link (optional).",
    )

    open_in_new_tab = blocks.BooleanBlock(
        required=False,
        default=None,
        help_text="Force link to open in new tab. External URLs open in new tab by default.",
    )

    class Meta:
        icon = "link"
        label = "Link"
        value_class = UniversalLinkValue

    def __init__(self, *args, **kwargs):
        self._required_override = kwargs.get("required")
        super().__init__(*args, **kwargs)
        self._is_required = self._resolve_required()

    def _resolve_required(self) -> bool:
        required = getattr(self.meta, "required", None)
        if required is None:
            required = self._required_override
        if required is None:
            required = False
        return bool(required)

    def clean(self, value):
        """
        Validate that the correct destination field is populated based on link_type.

        Also validates:
        - Phone contains at least one digit
        - Anchor is a valid HTML ID format
        """
        cleaned = super().clean(value or {})
        if not self._is_required:
            raw_value = value or {}
            if not raw_value:
                return cleaned
            default_link_type = self.child_blocks["link_type"].get_default()
            if (
                _link_value_is_empty(cleaned)
                and raw_value.get("link_type") == default_link_type
            ):
                return cleaned
            if _link_value_is_empty(cleaned) and not raw_value.get("link_type"):
                return cleaned
        link_type = cleaned.get("link_type")
        errors = {}

        if self._is_required and link_type in (None, ""):
            raise blocks.StructBlockValidationError(
                {"link_type": ValidationError("Select a link type.")}
            )

        # Map link types to their required fields
        field_map = {
            "page": "page",
            "url": "url",
            "path": "path",
            "email": "email",
            "phone": "phone",
            "anchor": "anchor",
        }
        required_field = field_map.get(link_type)
        if required_field is None:
            raise blocks.StructBlockValidationError(
                {"link_type": ValidationError("Invalid link type.")}
            )
        field_value = cleaned.get(required_field)

        # Check that the required field is populated
        if not field_value:
            field_labels = {
                "page": "a page",
                "url": "a URL",
                "path": "a path",
                "email": "an email address",
                "phone": "a phone number",
                "anchor": "an anchor ID",
            }
            errors[required_field] = ValidationError(
                f"Please select {field_labels.get(link_type, 'a value')} for this link type."
            )

        # Additional validation for phone
        if link_type == "phone" and field_value:
            # Must contain at least one digit
            if not any(c.isdigit() for c in field_value):
                errors["phone"] = ValidationError(
                    "Phone number must contain at least one digit."
                )

        # Additional validation for internal path
        if link_type == "path" and field_value:
            trimmed = str(field_value).strip()
            parsed = urlparse(trimmed)
            if not trimmed.startswith("/") or trimmed.startswith("//"):
                errors["path"] = ValidationError(
                    "Internal paths must start with a single leading '/'."
                )
            elif parsed.scheme or parsed.netloc:
                errors["path"] = ValidationError(
                    "Internal paths must not include a scheme or domain."
                )

        # Additional validation for anchor (anchor link or optional page anchor)
        anchor_value = cleaned.get("anchor")
        if link_type in {"anchor", "page"} and anchor_value:
            anchor_id = anchor_value.lstrip("#")
            if not ANCHOR_PATTERN.match(anchor_id):
                errors["anchor"] = ValidationError(
                    "Anchor must start with a letter and contain only letters, "
                    "numbers, hyphens, and underscores."
                )
        elif link_type == "path" and anchor_value:
            errors["anchor"] = ValidationError(
                "Anchors are only supported for page or anchor link types."
            )

        if errors:
            raise blocks.StructBlockValidationError(errors)

        return cleaned


def _link_value_is_empty(value: dict) -> bool:
    """Return True when a link struct value should be treated as empty."""
    return (
        not any(
            value.get(field)
            for field in (
                "page",
                "url",
                "path",
                "email",
                "phone",
                "anchor",
                "link_text",
            )
        )
        and value.get("open_in_new_tab") is not True
    )


class CtaLinkBlock(blocks.StructBlock):
    """
    Reusable CTA struct used by content blocks.
    """

    label = blocks.CharBlock(
        required=True,
        max_length=80,
        help_text="CTA label text.",
    )
    link = UniversalLinkBlock(
        required=True,
        help_text="CTA destination.",
    )
    style = blocks.ChoiceBlock(
        choices=[
            ("primary", "Primary"),
            ("secondary", "Secondary"),
            ("outline", "Outline"),
        ],
        default="primary",
        required=False,
        help_text="Optional CTA style.",
    )

    class Meta:
        icon = "link"
        label = "CTA Link"
