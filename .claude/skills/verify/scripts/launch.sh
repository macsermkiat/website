#!/usr/bin/env bash
# Build the site with analytics off into a private folder and serve it with `vite preview` on its own port.
# Usage: .claude/skills/verify/scripts/launch.sh [port]   (default 4417; the smoke test owns 4317)
# Prints the market URL once the server answers. State lives in .verify/run-<port>/ (removed by cleanup.sh).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
PORT="${1:-4417}"
RUN="$ROOT/.verify/run-$PORT"
SITE="$ROOT/site"

if [ -f "$RUN/pid" ] && kill -0 "$(cat "$RUN/pid")" 2>/dev/null; then
  echo "already running: pid $(cat "$RUN/pid") on port $PORT (run doctor.sh $PORT, or cleanup.sh $PORT first)" >&2
  exit 1
fi
if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
  echo "port $PORT is taken by something this script did not start; pick another port" >&2
  exit 1
fi
mkdir -p "$RUN"

[ -d "$SITE/node_modules/vite" ] || (cd "$SITE" && npm ci --no-audit --no-fund)
# VITE_GA_ID= overrides site/.env.production: a verification run must not count as a visit in Mac's Google Analytics
(cd "$SITE" && VITE_GA_ID= node node_modules/vite/bin/vite.js build --outDir "$RUN/dist" --emptyOutDir > "$RUN/build.log" 2>&1) \
  || { echo "build failed, see $RUN/build.log" >&2; tail -20 "$RUN/build.log" >&2; exit 1; }
if grep -rqs "G-[A-Z0-9]\{10\}" "$RUN/dist/assets/"analytics-*.js; then echo "analytics ID still in the build; refusing to serve" >&2; exit 1; fi

cd "$SITE"
nohup node node_modules/vite/bin/vite.js preview --outDir "$RUN/dist" --port "$PORT" --strictPort > "$RUN/server.log" 2>&1 &
echo $! > "$RUN/pid"
for _ in $(seq 1 60); do
  if curl -fsS -o /dev/null "http://localhost:$PORT/website/" 2>/dev/null; then
    echo "ready: http://localhost:$PORT/website/  (pid $(cat "$RUN/pid"), state $RUN)"
    exit 0
  fi
  kill -0 "$(cat "$RUN/pid")" 2>/dev/null || { echo "preview exited, see $RUN/server.log" >&2; cat "$RUN/server.log" >&2; exit 1; }
  sleep 0.5
done
echo "preview did not answer in 30 s, see $RUN/server.log" >&2
exit 1
