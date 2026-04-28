from __future__ import annotations

from screen_record.models import CaptureRegion
from screen_record.ui.region_selector import clamp_region


def test_region_clamps_to_bounds() -> None:
    bounds = CaptureRegion(left=0, top=0, width=100, height=80)
    region = CaptureRegion(left=-10, top=-5, width=150, height=120)

    clamped = clamp_region(region, bounds)

    assert clamped.left == 0
    assert clamped.top == 0
    assert clamped.width == 100
    assert clamped.height == 80
