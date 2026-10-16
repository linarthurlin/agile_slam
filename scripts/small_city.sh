#!/usr/bin/env bash
# Start the canonical small_city simulation through WSL.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# == 0 ]] || { echo "Use scripts/deploy.py; the legacy GPU overlay is retired." >&2; exit 2; }
exec python3 "$root/scripts/deploy.py" up
