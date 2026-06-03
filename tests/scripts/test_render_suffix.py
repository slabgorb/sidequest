"""Tests for per-tier style-suffix selection in render_common.resolve_suffix.

Portraits prefer a portrait-specific suffix when the world declares one (so a
close-subject portrait gets a denser engraving suffix without the landscape's
open-sky / anti-moiré language); everything else uses the shared
positive_suffix. Falls back to the shared suffix when no portrait-specific one
is authored, so existing worlds are unaffected.
"""

from scripts.render_common import resolve_suffix


def test_portrait_uses_portrait_suffix_when_declared():
    vs = {
        "positive_suffix": "LANDSCAPE open-sky line",
        "portrait_positive_suffix": "PORTRAIT dense crosshatch",
    }
    assert resolve_suffix(vs, "portraits") == "PORTRAIT dense crosshatch"


def test_portrait_falls_back_to_shared_suffix_when_unset():
    vs = {"positive_suffix": "SHARED Tenniel line"}
    assert resolve_suffix(vs, "portraits") == "SHARED Tenniel line"


def test_portrait_falls_back_when_portrait_suffix_empty_string():
    # An empty portrait_positive_suffix is not a usable suffix — fall back.
    vs = {"positive_suffix": "SHARED", "portrait_positive_suffix": ""}
    assert resolve_suffix(vs, "portraits") == "SHARED"


def test_poi_always_uses_positive_suffix_even_when_portrait_declared():
    vs = {
        "positive_suffix": "LANDSCAPE",
        "portrait_positive_suffix": "PORTRAIT",
    }
    assert resolve_suffix(vs, "poi") == "LANDSCAPE"


def test_missing_all_suffixes_returns_empty():
    assert resolve_suffix({}, "portraits") == ""
    assert resolve_suffix({}, "poi") == ""
