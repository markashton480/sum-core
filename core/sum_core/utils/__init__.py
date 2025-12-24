"""
Name: Utils Package Init
Path: core/sum_core/utils/__init__.py
Purpose: Namespace for shared utility helpers within sum_core.
Family: Imported across sum_core modules and client projects for common helpers.
Dependencies: contact module for phone normalization.
"""

from sum_core.utils.contact import normalize_phone_href

__all__ = ["normalize_phone_href"]
