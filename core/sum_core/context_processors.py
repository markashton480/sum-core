from __future__ import annotations

from django.conf import settings


def visual_test(request) -> dict[str, object]:
    return {
        "VISUAL_TEST": bool(getattr(settings, "VISUAL_TEST", False)),
        "VISUAL_TEST_FROZEN_ISO": getattr(settings, "VISUAL_TEST_FROZEN_ISO", ""),
        "VISUAL_TEST_FROZEN_YEAR": int(getattr(settings, "VISUAL_TEST_FROZEN_YEAR", 0)),
    }
