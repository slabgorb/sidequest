from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from generate_music import discover_jobs, is_in_r2
from unittest.mock import patch, MagicMock


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


def test_is_in_r2_returns_true_on_http_200():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SIDEQUEST_ASSET_BASE_URL", None)
        with patch("generate_music.requests.head") as mock_head:
            mock_head.return_value = MagicMock(status_code=200)
            assert is_in_r2("genre_packs/cav/audio/music/combat.ogg") is True
            mock_head.assert_called_once_with(
                "https://cdn.slabgorb.com/genre_packs/cav/audio/music/combat.ogg",
                timeout=5,
            )


def test_is_in_r2_returns_false_on_http_404():
    with patch("generate_music.requests.head") as mock_head:
        mock_head.return_value = MagicMock(status_code=404)
        assert is_in_r2("genre_packs/cav/audio/music/combat.ogg") is False


def test_is_in_r2_honors_asset_base_url_env(monkeypatch):
    monkeypatch.setenv("SIDEQUEST_ASSET_BASE_URL", "http://localhost:8765")
    with patch("generate_music.requests.head") as mock_head:
        mock_head.return_value = MagicMock(status_code=404)
        is_in_r2("genre_packs/cav/audio/music/combat.ogg")
        url = mock_head.call_args[0][0]
        assert url.startswith("http://localhost:8765/")


def test_filter_jobs_by_track_returns_only_matching_stem():
    from generate_music import filter_jobs_by_track
    jobs = [
        (Path("/x/genre_packs/cav/audio/music/combat_input_params.json"),
         "genre_packs/cav/audio/music/combat.ogg"),
        (Path("/x/genre_packs/cav/audio/music/tension_input_params.json"),
         "genre_packs/cav/audio/music/tension.ogg"),
    ]
    filtered = filter_jobs_by_track(jobs, "combat")
    assert len(filtered) == 1
    assert filtered[0][1] == "genre_packs/cav/audio/music/combat.ogg"


def test_filter_jobs_by_track_returns_empty_when_no_match():
    from generate_music import filter_jobs_by_track
    jobs = [
        (Path("/x/genre_packs/cav/audio/music/combat_input_params.json"),
         "genre_packs/cav/audio/music/combat.ogg"),
    ]
    assert filter_jobs_by_track(jobs, "nonexistent") == []
