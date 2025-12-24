"""
Name: Test Project Manage Script
Path: core/sum_core/test_project/manage.py
Purpose: Entry point for Django management commands in the sum_core test project.
Family: Used by developers and CI to run checks, migrations, and tests against sum_core.
Dependencies: django.core.management
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
    return None


if __name__ == "__main__":
    main()
