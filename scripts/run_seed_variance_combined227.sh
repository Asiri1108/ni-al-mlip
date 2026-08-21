#!/usr/bin/env bash
set -euo pipefail
ROOT=/workspace/ni_al
echo "=== COMBINED227 SEED VARIANCE RUN 1/2: seed 20260812 START $(date -u +%FT%TZ) ==="
bash "$ROOT/scripts/run_al3ni_combined227_seed20260812_mace_training.sh"
echo "=== COMBINED227 SEED VARIANCE RUN 1/2: seed 20260812 DONE $(date -u +%FT%TZ) ==="
echo "=== COMBINED227 SEED VARIANCE RUN 2/2: seed 20260813 START $(date -u +%FT%TZ) ==="
bash "$ROOT/scripts/run_al3ni_combined227_seed20260813_mace_training.sh"
echo "=== COMBINED227 SEED VARIANCE RUN 2/2: seed 20260813 DONE $(date -u +%FT%TZ) ==="
echo "=== COMBINED227 SEED VARIANCE: BOTH RUNS COMPLETE ==="
