#!/usr/bin/env bash
set -euo pipefail
ROOT=/workspace/ni_al
echo "=== RANK TEST 1/2: rank=8 START $(date -u +%FT%TZ) ==="
bash "$ROOT/scripts/run_al3ni_combined220_rank8_mace_training.sh"
echo "=== RANK TEST 1/2: rank=8 DONE $(date -u +%FT%TZ) ==="
echo "=== RANK TEST 2/2: rank=16 START $(date -u +%FT%TZ) ==="
bash "$ROOT/scripts/run_al3ni_combined220_rank16_mace_training.sh"
echo "=== RANK TEST 2/2: rank=16 DONE $(date -u +%FT%TZ) ==="
echo "=== RANK TEST: BOTH RUNS COMPLETE ==="
