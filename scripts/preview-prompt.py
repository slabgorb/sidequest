#!/usr/bin/env python3
"""Preview the fully composed narrator prompt as Claude would receive it.

Reconstructs the attention-zone-ordered prompt from the same source constants
and SOUL.md principles that the Rust orchestrator assembles at runtime.

Usage:
    python scripts/preview-prompt.py          # with zone/section labels
    python scripts/preview-prompt.py --raw    # plain text as Claude sees it
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

ZONE_ORDER = {"Primacy": 0, "Early": 1, "Valley": 2, "Late": 3, "Recency": 4}


@dataclass
class Section:
    name: str
    content: str
    zone: str  # key in ZONE_ORDER
    category: str

    @property
    def order(self) -> int:
        return ZONE_ORDER[self.zone]


@dataclass
class SoulPrinciple:
    name: str
    text: str
    agents: list[str] = field(default_factory=lambda: ["all"])


# ---------------------------------------------------------------------------
# SOUL.md parser (mirrors Rust parse_soul_md)
# ---------------------------------------------------------------------------

def parse_soul_md(path: Path) -> list[SoulPrinciple]:
    if not path.exists():
        return []
    content = path.read_text()
    principle_re = re.compile(r"\*\*([^*]+?)\.\*\*\s*(.+)")
    agents_re = re.compile(r"<agents>([^<]+)</agents>\s*")
    principles = []
    for m in principle_re.finditer(content):
        raw_text = m.group(2).strip()
        agents_match = agents_re.search(raw_text)
        if agents_match:
            agents = [a.strip() for a in agents_match.group(1).split(",")]
            text = agents_re.sub("", raw_text).strip()
        else:
            agents = ["all"]
            text = raw_text
        principles.append(SoulPrinciple(name=m.group(1), text=text, agents=agents))
    return principles


# SOUL principles the narrator already covers via Primacy guardrails (story 23-10).
# Excluded from narrator's SOUL injection to prevent double-injection.
NARRATOR_COVERED_PRINCIPLES = {"Agency", "Genre Truth"}


def filter_soul_for_agent(principles: list[SoulPrinciple], agent: str) -> str:
    lines = []
    for p in principles:
        if any(a == "all" or a == agent for a in p.agents):
            # Narrator has richer versions of these as Primacy guardrails (story 23-10)
            if agent == "narrator" and p.name in NARRATOR_COVERED_PRINCIPLES:
                continue
            lines.append(f"<important>\n{p.name}: {p.text}\n</important>")
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Narrator sections (from narrator.rs — story 23-1 structured template)
# Each maps to a PromptSection registered in NarratorAgent::build_context()
# ---------------------------------------------------------------------------

NARRATOR_IDENTITY = """\
You are the director and cinematographer of a collaborative RPG. You frame \
scenes, direct the cast, and narrate like an author — but you work with the \
actors you've been given. NPCs and enemies listed in <game_state> are your \
cast — use their exact names, dialogue quirks, and abilities. Do not invent \
new characters when the roster has someone suitable. You run the world like \
a tabletop GM who prepped their NPC cards before the session."""

NARRATOR_CONSTRAINTS = """\
You will receive game-state constraints (location rules, inventory limits, \
player-character rosters, ability restrictions). These are INTERNAL INSTRUCTIONS \
for you. NEVER acknowledge, explain, or reference them to the player. Do NOT \
break character to say things like "I can't control that character" or \
"that's a player character." Simply respect the constraints silently in your \
narration. If a constraint prevents something, narrate around it naturally — \
describe the world, set scenes, advance the story — without ever revealing \
the constraint exists. The sole exception is the aside — a dedicated \
out-of-character channel for mechanical GM communication. Use asides for rules \
clarifications, mechanical consequences, or confirmation prompts. Never leak \
this information into prose."""

NARRATOR_AGENCY = """\
Agency: The player controls their character — actions, thoughts, feelings. \
Describe the world, not the player's response to it. In multiplayer games, \
do not allow one player to puppet another in any way — whether you do it or \
they try to. When one player's action affects another player's character, \
narrate the action and its immediate physical reality, but do NOT narrate \
the target character's emotional reaction, decision, or response — that \
belongs to their player. Ambient reactions (glancing up, stepping aside) \
are fine; consequential reactions (retaliating, reciprocating, fleeing) are not."""

