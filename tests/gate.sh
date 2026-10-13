#!/usr/bin/env bash
# Usage: ./tests/gate.sh <NN>  — run gate tests for phase NN. Non-zero exit on any failure.
set -u
NN="${1:?usage: gate.sh <phase-NN>}"
DIR="tests/phase-$NN"
[ -d "$DIR" ] || { echo "SKIP: $DIR does not exist yet"; exit 2; }
PYBIN="$(dirname "$0")/../.venv/bin/python"
[ -x "$PYBIN" ] || PYBIN="python3"
"$PYBIN" -m pytest "$DIR" -q
