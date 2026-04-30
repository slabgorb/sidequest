#!/usr/bin/env python3
"""
add_short_names.py - Pre-generate shortName field for theme characters

Finds the shortest unique identifier that distinguishes each character.

Usage:
  python add_short_names.py                    # Dry run - show what would change
  python add_short_names.py --write            # Actually write changes
  python add_short_names.py --theme discworld  # Only process one theme
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def find_project_root() -> Path:
    """Find project root by looking for .pennyfarthing directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".pennyfarthing").is_dir():
            return current
        current = current.parent
    return Path.cwd()


# Common titles/prefixes to strip for comparison
SKIP_PREFIXES = {
    'the', 'dr.', 'dr', 'captain', 'admiral', 'colonel', 'lieutenant', 'commander',
    'president', 'lord', 'lady', 'sir', 'professor', 'inspector', 'sergeant',
    'mr.', 'mr', 'mrs.', 'mrs', 'miss', 'ms.', 'ms', 'chief', 'major', 'general',
    'king', 'queen', 'prince', 'princess', 'duke', 'earl', 'count', 'baron',
    'first', 'grand', 'arch', 'high',
    'uncle', 'aunt', 'brother', 'sister', 'father', 'mother', 'friar',
    'avatar', 'agent', 'detective', 'officer', 'private', 'corporal',
    'chancellor', 'ambassador', 'senator', 'governor', 'minister',
    'master', 'young', 'old', 'elder', 'reverend', 'bishop', 'cardinal'
}

# Words that make poor short names on their own
POOR_SHORT_NAMES = {
    'big', 'little', 'old', 'young', 'true', 'false', 'good', 'bad',
    'thought', 'ministry', 'situation', 'room', 'place', 'house',
    'superintendent', 'commander', 'speaker', 'council',
    'mode', 'narrator', 'chronicler',
    'h.m.', 'j.f.', 'a.w.', 'e.b.', 'l.'
}

# Names that should use the full form (iconic two-word names)
USE_FULL_NAME = {'big brother', 'sun tzu'}


def extract_nickname(name: str) -> str | None:
    """Extract quoted nickname from character name if present."""
    match = re.search(r'["\']([^"\']+)["\']', name)
    if match:
        nickname = match.group(1).strip()
        if nickname and ' ' not in nickname:
            return nickname
    return None


def clean_name(name: str) -> str:
    """Clean character name by removing parenthetical annotations and slash alternatives."""
    cleaned = re.sub(r'\s*\([^)]+\)\s*', ' ', name).strip()
    cleaned = re.sub(r'\b\w+/(\w+)\s', r'\1 ', cleaned)
    cleaned = re.sub(r'\s*["\'][^"\']+["\']\s*', ' ', cleaned).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def tokenize(name: str) -> list[str]:
    """Tokenize a name into meaningful parts."""
    cleaned = clean_name(name)
    words = [w for w in cleaned.split() if w]

    filtered = [
        w for w in words
        if w.lower() not in SKIP_PREFIXES
        and not re.match(r'^[A-Z]\.$', w)
        and not re.match(r'^[IVXLCDM]+$', w)
    ]

    return filtered if filtered else words


def compute_short_names(agents: dict) -> dict[str, str]:
    """Compute display name map for all characters in a theme."""
    characters = [
        a['character'] for a in agents.values()
        if a and a.get('character')
    ]

    def is_unique(candidate: str, except_for: str) -> bool:
        candidate_lower = candidate.lower()
        for char in characters:
            if char == except_for:
                continue
            tokens = tokenize(char)
            if any(t.lower() == candidate_lower for t in tokens):
                return False
        return True

    def is_good_short_name(candidate: str) -> bool:
        return candidate.lower() not in POOR_SHORT_NAMES and len(candidate) > 1

    def find_short_name(full_name: str) -> str:
        cleaned = clean_name(full_name)

        if cleaned.lower() in USE_FULL_NAME:
            return cleaned

        nickname = extract_nickname(full_name)
        if nickname and is_good_short_name(nickname):
            return nickname

        tokens = tokenize(full_name)

        if not tokens:
            return cleaned

        if len(tokens) == 1:
            return tokens[0]

        # Strategy 1: First token (if good and unique)
        if is_good_short_name(tokens[0]) and is_unique(tokens[0], full_name):
            return tokens[0]

        # Strategy 2: Last token (surname, if good and unique)
        last_token = tokens[-1]
        if is_good_short_name(last_token) and is_unique(last_token, full_name):
            return last_token

        # Strategy 3: First + Last
        if len(tokens) >= 2:
            first_last = f"{tokens[0]} {last_token}"
            if is_unique(first_last, full_name):
                return first_last

        return clean_name(full_name)

    return {char: find_short_name(char) for char in characters}


def process_theme(filepath: Path, dry_run: bool = True) -> dict:
    """Process a single theme file."""
    content = filepath.read_text()
    theme = yaml.safe_load(content)

    if not theme or 'agents' not in theme:
        print(f"  Skipping {filepath.name} - no agents found")
        return {'changes': 0, 'filename': filepath.name}

    short_names = compute_short_names(theme['agents'])
    changes = 0

    for role, agent in theme['agents'].items():
        if not agent or 'character' not in agent:
            continue

        short_name = short_names.get(agent['character'])
        existing = agent.get('shortName')

        if short_name and short_name != existing:
            if dry_run:
                existing_note = f' (was: "{existing}")' if existing else ''
                print(f'  {role}: "{agent["character"]}" -> "{short_name}"{existing_note}')
            agent['shortName'] = short_name
            changes += 1

    if not dry_run and changes > 0:
        with open(filepath, 'w') as f:
            yaml.dump(theme, f, default_flow_style=False, allow_unicode=True, width=1000)
        print(f"  Wrote {changes} changes to {filepath.name}")

    return {'changes': changes, 'filename': filepath.name}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pre-generate shortName field for theme characters"
    )
    parser.add_argument('--write', action='store_true',
                        help='Actually write changes (default: dry run)')
    parser.add_argument('--theme', type=str,
                        help='Only process one theme')
    args = parser.parse_args()

    dry_run = not args.write

    project_root = find_project_root()
    themes_dir = project_root / 'pennyfarthing-dist' / 'personas' / 'themes'

    print('DRY RUN - No files will be modified\n' if dry_run else 'WRITING CHANGES\n')

    files = sorted(themes_dir.glob('*.yaml'))
    if args.theme:
        theme_file = f"{args.theme}.yaml" if not args.theme.endswith('.yaml') else args.theme
        files = [f for f in files if f.name == theme_file]

    total_changes = 0
    for file in files:
        print(f"\n{file.name}:")
        result = process_theme(file, dry_run)
        total_changes += result['changes']
        if result['changes'] == 0:
            print('  (no changes needed)')

    print(f"\n{'=' * 50}")
    print(f"Total: {total_changes} changes across {len(files)} themes")
    if dry_run and total_changes > 0:
        print("\nRun with --write to apply changes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
