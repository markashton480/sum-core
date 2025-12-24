"""
Name: Contact Utilities
Path: core/sum_core/utils/contact.py
Purpose: Shared utilities for contact-related data normalisation.
Family: Utility functions shared across sum_core.
Dependencies: re (standard library)
"""

import re

# Phone number cleaning pattern - strips non-digits except leading +
_PHONE_CLEAN_PATTERN = re.compile(r"[^\d+]")


def normalize_phone_href(phone_number: str | None) -> str:
    """
    Normalize a phone number to tel: href format.

    Removes all non-digit characters except a leading '+'.

    Args:
        phone_number: Raw phone number string (e.g. "+44 (0)20 7946 0958")

    Returns:
        Normalized tel: URI (e.g. "tel:+442079460958")
        Returns empty string if phone_number is empty/None.

    Examples:
        >>> normalize_phone_href("+44 20 7946 0958")
        'tel:+442079460958'
        >>> normalize_phone_href("020-7946-0958")
        'tel:02079460958'
        >>> normalize_phone_href(None)
        ''
    """
    if not phone_number:
        return ""

    # Strip non-digits except leading +
    if phone_number.startswith("+"):
        cleaned = "+" + _PHONE_CLEAN_PATTERN.sub("", phone_number[1:])
    else:
        cleaned = _PHONE_CLEAN_PATTERN.sub("", phone_number)

    return f"tel:{cleaned}" if cleaned else ""
