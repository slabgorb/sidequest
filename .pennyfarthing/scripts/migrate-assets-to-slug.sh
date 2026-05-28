#!/usr/bin/env bash
# Migrate asset filenames from role-based to slug-based naming
# Usage: ./scripts/migrate-assets-to-slug.sh [--dry-run]
#
# Derives slug from shortName (or first word of character name)
# Renames: portraits, faces

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "=== DRY RUN MODE ==="
fi

THEMES_DIR="$PROJECT_DIR/pennyfarthing-dist/personas/themes"
PORTRAITS_DIR="$PROJECT_DIR/pennyfarthing-dist/personas/portraits"
FACES_DIR="$PROJECT_DIR/pennyfarthing-dist/personas/faces/by-theme"
ROLES="orchestrator sm tea dev reviewer architect pm tech-writer ux-designer devops ba"

# Generate base slug from name (matches loader.ts toSlug function)
to_slug() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//'
}

# Get OCEAN suffix from theme YAML (e.g., "54432")
get_ocean_suffix() {
    local theme_file="$1"
    local role="$2"
    local o c e a n
    o=$(yq ".agents.$role.ocean.O" "$theme_file")
    c=$(yq ".agents.$role.ocean.C" "$theme_file")
    e=$(yq ".agents.$role.ocean.E" "$theme_file")
    a=$(yq ".agents.$role.ocean.A" "$theme_file")
    n=$(yq ".agents.$role.ocean.N" "$theme_file")
    echo "${o}${c}${e}${a}${n}"
}

rename_file() {
    local src="$1"
    local dst="$2"

    if [[ "$src" == "$dst" ]]; then
        return 0
    fi

    # Skip if destination already exists (another role with same slug already migrated)
    if [[ -f "$dst" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "  [SKIP] $(basename "$dst") already exists"
        fi
        return 0
    fi

    if [[ -f "$src" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "  [DRY] mv $(basename "$src") -> $(basename "$dst")"
        else
            mv "$src" "$dst"
            echo "  mv $(basename "$src") -> $(basename "$dst")"
        fi
    fi
}

total_renames=0
skipped=0

# Process each theme
for theme_file in "$THEMES_DIR"/*.yaml; do
    theme=$(basename "$theme_file" .yaml)
    echo "Processing theme: $theme"

    for role in $ROLES; do
        # Get shortName, fallback to first word of character
        short_name=$(yq ".agents.$role.shortName // \"\"" "$theme_file")
        if [[ -z "$short_name" || "$short_name" == "null" ]]; then
            char=$(yq ".agents.$role.character // \"\"" "$theme_file")
            if [[ -z "$char" || "$char" == "null" ]]; then
                echo "  Skipping $role - no character defined"
                continue
            fi
            short_name="${char%% *}"  # First word
        fi

        base_slug=$(to_slug "$short_name")
        ocean_suffix=$(get_ocean_suffix "$theme_file" "$role")
        slug="${base_slug}-${ocean_suffix}"

        # Skip if slug matches role (no rename needed)
        if [[ "$slug" == "$role" ]]; then
            ((skipped++))
            continue
        fi

        echo "  $role -> $slug (from '$short_name')"

        # Rename portraits
        if [[ -d "$PORTRAITS_DIR/$theme" ]]; then
            rename_file "$PORTRAITS_DIR/$theme/$role.png" "$PORTRAITS_DIR/$theme/$slug.png"
            ((total_renames++)) || true
        fi

        # Rename faces
        if [[ -d "$FACES_DIR/$theme" ]]; then
            rename_file "$FACES_DIR/$theme/$role.svg" "$FACES_DIR/$theme/$slug.svg"
            ((total_renames++)) || true
        fi

    done
    echo ""
done

echo "=== Migration Summary ==="
echo "Total renames: $total_renames"
echo "Skipped (slug=role): $skipped"
if [[ "$DRY_RUN" == "true" ]]; then
    echo "(Dry run - no files were changed)"
fi
