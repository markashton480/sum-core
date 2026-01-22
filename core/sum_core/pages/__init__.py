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
    if name == "PortfolioIndexPage":
        from sum_core.pages.portfolio import PortfolioIndexPage

        return PortfolioIndexPage
    if name == "CaseStudyPage":
        from sum_core.pages.portfolio import CaseStudyPage

        return CaseStudyPage
    if name == "Category":
        from sum_core.pages.blog import Category

        return Category
    if name == "BlogIndexPage":
        from sum_core.pages.blog import BlogIndexPage

        return BlogIndexPage
    if name == "BlogPostPage":
        from sum_core.pages.blog import BlogPostPage

        return BlogPostPage
    if name == "LegalPage":
        from sum_core.pages.legal import LegalPage

        return LegalPage
    if name == "HomePage":
        from sum_core.pages.home import HomePage

        return HomePage
    if name == "HomePageHeroCTA":
        from sum_core.pages.home import HomePageHeroCTA

        return HomePageHeroCTA
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "StandardPage",
    "ServiceIndexPage",
    "ServicePage",
    "PortfolioIndexPage",
    "CaseStudyPage",
    "Category",
    "BlogIndexPage",
    "BlogPostPage",
    "LegalPage",
    "HomePage",
    "HomePageHeroCTA",
]

default_app_config = "sum_core.pages.apps.PagesConfig"
