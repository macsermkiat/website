#!/usr/bin/env bash
# Stop the preview launch.sh started on this port and remove its build. Evidence in .verify/evidence/ is kept.
# Usage: .claude/skills/verify/scripts/cleanup.sh [port]
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
PORT="${1:-4417}"
RUN="$ROOT/.verify/run-$PORT"
if [ -f "$RUN/pid" ]; then
  pid="$(cat "$RUN/pid")"
  if kill -0 "$pid" 2>/dev/null; then kill "$pid"; for _ in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$pid" 2>/dev/null || break; sleep 0.3; done; kill -9 "$pid" 2>/dev/null; echo "stopped pid $pid"; fi
fi
rm -rf "$RUN"
echo "removed $RUN; evidence kept in $ROOT/.verify/evidence/"
