#!/usr/bin/env bash
# Quick read-only status/progress summary for all round3 pod runner
# sessions. Reads configs/POD_*_STATUS.txt and tmux session state only --
# never modifies anything.
set -uo pipefail
CONFDIR=/workspace/ni_al/configs

echo "=== tmux sessions ==="
tmux ls 2>/dev/null | grep 'ni_al_round3_pod' || echo "(none running)"
echo

for f in "$CONFDIR"/POD_*_STATUS.txt; do
  [[ -f "$f" ]] || continue
  name=$(basename "$f")
  state=$(grep -m1 '^State:' "$f" | cut -d' ' -f2-)
  if [[ -z "$state" ]]; then
    echo "--- $name : no real run yet (stale/placeholder content) ---"
    continue
  fi
  total=$(grep -cE '^cfg[0-9]+_.* \| ' "$f")
  complete=$(grep -cE '^cfg[0-9]+_.* \| COMPLETE$' "$f")
  running=$(grep -cE '^cfg[0-9]+_.* \| RUNNING$' "$f")
  failed=$(grep -cE '^cfg[0-9]+_.* \| FAILED$' "$f")
  pending=$(grep -cE '^cfg[0-9]+_.* \| PENDING$' "$f")
  current=$(grep -E '^cfg[0-9]+_.* \| RUNNING$' "$f" | head -1 | cut -d'|' -f1 | xargs)
  echo "--- $name : state=$state  progress=$complete/$total  (running=$running pending=$pending failed=$failed)"
  [[ -n "$current" ]] && echo "    currently running: $current"
done
