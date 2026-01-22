"""
Test project home app - imports HomePage from sum_core.

This module re-exports the HomePage model from sum_core.pages.home
so that the test project's 'home' app provides the model for Django's
app registry while the actual implementation lives in sum_core.
"""

from sum_core.pages.home import HomePage, HomePageHeroCTA

__all__ = ["HomePage", "HomePageHeroCTA"]
