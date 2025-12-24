"""
Name: Navigation Effective Settings Resolver
Path: core/sum_core/navigation/services.py
Purpose: Provides "effective settings" that merge Navigation + Branding with clear precedence:
         Navigation overrides Branding when non-empty; otherwise fall back to Branding.
Family: Navigation System (Phase 1: Foundation)
Dependencies: sum_core.navigation.models, sum_core.branding.models, wagtail.models

Functions:
    - get_effective_footer_settings(site_or_request): Returns effective footer configuration
    - get_effective_header_settings(site_or_request): Returns effective header configuration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from wagtail.models import Site

if TYPE_CHECKING:
    from django.http import HttpRequest
    from sum_core.branding.models import SiteSettings
    from sum_core.navigation.models import FooterNavigation, HeaderNavigation


# =============================================================================
# Data Classes for Effective Settings
# =============================================================================


@dataclass
class EffectiveSocialLinks:
    """
    Canonical social media links with consistent keys.

    Keys are normalized regardless of underlying field names:
    - facebook, instagram, linkedin, youtube, x, tiktok
    """

    facebook: str = ""
    instagram: str = ""
    linkedin: str = ""
    youtube: str = ""
    x: str = ""
    tiktok: str = ""

    def to_dict(self) -> dict[str, str]:
        """Return social links as a dictionary."""
        return {
            "facebook": self.facebook,
            "instagram": self.instagram,
            "linkedin": self.linkedin,
            "youtube": self.youtube,
            "x": self.x,
            "tiktok": self.tiktok,
        }


@dataclass
class EffectiveFooterSettings:
    """
    Effective footer settings with override→fallback precedence.

    Fields:
        tagline: Footer tagline (FooterNavigation override, Branding fallback)
        copyright_text: Footer copyright text (FooterNavigation only)
        social: Canonical social media links dict
        company_name: From Branding SiteSettings
        phone_number: From Branding SiteSettings
        email: From Branding SiteSettings
        address: From Branding SiteSettings
    """

    tagline: str = ""
    copyright_text: str = ""
    social: dict[str, str] = field(default_factory=dict)
    company_name: str = ""
    phone_number: str = ""
    email: str = ""
    address: str = ""


@dataclass
class EffectiveCTAConfig:
    """
    Effective CTA configuration for header or mobile.

    Fields:
        enabled: Whether the CTA is enabled
        text: CTA button text
        link: The link block value (StreamValue), or None if not set
    """

    enabled: bool = True
    text: str = ""
    link: Any = None


@dataclass
class EffectiveHeaderSettings:
    """
    Effective header settings combining Navigation + Branding.

    Fields:
        show_phone_in_header: Toggle from HeaderNavigation
        phone_number: From Branding SiteSettings (None if show_phone disabled)
        header_cta: Header CTA configuration
        mobile_cta_enabled: Mobile sticky CTA bar enabled
        mobile_cta_phone_enabled: Show phone in mobile CTA
        mobile_cta_button: Mobile CTA button configuration
        menu_items: The menu items StreamValue from HeaderNavigation
    """

    show_phone_in_header: bool = True
    phone_number: str | None = None
    header_cta: EffectiveCTAConfig = field(default_factory=EffectiveCTAConfig)
    mobile_cta_enabled: bool = True
    mobile_cta_phone_enabled: bool = True
    mobile_cta_button: EffectiveCTAConfig = field(default_factory=EffectiveCTAConfig)
    menu_items: Any = None


# =============================================================================
# Helper Functions
# =============================================================================


def _resolve_site(site_or_request: Site | HttpRequest) -> Site:
    """
    Resolve a Site from either a Site instance or HttpRequest.

    Args:
        site_or_request: Either a Wagtail Site instance or Django HttpRequest

    Returns:
        The resolved Site instance
    """
    if isinstance(site_or_request, Site):
        return site_or_request
    # Assume it's a request-like object
    return Site.find_for_request(site_or_request)


def _get_branding_settings(site: Site) -> SiteSettings:
    """
    Get Branding SiteSettings for a site.

    Args:
        site: The Wagtail Site

    Returns:
        SiteSettings instance for the site
    """
    from sum_core.branding.models import SiteSettings

    return SiteSettings.for_site(site)


def _get_header_navigation(site: Site) -> HeaderNavigation:
    """
    Get HeaderNavigation for a site.

    Args:
        site: The Wagtail Site

    Returns:
        HeaderNavigation instance for the site
    """
    from sum_core.navigation.models import HeaderNavigation

    return HeaderNavigation.for_site(site)


def _get_footer_navigation(site: Site) -> FooterNavigation:
    """
    Get FooterNavigation for a site.

    Args:
        site: The Wagtail Site

    Returns:
        FooterNavigation instance for the site
    """
    from sum_core.navigation.models import FooterNavigation

    return FooterNavigation.for_site(site)


def _is_non_empty(value: str | None) -> bool:
    """
    Check if a string value is non-empty (not None and not whitespace-only).

    Args:
        value: The string value to check

    Returns:
        True if value is non-empty, False otherwise
    """
    return bool(value and value.strip())


# =============================================================================
# Public API
# =============================================================================


def get_effective_footer_settings(
    site_or_request: Site | HttpRequest,
) -> EffectiveFooterSettings:
    """
    Get effective footer settings with override→fallback precedence.

    Precedence rule: Navigation overrides Branding when non-empty;
    otherwise fall back to Branding.

    Args:
        site_or_request: Either a Wagtail Site instance or Django HttpRequest

    Returns:
        EffectiveFooterSettings with canonical keys and merged values

    Field mappings:
        - tagline: FooterNavigation.tagline → SiteSettings.tagline
        - copyright_text: FooterNavigation.copyright_text
        - social.facebook: FooterNavigation.social_facebook → SiteSettings.facebook_url
        - social.instagram: FooterNavigation.social_instagram → SiteSettings.instagram_url
        - social.linkedin: FooterNavigation.social_linkedin → SiteSettings.linkedin_url
        - social.youtube: FooterNavigation.social_youtube → SiteSettings.youtube_url
        - social.x: FooterNavigation.social_x → SiteSettings.twitter_url
        - social.tiktok: SiteSettings.tiktok_url (no FooterNavigation field)
    """
    site = _resolve_site(site_or_request)
    branding = _get_branding_settings(site)
    footer_nav = _get_footer_navigation(site)

    # Resolve tagline with precedence
    tagline = (
        footer_nav.tagline
        if _is_non_empty(footer_nav.tagline)
        else (branding.tagline or "")
    )

    # Resolve social links with precedence
    social = EffectiveSocialLinks(
        facebook=(
            footer_nav.social_facebook
            if _is_non_empty(footer_nav.social_facebook)
            else (branding.facebook_url or "")
        ),
        instagram=(
            footer_nav.social_instagram
            if _is_non_empty(footer_nav.social_instagram)
            else (branding.instagram_url or "")
        ),
        linkedin=(
            footer_nav.social_linkedin
            if _is_non_empty(footer_nav.social_linkedin)
            else (branding.linkedin_url or "")
        ),
        youtube=(
            footer_nav.social_youtube
            if _is_non_empty(footer_nav.social_youtube)
            else (branding.youtube_url or "")
        ),
        # X/Twitter: FooterNavigation uses social_x, Branding uses twitter_url
        x=(
            footer_nav.social_x
            if _is_non_empty(footer_nav.social_x)
            else (branding.twitter_url or "")
        ),
        # TikTok: Always from Branding (FooterNavigation has no tiktok field)
        tiktok=branding.tiktok_url or "",
    )

    return EffectiveFooterSettings(
        tagline=tagline,
        copyright_text=footer_nav.copyright_text or "",
        social=social.to_dict(),
        company_name=branding.company_name or "",
        phone_number=branding.phone_number or "",
        email=branding.email or "",
        address=branding.address or "",
    )


def get_effective_header_settings(
    site_or_request: Site | HttpRequest,
) -> EffectiveHeaderSettings:
    """
    Get effective header settings combining Navigation + Branding.

    Args:
        site_or_request: Either a Wagtail Site instance or Django HttpRequest

    Returns:
        EffectiveHeaderSettings with header configuration

    Notes:
        - phone_number is only included when show_phone_in_header is True
        - CTA configurations are passed through from HeaderNavigation
    """
    site = _resolve_site(site_or_request)
    branding = _get_branding_settings(site)
    header_nav = _get_header_navigation(site)

    # Phone number is only included when show_phone_in_header is True
    phone_number = branding.phone_number if header_nav.show_phone_in_header else None

    # Header CTA configuration
    header_cta = EffectiveCTAConfig(
        enabled=header_nav.header_cta_enabled,
        text=header_nav.header_cta_text or "",
        link=header_nav.header_cta_link if header_nav.header_cta_link else None,
    )

    # Mobile CTA button configuration
    mobile_cta_button = EffectiveCTAConfig(
        enabled=header_nav.mobile_cta_button_enabled,
        text=header_nav.mobile_cta_button_text or "",
        link=(
            header_nav.mobile_cta_button_link
            if header_nav.mobile_cta_button_link
            else None
        ),
    )

    return EffectiveHeaderSettings(
        show_phone_in_header=header_nav.show_phone_in_header,
        phone_number=phone_number,
        header_cta=header_cta,
        mobile_cta_enabled=header_nav.mobile_cta_enabled,
        mobile_cta_phone_enabled=header_nav.mobile_cta_phone_enabled,
        mobile_cta_button=mobile_cta_button,
        menu_items=header_nav.menu_items if header_nav.menu_items else None,
    )
