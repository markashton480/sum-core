"""
HomePage model for this client project.

Re-exports the HomePage from sum_core.pages. The actual implementation is in
sum_core, which ships to clients via pip install sum-core.

This module exists so the 'home' app is properly registered in INSTALLED_APPS
and Django's model discovery finds the HomePage model.
"""

from sum_core.pages.home import HomePage, HomePageHeroCTA

__all__ = ["HomePage", "HomePageHeroCTA"]
