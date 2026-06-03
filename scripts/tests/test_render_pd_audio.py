import pytest

from scripts.render_pd_audio import (
    UncataloguedTrackError,
    collect_demand,
    plan_renders,
)

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
    assert collect_demand([audio_yaml]) == {"Satie - Gymnopedie No.1.ogg"}


def test_plan_renders_skips_already_in_r2():
    demand = {"Satie - Gymnopedie No.1.ogg", "Chopin - Nocturne Op.9 No.2 in E-flat major.ogg"}
    already = {"genre_packs/assets/audio/classical_pd/Satie - Gymnopedie No.1.ogg"}
    todo = plan_renders(demand, CATALOG, already_keys=already)
    assert [e["out_name"] for e in todo] == ["Chopin - Nocturne Op.9 No.2 in E-flat major.ogg"]


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
        plan_renders(demand, CATALOG, already_keys=set())
    assert "Mystery - Unknown.ogg" in str(exc.value)


def test_main_returns_1_on_uncatalogued_demand_without_traceback():
    # tea_and_murder has demanded tracks absent from the catalog (KNOWN GAPS):
    # main() must translate the loud UncataloguedTrackError into a clean exit 1,
    # not let it propagate as an unhandled traceback.
    from scripts.render_pd_audio import main
    assert main(["--pack", "tea_and_murder", "--dry-run"]) == 1
