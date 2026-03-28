#!/usr/bin/env python3
"""Batch-generate mood tracks for genre packs using ACE-Step daemon.

Reads mood definitions from genre-specific configs below, sends render
requests to the running sidequest-renderer daemon, converts WAV→OGG.

Usage:
    python scripts/generate_music.py --genre pulp_noir           # all moods
    python scripts/generate_music.py --genre pulp_noir --mood combat
    python scripts/generate_music.py --genre pulp_noir --mood combat --variation sparse
    python scripts/generate_music.py --genre pulp_noir --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

SOCKET_PATH = Path("/tmp/sidequest-renderer.sock")
_root = Path(__file__).resolve().parent.parent
GENRE_PACKS_DIR = _root / "sidequest-content" / "genre_packs"

log = logging.getLogger(__name__)

# ── Variation types (shared across all genres) ──────────────────────

VARIATION_SUFFIXES = {
    "full": "full arrangement, complete orchestration, all instruments, rich, layered, dynamic",
    "ambient": "ambient, reverb, pads, stripped, minimal, atmospheric, slow",
    "sparse": "sparse, minimalist, solo instrument, space, silence, delicate, bare",
    "tension_build": "building tension, rising, crescendo, layered, intensifying",
    "resolution": "resolution, release, calm after storm, settling, peaceful conclusion, exhale",
    "overture": "overture, grand opening, introduction, establishing, sweeping, cinematic",
}

# ── Genre mood definitions ──────────────────────────────────────────
# Each genre maps mood_name → (prompt, duration_seconds)

GENRE_MOODS: dict[str, dict[str, tuple[str, int]]] = {
    "pulp_noir": {
        "exploration": ("cool jazz, upright bass, brushed drums, muted trumpet, walking bass line, smoky, nocturnal, 1920s Paris, noir", 60),
        "combat": ("hard bop, frantic drums, brass stabs, piano crashes, urgent, chaotic, bar fight, 1920s jazz, aggressive", 60),
        "tension": ("sparse piano, single bass note, silence between beats, film noir, suspense, dark, slow, menacing, minimal", 60),
        "rest": ("slow jazz ballad, solo saxophone, quiet piano, intimate, melancholic, late night, 1920s, torch song", 60),
        "speakeasy": ("hot jazz, full band, swing feel, crowd energy, trumpet solo, clarinet, 1920s, prohibition, dance, upbeat", 60),
        "intrigue": ("film noir score, solo clarinet, minor key, shadows, mysterious, detective, following leads, suspenseful, subtle", 60),
        "chase": ("driving rhythm, walking bass, urgent brass, fast tempo, pursuit, car chase, 1920s, frantic, bebop", 60),
    },
    "neon_dystopia": {
        "exploration": ("synthwave, neon, dark ambient, rain, city streets, blade runner, pulsing synth bass, atmospheric, nocturnal, cyberpunk", 60),
        "combat": ("industrial, aggressive synth, distorted bass, fast tempo, combat, cyberpunk, metallic percussion, intense, electronic, dark", 60),
        "tension": ("dark ambient, low drone, digital interference, suspense, hacking, cyber threat, minimal, ominous pulse, eerie, glitch", 60),
        "rest": ("lo-fi synth, ambient pads, gentle, peaceful, rooftop dawn, warm synth, reflective, cyberpunk calm, slow, atmospheric", 60),
        "cyberspace": ("digital, glitch, fast arpeggios, trance, virtual reality, data streams, electronic, pulsing, crystalline, matrix", 60),
        "club": ("darkwave, dance, heavy bass, synth, nightclub, neon, industrial dance, electronic, 128 bpm, driving, cyberpunk club", 60),
        "chase": ("high tempo synthwave, pursuit, driving bass, urgent, highway, vehicles, cyberpunk chase, fast, relentless, adrenaline", 60),
        "corporate": ("cold ambient, glass and steel, corporate, elevator dystopia, clean synth, minimal, sterile, oppressive calm, boardroom", 60),
    },
    "low_fantasy": {
        "exploration": ("medieval lute, acoustic guitar, gentle flute, tavern ambience, folk, pastoral, warm, earthy, wandering, journey", 60),
        "combat": ("war drums, brass fanfare, urgent strings, medieval battle, epic, aggressive percussion, chaotic, martial, iron and steel", 60),
        "tension": ("solo cello, minor key, sparse, creeping, dark forest, shadow, suspense, medieval, ominous drone, quiet menace", 60),
        "rest": ("gentle harp, soft flute, peaceful, fireside, warmth, healing, lullaby, medieval, pastoral calm, night rest", 60),
        "tavern": ("lively fiddle, bodhran, pub folk, raucous, ale and laughter, Celtic, dancing, jig, tavern crowd, merry", 60),
        "mystery": ("solo recorder, ethereal choir, sacred, ancient ruins, discovery, wonder, medieval church, echoing, reverent, mystical", 60),
        "chase": ("fast fiddle, galloping rhythm, pursuit, hooves, urgent, woodland chase, breathless, Celtic reel, frantic, escape", 60),
    },
    "elemental_harmony": {
        "exploration": ("shamisen, bamboo flute, koto, gentle, misty mountains, zen garden, peaceful, Japanese traditional, atmospheric, meditative", 60),
        "combat": ("taiko drums, fierce, martial, shamisen, fast tempo, samurai battle, steel and fire, aggressive, Japanese, epic", 60),
        "tension": ("solo shakuhachi, sparse, dark, temple at night, suspense, ominous, minimal, koto drone, ancient threat, quiet dread", 60),
        "rest": ("gentle koto, wind chimes, peaceful, hot springs, steam, evening, reflective, Japanese ambient, serene, warm", 60),
        "ceremony": ("gagaku, imperial court, formal, ancient ritual, slow, ceremonial, flute and strings, Japanese classical, sacred, solemn", 60),
        "spirit": ("ethereal, otherworldly, bell tones, shrine, supernatural, fox spirit, dreamlike, Japanese folklore, haunting, beautiful", 60),
        "chase": ("fast taiko, urgent shamisen, pursuit, rooftops, wind, running, Japanese action, breathless, dramatic, relentless", 60),
    },
    "space_opera": {
        "exploration": ("cinematic orchestral, space ambience, vast, strings, synthesizer, wonder, discovery, cosmic, sweeping, interstellar", 60),
        "combat": ("epic orchestral, brass, war drums, space battle, lasers, urgent, aggressive, cinematic, action, intense", 60),
        "tension": ("dark synth, low strings, suspense, deep space, isolation, dread, minimal, pulsing, alien, ominous", 60),
        "rest": ("gentle piano, soft strings, starlight, peaceful, space station, ambient, reflective, cosmic calm, warm, hopeful", 60),
        "cantina": ("alien jazz, unusual instruments, exotic, lively, space bar, eclectic, playful, interstellar lounge, quirky, upbeat", 60),
        "void": ("deep drone, cosmic ambience, vast emptiness, dark, cold, infinite, minimal, space, desolate, haunting", 60),
        "chase": ("fast orchestral, pursuit, engines, urgent brass, space chase, adrenaline, cinematic action, relentless, driving, epic", 60),
    },
    "mutant_wasteland": {
        "exploration": ("post-apocalyptic ambient, desolate, wind, sparse guitar, dusty, wasteland, lonely, atmospheric, decay, survival", 60),
        "combat": ("industrial metal, distorted, aggressive, chaotic, mutant battle, harsh, percussion, savage, wasteland combat, brutal", 60),
        "tension": ("geiger counter clicks, low drone, radiation hum, dread, contamination, sparse, ominous, wasteland horror, toxic, creeping", 60),
        "rest": ("campfire acoustic guitar, gentle, warm, night sky, stars, desert calm, folk, hopeful, survival rest, peaceful", 60),
        "scavenge": ("clanking metal, industrial ambient, rummaging, discovery, salvage, mechanical, rhythmic, wasteland workshop, building, creating", 60),
        "chase": ("fast industrial, pursuit, engines, wasteland vehicles, aggressive drums, road chase, dust, brutal, relentless, mad max", 60),
    },
    "road_warrior": {
        "exploration": ("desert rock, slide guitar, dusty road, heat haze, V8 engines idle, desolate highway, atmospheric, gritty, sun-bleached", 60),
        "combat": ("thrash metal, aggressive drums, vehicle combat, road rage, explosive, chaotic, high octane, brutal, relentless, metal", 60),
        "tension": ("sparse desert ambient, distant thunder, engine tick, fuel low, dread, minimal, hot wind, ominous, wasteland silence", 60),
        "rest": ("acoustic blues, campfire, desert night, stars, harmonica, reflective, weary, road song, folk, peaceful", 60),
        "chase": ("high tempo rock, V8 roar, pursuit, highway, adrenaline, guitar shred, drums pounding, road warrior chase, relentless", 60),
        "convoy": ("driving rock, steady rhythm, engines in formation, road, powerful, united, heavy bass, convoy, rolling thunder, epic", 60),
        # --- The Circuit: faction themes ---
        "faction_bosozoku": ("Japanese punk rock, distorted guitar, aggressive drums, engine revving percussion, synchronized exhaust rhythm, Guitar Wolf energy, fast tempo, rebellious, raw, 1970s Japanese garage punk", 60),
        "faction_mods": ("Northern Soul, urgent rhythm and blues, Motown energy, mod revival, The Jam, driving bass, Hammond organ, amphetamine energy, danceable, 1979 London, all-night club", 60),
        "faction_one_percenters": ("heavy blues rock, Southern rock, Steppenwolf, ZZ Top, rolling Harley-Davidson rumble, menacing slide guitar, open highway, leather and chrome, 1970s biker rock", 60),
        "faction_cafe_racers": ("instrumental surf rock, Dick Dale, Link Wray, reverb guitar, pure velocity, no vocals, driving tempo, clean tone, Fender twang, speed and precision, 1960s", 60),
        "faction_rockers": ("1950s rock and roll, rockabilly, Gene Vincent, Eddie Cochran, slap bass, raw guitar, leather jacket energy, greasy, pub rock, brawling, sneer", 60),
        "faction_lowriders": ("Chicano soul, oldies, War Low Rider, slow cruise bass, Thee Midniters, warm, low and slow, hydraulic bounce, candy paint, East LA, heartbreak and pride, 1970s", 60),
        "faction_matatu": ("Afrobeat, Kenyan benga guitar, Fela Kuti energy, massive bass, percussive, polyrhythmic, joyful chaos, subwoofer pressure, Nairobi, painted bus, dancehall energy", 60),
        "faction_tuk_tuk": ("Thai funk, Molam psychedelic, Khruangbin, hypnotic bass groove, Southeast Asian psych rock, three-wheeled groove, mysterious, wah guitar, nocturnal, alley music", 60),
        "faction_raggare": ("1950s doo-wop, Buddy Holly, The Penguins, American rock and roll, jukebox at midnight, V8 idle rumble, cruising, Swedish summer night, warm nostalgia, pompadour rock", 60),
        "faction_dekotora": ("Japanese enka ballad, dramatic vocal melody, sentimental, trucker highway opera, melancholy, convoy grandeur, Torakku Yaro film soundtrack, 1970s Japanese pop, orchestral, emotional", 60),
    },
}


def compute_seed(genre: str, mood: str, variation: str) -> int:
    key = f"{genre}+{mood}+{variation}"
    digest = hashlib.sha256(key.encode()).hexdigest()
    return int(digest[:8], 16)


def wav_to_ogg(wav_path: Path, ogg_path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-c:a", "libvorbis", "-q:a", "4", str(ogg_path)],
        capture_output=True,
    )
    if ogg_path.exists():
        wav_path.unlink()
        log.info("  Converted: %s (%dKB)", ogg_path.name, ogg_path.stat().st_size // 1024)


async def send_render(prompt: str, duration: int, seed: int) -> dict:
    """Send a music render request to the daemon."""
    reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))

    req = {
        "id": f"music-{seed}",
        "method": "render",
        "params": {
            "tier": "music",
            "prompt": prompt,
            "duration": duration,
            "seed": seed,
        },
    }

    writer.write((json.dumps(req) + "\n").encode())
    await writer.drain()

    response_line = await asyncio.wait_for(reader.readline(), timeout=900)
    writer.close()
    await writer.wait_closed()

    return json.loads(response_line.decode())


async def check_daemon() -> bool:
    try:
        reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))
        req = {"id": "healthcheck", "method": "ping"}
        writer.write((json.dumps(req) + "\n").encode())
        await writer.drain()
        resp = await asyncio.wait_for(reader.readline(), timeout=5)
        writer.close()
        await writer.wait_closed()
        data = json.loads(resp.decode())
        return data.get("result", {}).get("status") == "ok"
    except Exception:
        return False


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate mood music tracks for genre packs")
    parser.add_argument("--genre", required=True, help="Genre pack name")
    parser.add_argument("--mood", help="Only generate this mood")
    parser.add_argument("--variation", help="Only generate this variation type")
    parser.add_argument("--dry-run", action="store_true", help="Preview prompts without generating")
    parser.add_argument("--duration", type=int, help="Override track duration in seconds")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    if args.genre not in GENRE_MOODS:
        available = ", ".join(sorted(GENRE_MOODS.keys()))
        log.error("Unknown genre '%s'. Available: %s", args.genre, available)
        sys.exit(1)

    moods = GENRE_MOODS[args.genre]
    output_dir = GENRE_PACKS_DIR / args.genre / "audio" / "music"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter moods if specified
    if args.mood:
        if args.mood not in moods:
            available = ", ".join(sorted(moods.keys()))
            log.error("Unknown mood '%s' for %s. Available: %s", args.mood, args.genre, available)
            sys.exit(1)
        moods = {args.mood: moods[args.mood]}

    # Filter variations if specified
    variations = dict(VARIATION_SUFFIXES)
    if args.variation:
        if args.variation not in variations:
            available = ", ".join(sorted(variations.keys()))
            log.error("Unknown variation '%s'. Available: %s", args.variation, available)
            sys.exit(1)
        variations = {args.variation: variations[args.variation]}

    if not args.dry_run:
        if not await check_daemon():
            log.error("Daemon not running at %s — start with: sidequest-renderer", SOCKET_PATH)
            sys.exit(1)
        log.info("Daemon alive at %s", SOCKET_PATH)

    total = len(moods) * len(variations)
    success = 0
    failed = 0
    skipped = 0
    start_time = time.monotonic()
    i = 0

    for mood_name, (base_prompt, default_duration) in moods.items():
        duration = args.duration or default_duration

        log.info("\n%s", "=" * 60)
        log.info("MOOD: %s (%s)", mood_name, args.genre)
        log.info("=" * 60)

        for var_type, var_suffix in variations.items():
            i += 1
            full_prompt = f"{base_prompt}, {var_suffix}"
            seed = compute_seed(args.genre, mood_name, var_type)
            ogg_path = output_dir / f"{mood_name}_{var_type}.ogg"
            wav_path = output_dir / f"{mood_name}_{var_type}.wav"

            if ogg_path.exists() and not args.dry_run:
                log.info("  [%d/%d] SKIP %s (exists)", i, total, ogg_path.name)
                skipped += 1
                continue

            log.info("  [%d/%d] %s_%s", i, total, mood_name, var_type)

            if args.dry_run:
                print(f"\n  Mood: {mood_name}  Variation: {var_type}")
                print(f"  Duration: {duration}s  Seed: {seed}")
                print(f"  Prompt: {full_prompt[:120]}...")
                print(f"  Output: {ogg_path}")
                continue

            try:
                result = await send_render(full_prompt, duration, seed)
                if "error" in result:
                    log.error("  FAILED: %s", result["error"])
                    failed += 1
                    continue

                rendered_path = Path(result["result"]["image_path"])
                # Rename daemon output to our wav path
                rendered_path.rename(wav_path)

                # Convert WAV → OGG
                wav_to_ogg(wav_path, ogg_path)
                elapsed = result["result"].get("elapsed_ms", 0)
                log.info("  OK (%.1fs) → %s", elapsed / 1000, ogg_path.name)
                success += 1

            except Exception as e:
                log.error("  FAILED: %s", e)
                failed += 1

    total_time = time.monotonic() - start_time

    print(f"\n{'=' * 60}")
    print(f"Done! {success} generated, {skipped} skipped, {failed} failed")
    print(f"Total time: {total_time / 60:.1f} minutes")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
