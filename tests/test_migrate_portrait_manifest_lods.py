import yaml

from scripts.migrate_portrait_manifest_lods import migrate_manifest


def test_legacy_single_description_migrates_to_solo(tmp_path) -> None:
    src = tmp_path / "portrait_manifest.yaml"
    src.write_text(yaml.safe_dump({
        "characters": [
            {
                "name": "Rux",
                "role": "inquisitor",
                "type": "npc_major",
                "appearance": "a tall gaunt inquisitor in grey wool",
            },
        ],
    }))
    migrate_manifest(src, in_place=True)
    data = yaml.safe_load(src.read_text())
    char = data["characters"][0]
    assert char["descriptions"]["solo"] == "a tall gaunt inquisitor in grey wool"
    for lod in ("long", "short", "background"):
        assert char["descriptions"][lod].startswith("TODO:")
    assert "_needs_lod_authoring" in char


def test_already_migrated_file_is_noop(tmp_path) -> None:
    src = tmp_path / "portrait_manifest.yaml"
    src.write_text(yaml.safe_dump({
        "characters": [
            {
                "id": "rux",
                "descriptions": {
                    "solo": "...", "long": "...",
                    "short": "...", "background": "...",
                },
                "default_pose": "standing",
            },
        ],
    }))
    before = src.read_text()
    migrate_manifest(src, in_place=True)
    after = src.read_text()
    assert before == after
