"""RED — Story 101-8 (orchestrator side): ``render_common.slugify`` adopts the
unified NFKD-fold rule.

``scripts/render_common.py:slugify`` (rule 1) is the render-script rule that
writes ``<slug>.png`` to R2. Uniquely among the three rules it currently KEEPS
non-ASCII letters verbatim — so a diacritic name produces a non-ASCII R2 object
key ("srárný_…"), the worst case for CDN/tooling. Story 101-8 (session decision,
ratified by Keith) unifies all three rules behind one NFKD-fold core:
``unicodedata.normalize("NFKD", …)`` + strip combining marks, so diacritics fold
to ASCII base letters. ASCII output is UNCHANGED.

Golden vector ``"Srárný Fyzioloniązka"`` matches the server + daemon suites so
the three repos cannot drift on the fold contract. Run:
    cd <orchestrator-root> && uv run pytest scripts/tests/test_101_8_render_common_slug.py
"""

from __future__ import annotations

import pytest

from scripts.render_common import slugify

_DIACRITIC = "Srárný Fyzioloniązka"


# --- AC3: ASCII output unchanged (measured current values; green now + after) ---
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Jane Doe", "jane_doe"),
        ("Old Sten", "old_sten"),
        ("Lady Of The Hall", "lady_of_the_hall"),
        ("", ""),
    ],
)
def test_render_common_slugify_ascii_unchanged(raw: str, expected: str) -> None:
    assert slugify(raw) == expected


# --- AC1: NFKD fold of non-ASCII (RED today — today KEEPS non-ASCII verbatim) ---
def test_render_common_slugify_folds_diacritics() -> None:
    # today: "srárný_fyzioloniązka" (non-ASCII kept!)  →  fold: ASCII base letters.
    assert slugify(_DIACRITIC) == "srarny_fyzioloniazka"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("café", "cafe"),
        ("naïve", "naive"),
        ("Núñez", "nunez"),
    ],
)
def test_render_common_slugify_common_diacritics_fold(raw: str, expected: str) -> None:
    assert slugify(raw) == expected


def test_render_side_matches_consumer_portrait_rule() -> None:
    # The render-side R2 key must match the server/daemon portrait slug so the
    # asset the render script writes is the asset the reference page requests.
    assert slugify(_DIACRITIC) == "srarny_fyzioloniazka"
