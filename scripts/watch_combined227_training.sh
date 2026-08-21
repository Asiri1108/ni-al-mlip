#!/usr/bin/env bash
# Read-only monitor for all 3 combined-227 seed-variance training runs.
# Run in its own terminal:
#   watch -n 5 bash /workspace/ni_al/scripts/watch_combined227_training.sh
set -uo pipefail

ROOT=/workspace/ni_al
echo "=== combined-227 training status ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
echo

for seed_name in \
  "20260811:al3ni_combined227_lora_v1" \
  "20260812:al3ni_combined227_seed20260812_lora_v1" \
  "20260813:al3ni_combined227_seed20260813_lora_v1"; do
  seed="${seed_name%%:*}"
  name="${seed_name##*:}"
  model="$ROOT/models/$name/${name}.model"
  log="$ROOT/logs/$name/training_console.log"
  echo "--- seed $seed ($name) ---"
  if [[ -f "$model" ]]; then
    echo "  DONE -- model: $model"
  elif [[ -f "$log" ]]; then
    last_epoch=$(grep -oE '^[0-9-]+ [0-9:.]+ INFO: Epoch [0-9]+' "$log" | tail -1)
    echo "  RUNNING -- $last_epoch"
    tail -n 2 "$log" | sed 's/^/    | /'
  else
    echo "  NOT STARTED"
  fi
  echo
done

echo "--- driver ---"
tail -n 3 "$ROOT/logs/combined227_seed_variance/driver_console.log" 2>/dev/null | sed 's/^/  /'
