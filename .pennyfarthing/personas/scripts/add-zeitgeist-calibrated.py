#!/usr/bin/env python3
"""Add calibrated zeitgeist scores to theme YAML files.

Inserts zeitgeist block after theme: section without rewriting entire file.
"""

from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).parent
PERSONAS_DIR = SCRIPT_DIR.parent
THEMES_DIR = PERSONAS_DIR / "themes"
SCORES_FILE = PERSONAS_DIR / "zeitgeist-scores.yaml"


def main():
    if not SCORES_FILE.exists():
        print(f"Error: {SCORES_FILE} not found")
        return

    # Load calibrated scores
    with open(SCORES_FILE) as f:
        scores_data = yaml.safe_load(f)

    calibrated = scores_data.get("calibrated", {})
    print(f"Loaded {len(calibrated)} calibrated scores")
    print("Adding calibrated zeitgeist scores to theme files...\n")

    count = 0
    skipped = 0

    for theme_name, score_info in calibrated.items():
        theme_file = THEMES_DIR / f"{theme_name}.yaml"

        if not theme_file.exists():
            print(f"  SKIP: {theme_name} (file not found)")
            skipped += 1
            continue

        composite = score_info.get("composite")
        rating = score_info.get("rating")

        if not composite:
            print(f"  SKIP: {theme_name} (no score)")
            skipped += 1
            continue

        # Read theme file
        content = theme_file.read_text()

        # Check if already has zeitgeist
        if "zeitgeist:" in content:
            print(f"  SKIP: {theme_name} (already has zeitgeist)")
            skipped += 1
            continue

        # Insert zeitgeist block before "agents:" line
        zeitgeist_block = f"zeitgeist:\n  score: {composite}\n  rating: {rating}\n\n"

        # Find the agents: line and insert before it
        if "\nagents:" in content:
            content = content.replace("\nagents:", f"\n{zeitgeist_block}agents:")
        elif "agents:" in content:
            content = content.replace("agents:", f"{zeitgeist_block}agents:")
        else:
            print(f"  SKIP: {theme_name} (no agents section found)")
            skipped += 1
            continue

        # Write back
        theme_file.write_text(content)

        print(f"  Added: {theme_name} (score: {composite}, rating: {rating})")
        count += 1

    print(f"\nDone! Added zeitgeist to {count} themes, skipped {skipped}.")


if __name__ == "__main__":
    main()
