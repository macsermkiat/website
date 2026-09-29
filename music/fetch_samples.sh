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

# Tenor sax, per-note renders by gleitz/midi-js-soundfonts:
#   MusyngKite (CC BY-SA 3.0): the shipped tenor; FluidR3_GM (Frank Wen, CC BY 3.0): the A/B alternative
for bank in MusyngKite FluidR3_GM; do
  mkdir -p gleitz/$bank
  [ -f gleitz/$bank/tenor_sax-ogg.js ] || curl -sSf -o gleitz/$bank/tenor_sax-ogg.js \
    https://raw.githubusercontent.com/gleitz/midi-js-soundfonts/gh-pages/$bank/tenor_sax-ogg.js
done
echo "samples ready in $(pwd)"
