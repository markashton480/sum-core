"""
Name: Theme Presets
Path: core/sum_core/branding/theme_presets.py
Purpose: Define internal theme presets for SiteSettings one-click application.
Family: Used by SiteSettings admin form to prepopulate branding fields.
Dependencies: Standard library (dataclasses, typing) only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemePreset:
    """Defines a theme preset with colours and font recommendations."""

    key: str
    label: str
    primary_color: str
    secondary_color: str
    accent_color: str
    background_color: str
    surface_color: str
    surface_elevated_color: str
    text_color: str
    text_light_color: str
    heading_font: str
    body_font: str


THEME_PRESETS: dict[str, ThemePreset] = {
    "premium-trade": ThemePreset(
        key="premium-trade",
        label="Premium Trade",
        primary_color="#1e3a5f",
        secondary_color="#0f172a",
        accent_color="#f59e0b",
        background_color="#ffffff",
        surface_color="#f8fafc",
        surface_elevated_color="#f1f5f9",
        text_color="#0f172a",
        text_light_color="#64748b",
        heading_font="Montserrat",
        body_font="Open Sans",
    ),
    "professional-blue": ThemePreset(
        key="professional-blue",
        label="Professional Blue",
        primary_color="#2563eb",
        secondary_color="#1e40af",
        accent_color="#f97316",
        background_color="#ffffff",
        surface_color="#f8fafc",
        surface_elevated_color="#f1f5f9",
        text_color="#0f172a",
        text_light_color="#64748b",
        heading_font="Poppins",
        body_font="Inter",
    ),
    "modern-green": ThemePreset(
        key="modern-green",
        label="Modern Green",
        primary_color="#059669",
        secondary_color="#064e3b",
        accent_color="#fbbf24",
        background_color="#ffffff",
        surface_color="#f8fafc",
        surface_elevated_color="#ecfdf5",
        text_color="#0f172a",
        text_light_color="#64748b",
        heading_font="DM Sans",
        body_font="Source Sans 3",
    ),
    "warm-earth": ThemePreset(
        key="warm-earth",
        label="Warm Earth",
        primary_color="#92400e",
        secondary_color="#78350f",
        accent_color="#dc2626",
        background_color="#fffbeb",
        surface_color="#fef3c7",
        surface_elevated_color="#fde68a",
        text_color="#78350f",
        text_light_color="#92400e",
        heading_font="Playfair Display",
        body_font="Lato",
    ),
    "clean-slate": ThemePreset(
        key="clean-slate",
        label="Clean Slate",
        primary_color="#374151",
        secondary_color="#1f2937",
        accent_color="#6366f1",
        background_color="#f9fafb",
        surface_color="#f3f4f6",
        surface_elevated_color="#e5e7eb",
        text_color="#111827",
        text_light_color="#6b7280",
        heading_font="Work Sans",
        body_font="Roboto",
    ),
}


def get_theme_preset_choices() -> list[tuple[str, str]]:
    """Return choices for a form field: empty option + 5 presets."""
    choices: list[tuple[str, str]] = [("", "---------")]
    choices.extend((preset.key, preset.label) for preset in THEME_PRESETS.values())
    return choices