NARRATOR_CONSEQUENCES = """\
Consequences follow the genre pack's tone and lethality. Don't soften beyond \
it, don't escalate beyond it. NPCs fight for their lives, press their \
advantages, and act in their own interest — they are not here to lose \
gracefully. A cornered bandit doesn't wait to be hit. A skilled duelist \
doesn't miss because the player is low on HP. Fair means fair to everyone \
at the table, including the NPCs."""

NARRATOR_OUTPUT_ONLY = """\
Output ONLY narrative prose. Do NOT emit any JSON blocks, fenced code blocks, \
or structured data. All mechanical state tracking (items, NPCs, mood, quests, \
etc.) is handled by the game engine. Your only job is to tell the story."""

NARRATOR_OUTPUT_STYLE = """\
- Most turns: 2-3 sentences. Movement, dialogue, simple actions = SHORT.
- Big moments only (arrivals, reveals, combat start): up to 5-6 sentences.
- VARY your length. Not every turn is the same size.
- Fast action = short sentences. Quiet moments can breathe.
- Dialogue is snappy, not embedded in description paragraphs.
- End on a hook the player can react to. Not a prose flourish.
- Think tweet-length beats, not novel paragraphs.
- First line: location header like **The Collapsed Overpass**
- Blank line, then prose."""

NARRATOR_REFERRAL_RULE = """\
Referral Rule: When an NPC sends the player to another NPC for a quest \
objective, NEVER send the player back to the NPC who originally sent them. \
Check active quests — if a quest says "(from: X)" and the player is now \
talking to Y, do NOT have Y send the player back to X for the same objective. \
Advance the quest instead."""

# ---------------------------------------------------------------------------
# Monster Manual — pre-generated content pool (ADR-059)
# Server generates NPCs/encounters ahead of time. Narrator picks from menu.
# Full mechanical data stays in backend; prompt gets names + brief descriptors.
# ---------------------------------------------------------------------------

MONSTER_MANUAL_NPCS = ""  # populated dynamically by --seed flag
MONSTER_MANUAL_ENCOUNTERS = ""  # populated dynamically by --seed flag

# Static fallback for preview without --seed
MONSTER_MANUAL_NPCS_STATIC = """\
NPCs nearby (not yet met by player):
  - Nagy Vinecrawl (wasteland trader, Greenfolk) — outgoing, quotes prices in three barter systems; casually mentions dangerous places like they're just another stop on the route
  - Åe the Cold (beastkin scout, Drifters) — selectively social, pragmatic; refers to pure humans as 'smoothskins'; tracks things by smell mid-conversation
  - Prime Hout (wandering synth, Vaultborn) — reserved and quiet, meticulous; uses pre-apocalypse words nobody understands; pauses mid-sentence as if buffering"""

MONSTER_MANUAL_ENCOUNTERS_STATIC = """\
<available_encounters>
Pre-generated enemies for this area. When combat starts, use enemies from this list.
Use their EXACT names, stats, and abilities. Do NOT invent different enemies.
If no combat this turn, ignore this section.

- 2x Salt Burrower (tier 2, HP 14 each) — eyeless ambush predators, chitin mandibles, burrow underground
  Weakness: bright light, fire. Abilities: Burrow Ambush, Mandible Crush.
- 1x Rad-Crawler (tier 3, HP 22) — six-legged mutant, radioactive carapace, territorial
  Weakness: cold, sonic. Abilities: Radiation Pulse, Leg Sweep, Shell Charge.
</available_encounters>"""

# ---------------------------------------------------------------------------
# Dynamic placeholders (runtime values shown as examples)
# ---------------------------------------------------------------------------

