"""
Name: Pages Package Init
Path: core/sum_core/pages/__init__.py
Purpose: Namespace for Wagtail page models within sum_core.
Family: Used by client projects and test_project for shared page implementations.
Dependencies: StandardPage from standard module (imported lazily).

Note: Model imports are intentionally deferred to avoid Django app registry issues
during startup. Import StandardPage directly from sum_core.pages.standard or
access via this module after Django setup is complete.
"""


def __getattr__(name: str):
    """Lazy import for page models to avoid app registry issues."""
    if name == "StandardPage":
        from sum_core.pages.standard import StandardPage

        return StandardPage
    if name == "ServiceIndexPage":
        from sum_core.pages.services import ServiceIndexPage

        return ServiceIndexPage
    if name == "ServicePage":
        from sum_core.pages.services import ServicePage

        return ServicePage
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "StandardPage",
    "ServiceIndexPage",
    "ServicePage",
]
