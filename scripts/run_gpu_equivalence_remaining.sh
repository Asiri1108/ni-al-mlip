#!/usr/bin/env bash
set -u

NVROOT=/workspace/ni_al/tools/qe_gpu/nvhpc/Linux_x86_64/26.5
QE=/workspace/ni_al/tools/qe_gpu/builds/sm_89_autoconf/PW/src/pw.x
ROOT=/workspace/ni_al/data/expansion_026_100/gpu_benchmark/cpu_gpu_equivalence
PSEUDO=/workspace/ni_al/tools/qe_pseudos

export PATH="$NVROOT/compilers/bin:$PATH"
export NVHPC_CUDA_HOME="$NVROOT/cuda/12.9"
export LD_LIBRARY_PATH="$NVROOT/compilers/lib:$NVROOT/cuda/12.9/lib64:$NVROOT/math_libs/12.9/lib64:${LD_LIBRARY_PATH:-}"
export CUDA_VISIBLE_DEVICES=0
export OMP_NUM_THREADS=8
export OMP_PROC_BIND=close
export OMP_PLACES=cores

run_case() {
    case_id=$1
    case_dir="$ROOT/$case_id"
    input="$case_dir/gpu.in"
    output="$case_dir/gpu.out"
    monitor="$case_dir/nvidia_smi.csv"
    evidence="$case_dir/evidence.txt"

    if [ -s "$output" ] && rg -q 'JOB DONE' "$output"; then
        printf '%s already has JOB DONE; preserving it.\n' "$case_id"
        return 0
    fi

    start_iso=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    start_epoch=$(date +%s)
    command_line="env CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=8 OMP_PROC_BIND=close OMP_PLACES=cores $QE -in $input"
    {
        printf 'CASE=%s\n' "$case_id"
        printf 'START_UTC=%s\n' "$start_iso"
        printf 'LAUNCH_COMMAND=%s\n' "$command_line"
        printf 'MPI_RANKS=1\nOPENMP_THREADS=8\nQE_POOLS=1 (no -nk split)\n'
        printf 'QE_SHA256=%s\n' "$(sha256sum "$QE" | awk '{print $1}')"
        printf 'INPUT_SHA256=%s\n' "$(sha256sum "$input" | awk '{print $1}')"
        printf 'AL_SHA256=%s\n' "$(sha256sum "$PSEUDO/Al.pbe-n-kjpaw_psl.1.0.0.UPF" | awk '{print $1}')"
        printf 'NI_SHA256=%s\n' "$(sha256sum "$PSEUDO/ni_pbe_v1.4.uspp.F.UPF" | awk '{print $1}')"
    } > "$evidence"

    nvidia-smi --query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,power.draw,clocks.sm --format=csv,nounits -l 1 > "$monitor" 2> "$case_dir/nvidia_smi.err" &
    monitor_pid=$!
    "$QE" -in "$input" > "$output" 2> "$case_dir/gpu.err"
    exit_code=$?
    kill "$monitor_pid" 2>/dev/null || true
    wait "$monitor_pid" 2>/dev/null || true
    end_epoch=$(date +%s)
    end_iso=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    {
        printf 'END_UTC=%s\n' "$end_iso"
        printf 'WALL_SECONDS=%s\n' "$((end_epoch-start_epoch))"
        printf 'EXIT_CODE=%s\n' "$exit_code"
        if rg -q 'JOB DONE' "$output"; then printf 'JOB_DONE=YES\n'; else printf 'JOB_DONE=NO\n'; fi
        if rg -q 'convergence has been achieved' "$output"; then printf 'SCF_CONVERGED=YES\n'; else printf 'SCF_CONVERGED=NO\n'; fi
    } >> "$evidence"
    sync
    return "$exit_code"
}

run_case Al3Ni_iso_m02 || exit $?
run_case AlNi3_iso_m02 || exit $?