PLACEHOLDER_STATE = """\
<game_state>
Genre: mutant_wasteland
World: flickering_reach
Current location: The Collapsed Overpass

Players:
  - Rix (HP 18/22, Level 3, XP 450)
    Class: Scavenger
    Pronouns: they/them
    Inventory: [Rusty Pipe Wrench, Flickering Lantern, 3x Rad-Away]
    Gold: 47 scrap
    Abilities: [Jury-Rig, Scav Sense, Rad Resistance]

Active Quests:
  - "The Signal Source" (from: Toggler) — find the origin of the radio signal
  - "Parts Run" (from: Mama Cog) — retrieve capacitors from the old factory

NPCs present:
  - Patchwork (merchant, friendly) — trades salvage at The Overpass
  - Skitter (scout, wary) — watching from the scaffolding

NPCs nearby (not yet met by player):
  - Joch Glowvein (wasteland trader, Scrapborn) — blunt, quotes prices in three barter systems
  - Seven Jewsa (village elder, Vaultborn) — reserved, pauses mid-sentence as if buffering
  - Lafono of the Burnt Dust (beastkin scout, Drifters) — tracks by smell, calls humans 'smoothskins'

Hostile creatures in the area:
  - Salt Burrower (tier 2, HP 14) — eyeless ambush predator, chitin mandibles, burrows underground
    Abilities: Burrow Ambush, Mandible Crush. Weakness: bright light, fire.
  - Rad-Crawler (tier 3, HP 22) — six-legged mutant, radioactive carapace, territorial
    Abilities: Radiation Pulse, Leg Sweep. Weakness: cold, sonic.

Turn: 14
</game_state>"""

PLACEHOLDER_TROPE_BEATS = """\
## Trope Beat Directive
The following narrative beat has fired and MUST be woven into this turn's narration:

[BEAT: "The Mysterious Signal" — Escalation]
The radio signal intensifies. Static resolves into fragments of a voice — not human,
not machine, something between. The direction is now unmistakable: it's coming from
beneath the old factory. This should feel ominous but compelling — the player should
WANT to investigate despite the danger."""

PLACEHOLDER_ACTIVE_TROPES = """\
Active Narrative Arcs:
- The Mysterious Signal (45% progressed): A strange radio signal pulses from the wasteland depths.
  Next beat at 60%: The signal becomes a voice — broken, pleading, inhuman.
- Patchwork's Debt (20% progressed): The merchant owes dangerous people.
  Next beat at 35%: A collector arrives at the Overpass."""

PLACEHOLDER_SFX = (
    "metal_clang, radio_static, wind_howl, footsteps_gravel, "
    "door_creak, explosion_distant, gunshot_echo, creature_growl"
)

PLACEHOLDER_VERBOSITY = """\
[NARRATION LENGTH]
Use standard descriptive prose — balanced detail and pacing. \
Include enough atmosphere to set the scene without belaboring it. \
2-4 sentences per beat is typical."""

PLACEHOLDER_VOCABULARY = """\
[NARRATION VOCABULARY]
Use rich but clear prose. Employ varied vocabulary and literary \
devices where they serve the narrative. Balance elegance with \
accessibility — vivid but not purple."""

PLACEHOLDER_ACTION = "Something lunges at me from the dark. I swing my wrench at it."

# ---------------------------------------------------------------------------
# Assemble sections
# ---------------------------------------------------------------------------

