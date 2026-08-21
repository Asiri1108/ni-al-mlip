#!/usr/bin/env bash
set -euo pipefail
ROOT=/workspace/ni_al
NAME=al3ni_combined113_lora_v1
LOGDIR="$ROOT/logs/$NAME"
mkdir -p "$LOGDIR"
date +%s > "$LOGDIR/start_epoch_seconds.txt"
nvidia-smi --query-gpu=index,name,uuid,driver_version,memory.total --format=csv,noheader > "$LOGDIR/gpu_info.csv"
printf '%s\n' 'export XDG_CACHE_HOME=/workspace/ni_al/runs/dataset100_matpes_pbe_lora_v1/downloads (reused: already has the foundation model cached)' 'export TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1' '/workspace/ni_al/envs/mace-py312-cu128/bin/mace_run_train --config=/workspace/ni_al/configs/al3ni_combined113_lora_v1.yaml' > "$LOGDIR/LAUNCH_COMMAND.txt"
(
  while true; do
    nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used --format=csv,noheader,nounits || true
    sleep 5
  done
) > "$LOGDIR/gpu_monitor.csv" 2>&1 &
MONITOR_PID=$!
trap 'kill "$MONITOR_PID" 2>/dev/null || true' EXIT
export XDG_CACHE_HOME="$ROOT/runs/dataset100_matpes_pbe_lora_v1/downloads"
export TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1
"$ROOT/envs/mace-py312-cu128/bin/mace_run_train" --config="$ROOT/configs/$NAME.yaml" 2>&1 | tee "$LOGDIR/training_console.log"
kill "$MONITOR_PID" 2>/dev/null || true
wait "$MONITOR_PID" 2>/dev/null || true
trap - EXIT
echo "TRAINING SUBPROCESS DONE"
