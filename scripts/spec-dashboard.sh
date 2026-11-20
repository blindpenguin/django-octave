#!/usr/bin/env bash
# Start the Spec Workflow approval dashboard for this repo.
# Default: http://localhost:5000
#
# Usage:
#   ./scripts/spec-dashboard.sh
#   ./scripts/spec-dashboard.sh --port 8080
#   ./scripts/spec-dashboard.sh --no-open
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v npx >/dev/null 2>&1; then
  echo "npx not found. Install Node.js (includes npm/npx), then retry." >&2
  exit 1
fi

PORT="${SPEC_DASHBOARD_PORT:-5000}"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT="${2:?--port requires a value}"
      shift 2
      ;;
    --port=*)
      PORT="${1#*=}"
      shift
      ;;
    -h|--help)
      cat <<EOF
Start Spec Workflow dashboard for django-octave.

Usage: $(basename "$0") [--port PORT] [--no-open] [extra npx args...]

Environment:
  SPEC_DASHBOARD_PORT   Default port when --port is omitted (default: 5000)

Opens http://localhost:<port> (unless --no-open).
EOF
      exit 0
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

echo "Spec Workflow dashboard → http://localhost:${PORT}"
echo "Project: ${ROOT}"
echo "Ctrl+C to stop."
echo

exec npx -y @pimzino/spec-workflow-mcp@latest "$ROOT" --dashboard --port "$PORT" "${EXTRA_ARGS[@]}"
