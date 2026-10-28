#!/usr/bin/env bash
# Narrated run of the whole loop for screen recording: one banner per stage, real commands, nothing faked.
# Usage: scripts/demo_run.sh CLIP TRACK X,Y [TRACK_OFFSET_SECONDS]
set -euo pipefail
cd "$(dirname "$0")/.."
CLIP=${1:?clip}; TRACK=${2:?track}; TAP=${3:?x,y}; OFFSET=${4:-0}
banner() { printf '\n\033[1;35m== %s ==\033[0m\n' "$*"; }
banner "1/3  Meta Model API: is the key good, is SAM 3.1 available?"
.venv/bin/python scripts/sam_smoke_test.py | grep -E '^(OK|FAIL|WARN|MILESTONE)' | cut -c1-110
banner "2/3  Full loop: ingest, SAM 3.1 tracks the subject, beat map, render, export"
.venv/bin/python -m beatmask.pipeline --clip "$CLIP" --track "$TRACK" --tap "$TAP" \
  --track-offset "$OFFSET" --segmenter sam --effect glow --name demo --out renders/demo_run.mp4
banner "3/3  Done"
ls -lh renders/demo_run.mp4
