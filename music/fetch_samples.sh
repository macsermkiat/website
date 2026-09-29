#!/usr/bin/env bash
# Fetch the freely licensed sample libraries the ballad is rendered from into music/.samples/.
# Only the files the renderer uses are checked out (blobless, sparse), about 550 MB.
# Licences: see CREDITS.md (music writer) and each repo's LICENSE.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p .samples && cd .samples

clone() { # repo dir
  [ -d "$2/.git" ] || git clone -q --depth 1 --filter=blob:none --no-checkout "https://github.com/$1" "$2"
}

# Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0), SFZ/FLAC edition by sfzinstruments
clone sfzinstruments/SalamanderGrandPiano SalamanderGrandPiano
( cd SalamanderGrandPiano
  git checkout -q HEAD -- LICENSE README.md
  files=$(git ls-tree -r --name-only HEAD Samples | grep -E "^Samples/(A|C|D#|F#)[1-6]v(3|5|7|9|11)\.flac$|^Samples/C7v(3|5|7|9|11)\.flac$")
  git checkout -q HEAD -- $files )

# Karoryfer Meatbass (1958 Otto Rubner double bass, CC0), pizzicato only
clone sfzinstruments/karoryfer.meatbass karoryfer.meatbass
( cd karoryfer.meatbass && git checkout -q HEAD -- LICENSE readme.txt Programs Samples/pizz )

# Virtuosity Drums (Versilian Studios / Austin McMahon, CC0), jazz kit: overhead + room mics
clone sfzinstruments/virtuosity_drums virtuosity_drums
( cd virtuosity_drums
  git checkout -q HEAD -- LICENSE README.md
  files=$(git ls-tree -r --name-only HEAD Samples/oh Samples/room Samples/kickmic Samples/snaremic \
    | grep -E "_(kick_snoff|kick_snon|snare_center|snare_offcenter|snare_buzz|snare_muted|snareoff_center|hh_pedal|hh_closed|ride_ride|flatride_ride|crash_sizzle)_")
  git checkout -q HEAD -- $files )

# MTG Solo Saxophones, tenor (recorded by the Music Technology Group, UPF, on freesound.org; trimmed and
# mapped by kinwie; CC BY 4.0): soft (p) and loud (f) sustained notes, breath noises and key clicks
clone sfzinstruments/MTG.SoloSax MTG.SoloSax
( cd MTG.SoloSax
  git checkout -q HEAD -- LICENSE README.md "MTG Solo Saxophones/Data" "MTG Solo Saxophones/MTG Tenor Sax (NL).sfz"
  git ls-tree -r -z --name-only HEAD "MTG Solo Saxophones/Samples" | grep -z -E "/ten_(p|f|b|k)_[0-9]+\.flac$" \
    | xargs -0 git checkout -q HEAD -- )

# Karoryfer Swirly Drums (a jazz kit played with brushes, CC0): snare hits, digs, stirs and flutters,
# the brushed ride, hi-hat foot, marching kick (dry "Samples/" set only)
clone sfzinstruments/karoryfer.swirly-drums karoryfer.swirly-drums
( cd karoryfer.swirly-drums
  git checkout -q HEAD -- license changelog.txt Programs/mappings
  git ls-tree -r -z --name-only HEAD Samples | grep -z -E "^Samples/(snare_main|snare_edge|snare_dig|snare_stir|snare_flutter|ride|hat_foot|marching_kick)/" \
    | xargs -0 git checkout -q HEAD -- )

# Tenor sax, per-note renders by gleitz/midi-js-soundfonts:
#   MusyngKite (CC BY-SA 3.0): the shipped tenor; FluidR3_GM (Frank Wen, CC BY 3.0): the A/B alternative
for bank in MusyngKite FluidR3_GM; do
  mkdir -p gleitz/$bank
  [ -f gleitz/$bank/tenor_sax-ogg.js ] || curl -sSf -o gleitz/$bank/tenor_sax-ogg.js \
    https://raw.githubusercontent.com/gleitz/midi-js-soundfonts/gh-pages/$bank/tenor_sax-ogg.js
done
echo "samples ready in $(pwd)"
