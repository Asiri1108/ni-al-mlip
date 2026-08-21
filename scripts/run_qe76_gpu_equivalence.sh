#!/usr/bin/env bash
set -euo pipefail
root=/workspace/ni_al
base="$root/data/expansion_026_100/gpu_benchmark/cpu_gpu_equivalence"
pw="$root/tools/qe_gpu/builds/sm_89_autoconf/bin/pw.x"
sdk="$root/tools/qe_gpu/nvhpc/Linux_x86_64/26.5"
export PATH="$sdk/compilers/bin:$sdk/cuda/12.9/bin:$PATH"
export LD_LIBRARY_PATH="$sdk/compilers/lib:$sdk/cuda/12.9/lib64:$sdk/math_libs/12.9/lib64:${LD_LIBRARY_PATH:-}"
export OMP_NUM_THREADS=4
mkdir -p "$base"
for phase in AlNi Al3Ni AlNi3; do
  id="${phase}_iso_m02"
  dir="$base/$id"
  if [ -s "$dir/gpu.out" ] && grep -q 'JOB DONE' "$dir/gpu.out"; then
    printf 'SKIP_COMPLETED %s\n' "$id"
    continue
  fi
  src="$root/data/raw_dft/diverse_pilot_01/$phase/iso_m02/$id.in"
  mkdir -p "$dir/tmp"
  sed -e "s|^[[:space:]]*pseudo_dir.*|   pseudo_dir = '$root/tools/qe_pseudos',|" \
      -e "s|^[[:space:]]*outdir.*|   outdir = '$dir/tmp',|" "$src" > "$dir/gpu.in"
  sha256sum "$src" "$dir/gpu.in" > "$dir/input_hashes.txt"
  start=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf 'timestamp,utilization.gpu,memory.used\n' > "$dir/nvidia_smi.csv"
  (while :; do nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used --format=csv,noheader,nounits >> "$dir/nvidia_smi.csv"; sleep 1; done) & sampler=$!
  set +e
  start_ns=$(date +%s%N)
  "$pw" -in "$dir/gpu.in" > "$dir/gpu.out" 2> "$dir/gpu.err"
  code=$?
  end_ns=$(date +%s%N)
  set -e
  kill "$sampler" 2>/dev/null || true
  wait "$sampler" 2>/dev/null || true
  end=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  awk -v a="$start_ns" -v b="$end_ns" 'BEGIN {printf "WALL_SECONDS=%.3f\n", (b-a)/1000000000}' > "$dir/time.txt"
  printf 'START=%s\nEND=%s\nEXIT_CODE=%s\n' "$start" "$end" "$code" > "$dir/run_status.txt"
  grep -E 'Program PWSCF|GPU acceleration|JOB DONE|convergence has been achieved|convergence NOT achieved' "$dir/gpu.out" > "$dir/evidence.txt" || true
  if [ "$code" -ne 0 ] || ! grep -q 'JOB DONE' "$dir/gpu.out"; then exit 20; fi
done
