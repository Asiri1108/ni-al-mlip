#!/usr/bin/env bash
set -euo pipefail
ROOT=/workspace/ni_al
RUNNER="$ROOT/scripts/run_dataset100_gpu_chunk.sh"
case "${POD_ID:-}" in
  01) chunks='06 01';; 02) chunks='07 02';; 03) chunks='04 08';; 04) chunks='05 09';; 05) chunks='10 03';;
  *) echo 'ERROR: POD_ID must be exactly 01 through 05' >&2; exit 2;;
esac
session="ni_al_prod_pod_$POD_ID"
[ -n "${TMUX:-}" ] && [ "$(tmux display-message -p '#S' 2>/dev/null || true)" = "$session" ] || { echo "ERROR: run only inside tmux session $session" >&2; exit 3; }
for chunk in $chunks; do
  checkpoint="$ROOT/configs/production_chunks/chunk_${chunk}_checkpoint.txt"
  if grep -q '^Overall state: COMPLETE$' "$checkpoint" 2>/dev/null; then continue; fi
  env POD_ID="$POD_ID" CHUNK_ID="$chunk" bash -x "$RUNNER"
  grep -q '^Overall state: COMPLETE$' "$checkpoint" || { echo "ERROR: chunk_$chunk did not complete; Pod stops" >&2; exit 10; }
done
