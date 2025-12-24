"""
Name: Theme Discovery & Registry (Theme System v1)
Path: core/sum_core/themes/__init__.py
Purpose: Deprecated theme manifest helpers (tooling should use repo-root `themes/` via sum_cli).
Family: Themes / Toolchain
Dependencies: stdlib only
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ThemeNotFoundError(Exception):
    """Raised when a requested theme slug cannot be found."""


class ThemeValidationError(ValueError):
    """Raised when a theme exists but is invalid (bad manifest or missing files)."""


@dataclass(frozen=True, slots=True)
class ThemeManifest:
    """Type-safe theme metadata loaded from theme.json."""

    slug: str
    name: str
    description: str
    version: str

    def validate(self) -> None:
        if not self.slug:
            raise ValueError("slug cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.version:
            raise ValueError("version cannot be empty")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ThemeManifest:
        return cls(
            slug=str(data.get("slug", "")).strip(),
            name=str(data.get("name", "")).strip(),
            description=str(data.get("description", "")).strip(),
            version=str(data.get("version", "")).strip(),
        )


THEMES_DIR: Path = Path(__file__).resolve().parent


def _read_manifest(theme_dir: Path) -> ThemeManifest:
    manifest_path = theme_dir / "theme.json"
    if not manifest_path.is_file():
        raise ThemeValidationError(f"Missing theme manifest: {manifest_path}")

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ThemeValidationError(
            f"Invalid JSON in theme manifest: {manifest_path} ({e})"
        ) from e

    if not isinstance(data, dict):
        raise ThemeValidationError(f"Theme manifest must be an object: {manifest_path}")

    manifest = ThemeManifest.from_dict(data)
    manifest.validate()

    # Hard validation: directory name must match manifest slug
    if manifest.slug != theme_dir.name:
        raise ThemeValidationError(
            f"Theme slug mismatch: dir='{theme_dir.name}' manifest='{manifest.slug}'"
        )

    return manifest


def discover_themes(themes_dir: Path | None = None) -> list[ThemeManifest]:
    """
    Discover themes by scanning `<themes_dir>/*/theme.json`.

    Notes:
    - Skips directories without theme.json
    - Skips invalid manifests (bad JSON, missing required fields, slug mismatch)
    """
    root = themes_dir or THEMES_DIR
    if not root.exists():
        return []

    manifests: list[ThemeManifest] = []
    for theme_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if theme_dir.name.startswith("__"):
            continue
        try:
            manifests.append(_read_manifest(theme_dir))
        except ThemeValidationError:
            # Discovery is tolerant by design: invalid themes are ignored.
            continue
    return manifests


def list_themes() -> list[ThemeManifest]:
    """Return all discovered themes sorted by slug."""
    themes = discover_themes()
    return sorted(themes, key=lambda t: t.slug)


def get_theme_dir(slug: str) -> Path:
    """Return the filesystem directory for a theme slug."""
    theme_dir = THEMES_DIR / slug
    if not theme_dir.is_dir():
        raise ThemeNotFoundError(f"Theme '{slug}' not found")
    return theme_dir


def get_theme(slug: str) -> ThemeManifest:
    """Return a validated ThemeManifest for the theme slug."""
    theme_dir = get_theme_dir(slug)
    try:
        return _read_manifest(theme_dir)
    except ThemeValidationError as e:
        # Keep a stable exception type for callers (CLI/tests).
        raise ThemeValidationError(str(e)) from e


def get_theme_template_dir(slug: str) -> Path:
    """Return the theme's templates directory (e.g. .../templates)."""
    theme_dir = get_theme_dir(slug)
    templates_dir = theme_dir / "templates"
    if not templates_dir.is_dir():
        raise ThemeValidationError(
            f"Theme '{slug}' missing templates dir: {templates_dir}"
        )
    return templates_dir


def get_theme_static_dir(slug: str) -> Path:
    """Return the theme's static directory (e.g. .../static)."""
    theme_dir = get_theme_dir(slug)
    static_dir = theme_dir / "static"
    if not static_dir.is_dir():
        raise ThemeValidationError(f"Theme '{slug}' missing static dir: {static_dir}")
    return static_dir


__all__ = [
    "ThemeManifest",
    "ThemeNotFoundError",
    "ThemeValidationError",
    "discover_themes",
    "list_themes",
    "get_theme",
    "get_theme_dir",
    "get_theme_template_dir",
    "get_theme_static_dir",
]

"""
Deprecated note:

Themes are *not* canonical inside `sum_core`. Canonical theme sources live at repo root
`themes/` per Theme Architecture Spec v1, and are copied into client projects at init-time.

This module remains only for backwards compatibility with older tooling/tests.
"""
