import yaml

from scripts.migrate_poi_backdrop_lod import migrate_history


def test_legacy_single_visual_prompt_migrates(tmp_path) -> None:
    src = tmp_path / "history.yaml"
    src.write_text(yaml.safe_dump({
        "chapters": [{
            "name": "Present Age",
            "points_of_interest": [
                {"slug": "lookout", "visual_prompt": "a stone watchtower"},
            ],
        }],
    }))
    migrate_history(src, in_place=True)
    data = yaml.safe_load(src.read_text())
    poi = data["chapters"][0]["points_of_interest"][0]
    assert poi["visual_prompt"]["solo"] == "a stone watchtower"
    assert poi["visual_prompt"]["backdrop"].startswith("TODO:")
