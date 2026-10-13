#!/usr/bin/env bash
# kyuma-mic: built-in mic -> micfilter DSP -> virtual `kyuma_mic` source.
# Run via the systemd user unit (or by hand). Sets kyuma_mic as the
# system default source, so OBS/calls/browsers all get the cleaned mic.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
FIFO=/tmp/kyuma-mic.pipe
MODFILE=/tmp/kyuma-mic.mod
MIC="${KYUMA_MIC_TARGET:-}"
if [ -z "$MIC" ]; then
    MIC="$(pactl list sources short | awk '/alsa_input\./ {print $2; exit}')"
fi
[ -n "$MIC" ] || { echo "no mic source found"; exit 1; }

cleanup() {
    if [ -f "$MODFILE" ]; then
        pactl unload-module "$(cat "$MODFILE")" 2>/dev/null
        rm -f "$MODFILE" "$FIFO"
    fi
    echo "kyuma-mic stopped"
}
trap cleanup EXIT INT TERM

rm -f "$FIFO"
mkfifo "$FIFO" || exit 1
MOD="$(pactl load-module module-pipe-source file="$FIFO" source_name=kyuma_mic \
    source_properties=device.description=KyumaMic rate=16000 channels=1 format=s16le)"
echo "$MOD" > "$MODFILE"
pactl set-default-source kyuma_mic
echo "kyuma-mic live from $MIC (module $MOD), default source set"

# shellcheck disable=SC2094
pw-record --rate 16000 --channels 1 --format s16 --target "$MIC" - 2>/dev/null \
    | "$REPO/.venv/bin/python" "$REPO/stt/micfilter.py" > "$FIFO"
