#!/bin/bash
# Add zeitgeist_score field to all theme YAML files
# Run from pennyfarthing-dist/personas directory

THEMES_DIR="$(dirname "$0")/../themes"

# Function to add zeitgeist_score after tier line
add_score() {
    local file="$1"
    local score="$2"

    # Check if zeitgeist_score already exists
    if grep -q "zeitgeist_score:" "$file"; then
        echo "  Skipping $file (already has zeitgeist_score)"
        return
    fi

    # Add zeitgeist_score after tier line
    if grep -q "tier:" "$file"; then
        sed -i '' "/^  tier:/a\\
\\  zeitgeist_score: $score
" "$file"
        echo "  Added zeitgeist_score: $score to $file"
    else
        echo "  WARNING: No tier field found in $file"
    fi
}

echo "Adding zeitgeist scores to theme files..."

# Exceptional
for theme in discworld firefly star-wars west-wing breaking-bad dune the-wire succession the-sopranos mad-men game-of-thrones; do
    [ -f "$THEMES_DIR/$theme.yaml" ] && add_score "$THEMES_DIR/$theme.yaml" "exceptional"
done

# Rich
for theme in the-expanse ted-lasso parks-and-rec catch-22 better-call-saul babylon-5 battlestar-galactica sherlock-holmes doctor-who lord-of-the-rings hitchhikers-guide foundation mass-effect arcane avatar-the-last-airbender cowboy-bebop futurama the-good-place the-office the-simpsons marvel-mcu watchmen vorkosigan-saga his-dark-materials neuromancer snow-crash bobiverse expeditionary-force hannibal fargo justified peaky-blinders deadwood black-sails the-americans twin-peaks x-files the-matrix blade-runner the-crown rome inspector-morse software-pioneers wwii-leaders; do
    [ -f "$THEMES_DIR/$theme.yaml" ] && add_score "$THEMES_DIR/$theme.yaml" "rich"
done

# Moderate
for theme in superfriends a-team princess-bride mash jane-austen agatha-christie dickens shakespeare moby-dick great-gatsby 1984 count-of-monte-cristo don-quixote les-miserables gothic-literature the-odyssey arthurian-mythos greek-mythology norse-mythology alice-in-wonderland monty-python big-lebowski mad-max the-witcher ancient-philosophers ancient-strategists enlightenment-thinkers classical-composers jazz-legends film-auteurs renaissance-masters russian-masters scientific-revolutionaries military-commanders historical-figures world-explorers; do
    [ -f "$THEMES_DIR/$theme.yaml" ] && add_score "$THEMES_DIR/$theme.yaml" "moderate"
done

# Thin
for theme in gilligans-island legion-of-doom star-trek-tng star-trek-tos; do
    [ -f "$THEMES_DIR/$theme.yaml" ] && add_score "$THEMES_DIR/$theme.yaml" "thin"
done

# Minimal
for theme in control all-stars; do
    [ -f "$THEMES_DIR/$theme.yaml" ] && add_score "$THEMES_DIR/$theme.yaml" "minimal"
done

echo "Done!"
