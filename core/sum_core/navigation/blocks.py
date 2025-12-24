"""
Name: Navigation Blocks
Path: core/sum_core/navigation/blocks.py
Purpose: Define reusable StreamField blocks for navigation menus (header/footer).
Family: Navigation System (Phase 1: Foundation)
Dependencies: wagtail.blocks, sum_core.blocks.UniversalLinkBlock

Blocks defined:
    - SubmenuItemBlock: A single submenu item (label + link)
    - MenuItemBlock: A top-level menu item (label + link + optional children)
    - FooterLinkSectionBlock: A footer section (title + list of links)

Constraints:
    - MenuItemBlock.children: max 8 submenu items
    - FooterLinkSectionBlock.links: max 10 links
    - Max 8 top-level menu items is enforced at the HeaderNavigation level (NAV-003)
"""

# Import UniversalLinkBlock from sum_core.blocks (shared primitive)
from sum_core.blocks import UniversalLinkBlock
from wagtail import blocks

# =============================================================================
# SubSubmenuItemBlock
# =============================================================================


class SubSubmenuItemBlock(blocks.StructBlock):
    """
    A second-level submenu item (nested within a SubmenuItem).

    Fields:
        label: Display text for the menu item (max 50 chars)
        link: Universal link destination
    """

    label = blocks.CharBlock(
        max_length=50,
        required=True,
        help_text="Menu item label (max 50 characters).",
    )

    link = UniversalLinkBlock(
        required=True,
        help_text="Link destination for this menu item.",
    )

    class Meta:
        icon = "link"
        label = "Sub-submenu Item"


# =============================================================================
# SubmenuItemBlock
# =============================================================================


class SubmenuItemBlock(blocks.StructBlock):
    """
    A single submenu item within a dropdown menu.

    Fields:
        label: Display text for the menu item (max 50 chars)
        link: Universal link destination (page, URL, email, phone, or anchor)
    """

    label = blocks.CharBlock(
        max_length=50,
        required=True,
        help_text="Menu item label (max 50 characters).",
    )

    link = UniversalLinkBlock(
        required=True,
        help_text="Link destination for this menu item.",
    )

    class Meta:
        icon = "indent"  # Changed icon to distinguish from simple link
        label = "Submenu Item"

    children = blocks.ListBlock(
        SubSubmenuItemBlock(),
        required=False,
        max_num=8,
        help_text="Nested menu items (optional, max 8 items).",
    )


# =============================================================================
# MenuItemBlock
# =============================================================================


class MenuItemBlock(blocks.StructBlock):
    """
    A top-level menu item for the header navigation.

    Can optionally contain child submenu items (dropdown menu).

    Fields:
        label: Display text for the menu item (max 50 chars)
        link: Universal link destination (page, URL, email, phone, or anchor)
        children: Optional list of submenu items (max 8)

    Constraints:
        - Maximum 8 submenu items per menu item
    """

    label = blocks.CharBlock(
        max_length=50,
        required=True,
        help_text="Menu item label (max 50 characters).",
    )

    link = UniversalLinkBlock(
        required=True,
        help_text="Link destination for this menu item.",
    )

    children = blocks.ListBlock(
        SubmenuItemBlock(),
        required=False,
        max_num=8,
        help_text="Submenu items (optional, max 8 items).",
    )

    class Meta:
        icon = "list-ul"
        label = "Menu Item"


# =============================================================================
# FooterLinkSectionBlock
# =============================================================================


class FooterLinkSectionBlock(blocks.StructBlock):
    """
    A footer section containing a title and a list of links.

    Used to organize footer content into columns (e.g., "Company", "Services").

    Fields:
        title: Section heading (max 50 chars)
        links: List of universal links (required, max 10)

    Constraints:
        - Maximum 10 links per footer section
    """

    title = blocks.CharBlock(
        max_length=50,
        required=True,
        help_text="Section title (max 50 characters).",
    )

    links = blocks.ListBlock(
        UniversalLinkBlock(),
        required=True,
        max_num=10,
        help_text="Links in this section (max 10 links).",
    )

    class Meta:
        icon = "doc-full"
        label = "Footer Link Section"
