#!/usr/bin/env bash
# Open the optional clients in the canonical Compose project.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# == 0 || ( $# == 1 && "$1" == motion ) ]] || { echo "Usage: bash scripts/gui.sh [motion]" >&2; exit 2; }
exec python3 "$root/scripts/deploy.py" up --gui
