#!/usr/bin/env bash
set -euo pipefail
ROOT=/workspace/ni_al
RUNNER="$ROOT/scripts/run_dataset100_gpu_chunk.sh"
for id in 01 02 03 04 05 06 07 08 09 10; do
  session="ni_al_prod_chunk_$id"; checkpoint="$ROOT/configs/production_chunks/chunk_${id}_checkpoint.txt"
  if grep -q '^Overall state: COMPLETE$' "$checkpoint" 2>/dev/null; then continue; fi
  if tmux has-session -t "$session" 2>/dev/null; then echo "Adopting existing $session"
  else tmux new-session -d -s "$session" "env CHUNK_ID=$id $RUNNER"
  fi
  while tmux has-session -t "$session" 2>/dev/null; do sleep 30; done
  grep -q '^Overall state: COMPLETE$' "$checkpoint" || { echo "Chunk $id did not complete; stopping" >&2; exit 1; }
done
