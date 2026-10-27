#!/usr/bin/env bash
# Read-only: is the instance on this port ours, up, built from this checkout, and free of analytics?
# Usage: .claude/skills/verify/scripts/doctor.sh [port]   Exit 0 = worth driving.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
PORT="${1:-4417}"
RUN="$ROOT/.verify/run-$PORT"
BASE="http://localhost:$PORT/website/"
bad=0
ok() { echo "  ok   $*"; }
no() { echo "  FAIL $*"; bad=1; }

[ -f "$RUN/pid" ] && kill -0 "$(cat "$RUN/pid")" 2>/dev/null && ok "preview pid $(cat "$RUN/pid") is alive" || no "no live preview started by launch.sh on port $PORT ($RUN/pid)"
html="$(curl -fsS "$BASE" 2>/dev/null)" && ok "$BASE answers" || no "$BASE does not answer"
main="$(printf '%s' "$html" | grep -o 'assets/main-[A-Za-z0-9_-]*\.js' | head -1)"
if [ -n "$main" ] && [ -f "$RUN/dist/$main" ]; then ok "the served page is our build ($main in $RUN/dist)"; else no "the served page is not the build in $RUN/dist (someone else's server on this port?)"; fi
newer="$(find "$ROOT/site/src" "$ROOT/site/index.html" "$ROOT/content" -newer "$RUN/dist/index.html" -type f 2>/dev/null | head -3)"
[ -z "$newer" ] && ok "build is newer than site/src and content/" || no "source changed after the build (relaunch): $newer"
curl -fsS "$BASE/plain.html" -o /dev/null 2>/dev/null && ok "plain.html answers" || no "plain.html does not answer"
curl -fsS "${BASE}models/gluehwein.lite.glb.gz" -o /dev/null 2>/dev/null && ok "models are served (gluehwein.lite.glb.gz)" || no "models missing from the build"
if grep -qs "G-[A-Z0-9]\{10\}" "$RUN"/dist/assets/analytics-*.js; then no "the build carries a Google Analytics ID"; else ok "no Google Analytics ID in the build"; fi
(cd "$ROOT/site" && node -e "import('playwright').catch(()=>import('/opt/node22/lib/node_modules/playwright/index.mjs')).then(()=>process.exit(0),()=>process.exit(1))") \
  && ok "playwright importable" || no "playwright not importable from site/ (npm i -D playwright, or use the preinstalled one)"
exit $bad
