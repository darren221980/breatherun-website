#!/usr/bin/env bash
# Thin wrapper so the theme swap is one command from the repo root:
#   ./tools/switch-theme.sh holly
#   ./tools/switch-theme.sh --list
#   ./tools/switch-theme.sh --check
#   ./tools/switch-theme.sh holly --brand ~/src/breatherun-brand
#
# The brand asset pack is not in this repo. The first run asks where yours is
# and saves the answer to .brandpath; $BREATHERUN_BRAND overrides it.
set -euo pipefail
exec python3 "$(dirname "$0")/switch-theme.py" "$@"
