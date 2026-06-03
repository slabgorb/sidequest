import pytest

from scripts.render_pd_audio import (
    UncataloguedTrackError,
    collect_demand,
    plan_renders,
)

CLASSICAL_PREFIX = "assets/audio/classical_pd/"
CLASSICAL_REL = "genre_packs/assets/audio/classical_pd"
RAGTIME_PREFIX = "assets/audio/ragtime_pd/"
RAGTIME_REL = "genre_packs/assets/audio/ragtime_pd"

CATALOG = {
    "Satie - Gymnopedie No.1.ogg": {
        "out_name": "Satie - Gymnopedie No.1.ogg",
        "title": "Gymnopédie No. 1",
        "source_url": "https://example/g1.mid",
    },
    "Chopin - Nocturne Op.9 No.2 in E-flat major.ogg": {
        "out_name": "Chopin - Nocturne Op.9 No.2 in E-flat major.ogg",
        "title": "Nocturne",
        "source_url": "https://example/noc.mid",
    },
}


def test_collect_demand_extracts_shared_classical_pd_filenames():
    audio_yaml = {
        "mood_tracks": {
            "exploration": [
                {"path": "assets/audio/classical_pd/Satie - Gymnopedie No.1.ogg",
                 "title": "x", "bpm": 60},
                {"path": "audio/music/local.ogg", "title": "y", "bpm": 90},  # pack-local: ignored
            ]
        }
    }
    assert collect_demand(
        [audio_yaml], shared_audio_prefix=CLASSICAL_PREFIX
    ) == {"Satie - Gymnopedie No.1.ogg"}


def test_collect_demand_for_non_classical_bucket():
    # A ragtime_pd run must pick up ragtime paths and ignore classical_pd +
    # pack-local paths (which belong to other buckets).
    audio_yaml = {
        "mood_tracks": {
            "saloon": [
                {"path": "assets/audio/ragtime_pd/Joplin - Maple Leaf Rag.ogg",
                 "title": "rag", "bpm": 80},
                {"path": "assets/audio/classical_pd/Satie - Gymnopedie No.1.ogg",
                 "title": "classical: ignored", "bpm": 60},
                {"path": "audio/music/local.ogg", "title": "pack-local: ignored", "bpm": 90},
            ]
        }
    }
    assert collect_demand(
        [audio_yaml], shared_audio_prefix=RAGTIME_PREFIX
    ) == {"Joplin - Maple Leaf Rag.ogg"}


def test_plan_renders_skips_already_in_r2():
    demand = {"Satie - Gymnopedie No.1.ogg", "Chopin - Nocturne Op.9 No.2 in E-flat major.ogg"}
    already = {"genre_packs/assets/audio/classical_pd/Satie - Gymnopedie No.1.ogg"}
    todo = plan_renders(demand, CATALOG, already_keys=already, shared_rel=CLASSICAL_REL)
    assert [e["out_name"] for e in todo] == ["Chopin - Nocturne Op.9 No.2 in E-flat major.ogg"]


def test_plan_renders_builds_keys_with_bucket_rel():
    # plan_renders must form already-keys with the passed shared_rel so a
    # ragtime entry already in R2 is correctly skipped under its own prefix.
    rag_catalog = {
        "Joplin - Maple Leaf Rag.ogg": {
            "out_name": "Joplin - Maple Leaf Rag.ogg",
            "title": "Maple Leaf Rag",
            "source_url": "https://example/mlr.mid",
        },
        "Joplin - The Entertainer.ogg": {
            "out_name": "Joplin - The Entertainer.ogg",
            "title": "The Entertainer",
            "source_url": "https://example/ent.mid",
        },
    }
    demand = {"Joplin - Maple Leaf Rag.ogg", "Joplin - The Entertainer.ogg"}
    already = {"genre_packs/assets/audio/ragtime_pd/Joplin - Maple Leaf Rag.ogg"}
    todo = plan_renders(demand, rag_catalog, already_keys=already, shared_rel=RAGTIME_REL)
    assert [e["out_name"] for e in todo] == ["Joplin - The Entertainer.ogg"]


def test_composer_entries_strip_ogg_suffix_for_composer_outname():
    from scripts.render_pd_audio import _composer_entries
    todo = [{"out_name": "Satie - Gymnopedie No.1.ogg", "title": "G1", "source_url": "x.mid"}]
    out = _composer_entries(todo)
    assert out[0]["out_name"] == "Satie - Gymnopedie No.1"   # composer re-appends .ogg
    assert todo[0]["out_name"] == "Satie - Gymnopedie No.1.ogg"  # originals untouched
    assert out[0]["source_url"] == "x.mid"  # other fields preserved


def test_plan_renders_fails_loud_on_uncatalogued_demand():
    demand = {"Mystery - Unknown.ogg"}
    with pytest.raises(UncataloguedTrackError) as exc:
        plan_renders(demand, CATALOG, already_keys=set(), shared_rel=CLASSICAL_REL)
    assert "Mystery - Unknown.ogg" in str(exc.value)


def test_main_returns_1_on_uncatalogued_demand_without_traceback(monkeypatch):
    # When a pack demands a shared track that has no catalog entry, main() must
    # translate the loud UncataloguedTrackError into a clean exit 1, not let it
    # propagate as an unhandled traceback. We synthesize uncatalogued demand
    # (rather than depend on a live pack's KNOWN GAPS, which get filled over
    # time) by stubbing the loaders.
    import scripts.render_pd_audio as mod

    monkeypatch.setattr(mod, "load_catalog", lambda path: {})  # empty supply
    monkeypatch.setattr(mod, "_audio_configs", lambda pack: [
        {"mood_tracks": {"m": [
            {"path": "assets/audio/classical_pd/Nobody - Uncatalogued.ogg"},
        ]}}
    ])
    monkeypatch.setattr(mod, "_already_keys", lambda: set())

    assert mod.main(["--dry-run"]) == 1
