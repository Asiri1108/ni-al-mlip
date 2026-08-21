#!/usr/bin/env bash
# Read-only monitor for all round285 pods, via the shared network volume --
# does not care which host/GPU actually runs each pod. Run this in its own
# terminal:
#   watch -n 5 bash /workspace/ni_al/scripts/watch_round285_pods.sh
set -uo pipefail

ROOT=/workspace/ni_al
PROD_BASE="$ROOT/data/al3ni_remediation_v1/round285_production_dft"

echo "=== Round285 pod status ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
echo

for nn in 01 02 03; do
  status_file="$ROOT/configs/ROUND285_POD_${nn}_STATUS.txt"
  echo "--- POD ${nn} ---"
  if [[ ! -f "$status_file" ]]; then
    echo "  (no status file yet)"
    echo
    continue
  fi
  state=$(grep '^State:' "$status_file" | awk '{print $2}')
  updated=$(grep '^Updated UTC:' "$status_file" | cut -d' ' -f3-)
  echo "  State: $state   Last updated: $updated"
  grep -E '^\S+ \| role=' "$status_file" | sed 's/^/  /'

  running_cid=$(grep -E '^\S+ \| role=\S+ \| RUNNING$' "$status_file" | cut -d' ' -f1)
  if [[ -n "${running_cid:-}" ]]; then
    qeout="$PROD_BASE/pod${nn}/${running_cid}/attempt_001/qe.out"
    if [[ -f "$qeout" ]]; then
      lines=$(wc -l < "$qeout")
      echo "  Live: $running_cid  (qe.out: $lines lines)"
      tail -n 4 "$qeout" | sed 's/^/    | /'
    fi
  fi
  echo
done
