from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from generate_music import discover_jobs


def test_discover_jobs_walks_pack_audio_music_dir(tmp_path):
    pack_dir = tmp_path / "genre_packs" / "cav"
    music_dir = pack_dir / "audio" / "music"
    music_dir.mkdir(parents=True)
    (music_dir / "combat_input_params.json").write_text("{}")
    (music_dir / "tension_input_params.json").write_text("{}")
    (music_dir / "ignore_me.json").write_text("{}")  # missing _input_params suffix

    jobs = discover_jobs(pack_dir)

    by_key = {key: path for path, key in jobs}
    assert "genre_packs/cav/audio/music/combat.ogg" in by_key
    assert "genre_packs/cav/audio/music/tension.ogg" in by_key
    assert len(jobs) == 2