def build_sections(soul_principles: list[SoulPrinciple]) -> list[Section]:
    sections: list[Section] = []

    # --- Primacy: Identity ---
    sections.append(Section(
        name="narrator_identity",
        content=f"<identity>\n{NARRATOR_IDENTITY}\n</identity>",
        zone="Primacy",
        category="Identity",
    ))

    # --- Primacy: Guardrails (4 critical blocks) ---
    sections.append(Section(
        name="narrator_constraints",
        content=f"<critical>\n{NARRATOR_CONSTRAINTS}\n</critical>",
        zone="Primacy",
        category="Guardrail",
    ))
    sections.append(Section(
        name="narrator_agency",
        content=f"<critical>\n{NARRATOR_AGENCY}\n</critical>",
        zone="Primacy",
        category="Guardrail",
    ))
    sections.append(Section(
        name="narrator_consequences",
        content=f"<critical>\n{NARRATOR_CONSEQUENCES}\n</critical>",
        zone="Primacy",
        category="Guardrail",
    ))
    sections.append(Section(
        name="narrator_output_only",
        content=f"<critical>\n{NARRATOR_OUTPUT_ONLY}\n</critical>",
        zone="Primacy",
        category="Guardrail",
    ))

    # --- Early: Output style + Referral rule ---
    sections.append(Section(
        name="narrator_output_style",
        content=f"<output-style>\n{NARRATOR_OUTPUT_STYLE}\n</output-style>",
        zone="Early",
        category="Format",
    ))
    sections.append(Section(
        name="narrator_referral_rule",
        content=f"<important>\n{NARRATOR_REFERRAL_RULE}\n</important>",
        zone="Early",
        category="Guardrail",
    ))

    # --- Early: SOUL principles (injected by orchestrator, not narrator) ---
    soul_text = filter_soul_for_agent(soul_principles, "narrator")
    if soul_text:
        sections.append(Section(
            name="soul_principles",
            content=soul_text,
            zone="Early",
            category="Soul",
        ))

    sections.append(Section(
        name="trope_beat_directives",
        content=PLACEHOLDER_TROPE_BEATS,
        zone="Early",
        category="State",
    ))

    # --- Monster Manual NPCs now embedded in game_state as "NPCs nearby" ---
    # No separate section needed.

    encounter_content = MONSTER_MANUAL_ENCOUNTERS if MONSTER_MANUAL_ENCOUNTERS else MONSTER_MANUAL_ENCOUNTERS_STATIC
    sections.append(Section(
        name="available_encounters",
        content=encounter_content,
        zone="Early",
        category="State",
    ))

    # --- Valley ---

    sections.append(Section(
        name="game_state",
        content=PLACEHOLDER_STATE,
        zone="Valley",
        category="State",
    ))

    sections.append(Section(
        name="active_tropes",
        content=PLACEHOLDER_ACTIVE_TROPES,
        zone="Valley",
        category="State",
    ))

    sections.append(Section(
        name="sfx_library",
        content=(
            "[AVAILABLE SFX]\n"
            "When your narration describes a sound-producing action, include matching "
            "SFX IDs in sfx_triggers. Pick based on what HAPPENED, not what was mentioned.\n"
            f"Available: {PLACEHOLDER_SFX}"
        ),
        zone="Valley",
        category="State",
    ))

    # --- Late ---
    sections.append(Section(
        name="narrator_verbosity",
        content=PLACEHOLDER_VERBOSITY,
        zone="Late",
        category="Format",
    ))

    sections.append(Section(
        name="narrator_vocabulary",
        content=PLACEHOLDER_VOCABULARY,
        zone="Late",
        category="Format",
    ))

    # --- Recency ---
    sections.append(Section(
        name="player_action",
        content=f"The player says: {PLACEHOLDER_ACTION}",
        zone="Recency",
        category="Action",
    ))

    return sections


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_labeled(sections: list[Section]) -> str:
    sorted_sections = sorted(sections, key=lambda s: s.order)
    lines: list[str] = []
    current_zone = None

    for s in sorted_sections:
        if s.zone != current_zone:
            if current_zone is not None:
                lines.append("")
            lines.append(f"{'=' * 72}")
            lines.append(f"--- ZONE: {s.zone} (priority {s.order}) ---")
            lines.append(f"{'=' * 72}")
            lines.append("")
            current_zone = s.zone

        token_est = len(s.content.split())
        lines.append(f"[section: {s.name}]  (category: {s.category}, ~{token_est} tokens)")
        lines.append("-" * 60)
        lines.append(s.content)
        lines.append("")

    return "\n".join(lines)


