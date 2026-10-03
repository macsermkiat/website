#!/usr/bin/env bash
# Launch build_props.py with its log inside the vendor's own output folder, never anywhere else.
#
#   blender/props/run_build.sh <tag> [build_props.py args...]
#       log: blender/out/vendor/logs/<tag>.log   (NM_DEVICE / NM_THREADS default to CPU / 2)
#
# Guards: every path is derived from this script's own location (no caller variables), each is checked to
# be non-empty and inside the repo's vendor-owned output folders before anything is written, and the tag
# may only hold letters, digits, '-', '_' and '.' (no '/' or empty tag, so no log can land in / or elsewhere).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
TAG="${1:-}"
if [[ -z "$TAG" || ! "$TAG" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "run_build.sh: give a log tag of letters, digits, '.', '_' or '-' (got '${TAG}')" >&2
  exit 2
fi
shift
LOGDIR="$REPO/blender/out/vendor/logs"
case "$LOGDIR" in
  "$REPO"/blender/out/vendor/logs) ;;
  *) echo "run_build.sh: refusing log folder '$LOGDIR'" >&2; exit 2 ;;
esac
if [[ -z "$REPO" || "$REPO" == "/" || ! -f "$REPO/docs/BUILD.md" ]]; then
  echo "run_build.sh: could not locate the repo (got '$REPO')" >&2
  exit 2
fi
mkdir -p "$LOGDIR"
LOG="$LOGDIR/$TAG.log"
export NM_DEVICE="${NM_DEVICE:-CPU}" NM_THREADS="${NM_THREADS:-2}"
echo "[run_build] $(date -u +%FT%TZ) build_props.py $* -> $LOG"
exec /home/claude/tools/bpy-venv/bin/python "$HERE/build_props.py" "$@" >"$LOG" 2>&1
