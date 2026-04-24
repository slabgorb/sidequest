import yaml

from scripts.migrate_visual_tag_overrides import migrate_world


def test_override_migrates_to_matching_archetype(tmp_path) -> None:
    genre_root = tmp_path / "genre_packs" / "testgenre"
    (genre_root / "worlds" / "testworld").mkdir(parents=True)
    (genre_root / "worlds" / "testworld" / "visual_style.yaml").write_text(
        yaml.safe_dump({
            "visual_tag_overrides": {
                "tavern": "low-ceilinged roadhouse, amber lantern-glow",
            },
        }),
    )
    (genre_root / "places.yaml").write_text(
        yaml.safe_dump({
            "tavern": {
                "landmark": {"solo": "", "backdrop": ""},
                "environment": {"solo": "wood beams", "backdrop": "wood beams"},
                "description": {"solo": "tavern", "backdrop": "tavern"},
            },
        }),
    )
    report = migrate_world(genre_root, "testworld", in_place=True)
    tav = yaml.safe_load((genre_root / "places.yaml").read_text())["tavern"]
    assert "roadhouse" in tav["environment"]["solo"]
    assert report["matched"] == ["tavern"]


def test_override_with_no_match_goes_to_report(tmp_path) -> None:
    genre_root = tmp_path / "genre_packs" / "testgenre"
    (genre_root / "worlds" / "testworld").mkdir(parents=True)
    (genre_root / "worlds" / "testworld" / "visual_style.yaml").write_text(
        yaml.safe_dump({"visual_tag_overrides": {"xenotemple": "glowing geometry"}}),
    )
    (genre_root / "places.yaml").write_text(yaml.safe_dump({}))
    report = migrate_world(genre_root, "testworld", in_place=True)
    assert "xenotemple" in report["unmatched"]