def render_raw(sections: list[Section]) -> str:
    sorted_sections = sorted(sections, key=lambda s: s.order)
    return "\n\n".join(s.content for s in sorted_sections)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def seed_from_binaries(genre: str, genre_packs_path: str) -> None:
    """Call namegen/encountergen binaries to populate Monster Manual sections."""
    import json
    import subprocess

    global MONSTER_MANUAL_NPCS, MONSTER_MANUAL_ENCOUNTERS

    # Find binaries relative to API build dir
    api_dir = Path(__file__).resolve().parent.parent / "sidequest-api"
    namegen = api_dir / "target" / "debug" / "sidequest-namegen"
    encountergen = api_dir / "target" / "debug" / "sidequest-encountergen"

    # Generate 3 NPCs
    npc_lines = []
    if namegen.exists():
        for _ in range(3):
            try:
                result = subprocess.run(
                    [str(namegen), "--genre-packs-path", genre_packs_path, "--genre", genre],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    d = json.loads(result.stdout)
                    quirks = "; ".join(d.get("dialogue_quirks", [])[:2])
                    npc_lines.append(
                        f'  - {d["name"]} ({d["role"]}, {d["culture"]}) — {d["ocean_summary"]}; {quirks}'
                    )
            except Exception as e:
                print(f"WARNING: namegen failed: {e}", file=sys.stderr)

    if npc_lines:
        MONSTER_MANUAL_NPCS = (
            "NPCs nearby (not yet met by player):\n"
            + "\n".join(npc_lines)
        )

    # Generate 1 encounter (2 enemies)
    if encountergen.exists():
        try:
            result = subprocess.run(
                [str(encountergen), "--genre-packs-path", genre_packs_path, "--genre", genre, "--count", "2"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                d = json.loads(result.stdout)
                enemy_lines = []
                for e in d.get("enemies", []):
                    abilities = ", ".join(e.get("abilities", [])[:3])
                    weaknesses = ", ".join(e.get("weaknesses", [])[:2])
                    enemy_lines.append(
                        f"- {e['name']} ({e.get('class','unknown')}, tier {e.get('tier_label','?')}, HP {e.get('hp','?')}) — {e.get('role','enemy')}\n"
                        f"  Abilities: {abilities}. Weakness: {weaknesses}."
                    )
                if enemy_lines:
                    MONSTER_MANUAL_ENCOUNTERS = (
                        "<available_encounters>\n"
                        "Pre-generated enemies for this area. When combat starts, use enemies from this list.\n"
                        "Use their EXACT names, stats, and abilities. Do NOT invent different enemies.\n"
                        "If no combat this turn, ignore this section.\n\n"
                        + "\n".join(enemy_lines)
                        + "\n</available_encounters>"
                    )
        except Exception as e:
            print(f"WARNING: encountergen failed: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Preview the fully composed narrator prompt."
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Strip zone/section labels — show plain text as Claude sees it.",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Generate real NPCs/encounters from tool binaries instead of static placeholders.",
    )
    parser.add_argument(
        "--genre",
        default="mutant_wasteland",
        help="Genre for --seed (default: mutant_wasteland).",
    )
    parser.add_argument(
        "--genre-packs-path",
        default=None,
        help="Path to genre_packs/ for --seed (auto-detected if omitted).",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Pipe the raw prompt to 'claude -p' and show the narrator's response.",
    )
    args = parser.parse_args()

    # Locate SOUL.md relative to this script (scripts/ -> oq-1/sidequest-api/SOUL.md)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    soul_path = repo_root / "sidequest-api" / "SOUL.md"
    principles = parse_soul_md(soul_path)

    if not principles:
        print(f"WARNING: SOUL.md not found at {soul_path}", file=sys.stderr)

    # Seed Monster Manual from real binaries if requested
    if args.seed:
        genre_packs = args.genre_packs_path or str(repo_root / "sidequest-content" / "genre_packs")
        print(f"Seeding Monster Manual from {args.genre} ...", file=sys.stderr)
        seed_from_binaries(args.genre, genre_packs)
        print(f"  NPCs: {'seeded' if MONSTER_MANUAL_NPCS else 'FAILED (using static)'}", file=sys.stderr)
        print(f"  Encounters: {'seeded' if MONSTER_MANUAL_ENCOUNTERS else 'FAILED (using static)'}", file=sys.stderr)

    sections = build_sections(principles)

    if args.test:
        # Pipe raw prompt to claude -p and show response
        import subprocess
        prompt = render_raw(sections)
        print(f"Testing prompt ({len(prompt.split())} tokens) against claude -p ...", file=sys.stderr)
        result = subprocess.run(
            ["claude", "-p", "--model", "sonnet", prompt],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"ERROR: claude -p failed: {result.stderr}", file=sys.stderr)
            sys.exit(1)
    elif args.raw:
        print(render_raw(sections))
    else:
        total_tokens = sum(len(s.content.split()) for s in sections)
        print(f"Narrator Prompt Preview  ({len(sections)} sections, ~{total_tokens} tokens)")
        print(f"SOUL.md: {soul_path} ({len(principles)} principles)")
        print()
        print(render_labeled(sections))


if __name__ == "__main__":
    main()
