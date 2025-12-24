"""
Name: Navigation Package
Path: core/sum_core/navigation/__init__.py
Purpose: Namespace for navigation-related components (menus, links, etc.)
Family: SUM Platform Navigation System

Usage:
    # Import blocks directly from their module
    from sum_core.navigation.blocks import (
        MenuItemBlock,
        SubmenuItemBlock,
        FooterLinkSectionBlock,
    )

    # Import models directly from their module
    from sum_core.navigation.models import (
        HeaderNavigation,
        FooterNavigation,
    )

    # Import effective settings resolver from services
    from sum_core.navigation.services import (
        get_effective_footer_settings,
        get_effective_header_settings,
    )

Note: Direct imports from sum_core.navigation are not provided to avoid
circular import issues during Django app loading.
"""

default_app_config = "sum_core.navigation.apps.NavigationConfig"
