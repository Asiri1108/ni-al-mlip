#!/usr/bin/env bash
# Round-285 production DFT, per-pod execution.
# Usage: bash scripts/run_round285_pod.sh <POD_NUMBER>
#
# Self-contained: reads ONLY its own pod's rows from
# configs/ROUND285_POD_ASSIGNMENT.csv, runs pw.x sequentially for those
# configs only, and writes ONLY its own configs/ROUND285_POD_<NN>_STATUS.txt
# -- never the shared assignment CSV, never another pod's status file.
# Pods are designed to run concurrently on the same volume; this script
# touches nothing outside its own pod's production directory and its own
# status file.
#
# SEALED HANDLING: cfg297/cfg299 (role=SEALED in the assignment CSV) run
# through pw.x exactly like TRAIN configs -- same binary, same pseudos,
# same completion checks. This script NEVER greps, parses, or prints the
# numeric energy/forces/stress from any qe.out, sealed or not -- only
# process-completion markers (JOB DONE., convergence has been achieved,
# exit code, file hashes), the same information cfg109/cfg110's original
# generation script recorded without reading their labels. That discipline
# holds regardless of role; it is called out explicitly here because the
# sealed configs' labels must stay unread until a single, later, explicitly
# designated unsealing event -- same rule as cfg109/cfg110 (2026-08-13 DFT
# run, 2026-08-17 first read).
set -uo pipefail

POD_NUM="${1:?Usage: bash scripts/run_round285_pod.sh <POD_NUMBER>}"
POD_NN=$(printf '%02d' "$POD_NUM")

ROOT=/workspace/ni_al
CSV="$ROOT/configs/ROUND285_POD_ASSIGNMENT.csv"
PROD="$ROOT/data/al3ni_remediation_v1/round285_production_dft/pod${POD_NN}"
STATUS="$ROOT/configs/ROUND285_POD_${POD_NN}_STATUS.txt"
SESSION="ni_al_round285_pod${POD_NUM}"

QE="$ROOT/tools/qe_gpu/builds/sm_89_autoconf/PW/src/pw.x"
QE_SHA=66b7ea9f173b006854fc9e27dc9982c332dad295384803d612da7dad3edc7f8e
PSEUDO_DIR="$ROOT/tools/qe_pseudos"
AL_PSEUDO="$PSEUDO_DIR/Al.pbe-n-kjpaw_psl.1.0.0.UPF"
NI_PSEUDO="$PSEUDO_DIR/ni_pbe_v1.4.uspp.F.UPF"
AL_SHA=fd7b78921e6d0939095b681c328732668eaefd1dee6882fdbc03be463550cc97
NI_SHA=f76b86ce60cde3d83dfcc8df79ba05478db573d158289f1b226919442d977d25

TRAIN_DIR="$ROOT/data/al3ni_remediation_v1/round285_structures/train"
SEALED_DIR="$ROOT/data/al3ni_remediation_v1/round285_structures/sealed_confirmation"

NVROOT=/workspace/ni_al/tools/qe_gpu/nvhpc/Linux_x86_64/26.5
export NVHPC_CUDA_HOME="$NVROOT/cuda/12.9"
export PATH="$NVROOT/compilers/bin:$NVHPC_CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$NVROOT/compilers/lib:$NVHPC_CUDA_HOME/lib64:$NVROOT/math_libs/12.9/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export CUDA_VISIBLE_DEVICES=0
export OMP_NUM_THREADS=8
export OMP_PROC_BIND=close
export OMP_PLACES=cores

utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }
sha() { sha256sum "$1" | awk '{print $1}'; }
die() { printf 'FATAL: %s\n' "$*"; exit 2; }

[[ -f "$CSV" ]] || die "pod assignment CSV missing: $CSV"

# Read ONLY this pod's rows: config_id, role (skip header, filter col2==POD_NUM)
mapfile -t POD_ROWS < <(awk -F, -v pod="$POD_NUM" 'NR>1 && $2==pod {print $1","$3}' "$CSV")
[[ ${#POD_ROWS[@]} -gt 0 ]] || die "no rows found for pod $POD_NUM in $CSV"

declare -a CIDS ROLES CANONICALS
for row in "${POD_ROWS[@]}"; do
  cid="${row%%,*}"
  role="${row##*,}"
  if [[ "$role" == "SEALED" ]]; then
    canonical="$SEALED_DIR/$cid.in"
  else
    canonical="$TRAIN_DIR/$cid.in"
  fi
  CIDS+=("$cid"); ROLES+=("$role"); CANONICALS+=("$canonical")
done

declare -A CFG_STATE
for cid in "${CIDS[@]}"; do CFG_STATE["$cid"]="PENDING"; done
STATE_STR="INIT"

render_status() {
  local tmp="$STATUS.tmp.$$"
  {
    echo "ROUND285 POD${POD_NN} PRODUCTION DFT STATUS"
    echo
    echo "Updated UTC: $(utc)"
    echo "State: $STATE_STR"
    echo "tmux session (expected): $SESSION"
    echo "Production root: $PROD"
    echo "Source: configs/ROUND285_POD_ASSIGNMENT.csv (pod $POD_NUM rows only)"
    echo "QE binary: $QE"
    echo "QE binary SHA256: $QE_SHA"
    echo
    echo "PER-CONFIG TECHNICAL STATUS"
    for i in "${!CIDS[@]}"; do
      printf '%s | role=%s | %s\n' "${CIDS[$i]}" "${ROLES[$i]}" "${CFG_STATE[${CIDS[$i]}]}"
    done
    echo
    echo "PROTECTION ASSERTIONS"
    echo "Other round285 pods modified: NO"
    echo "Shared assignment CSV modified: NO (this script only writes its own STATUS file)"
    echo "cfg109/cfg110 (already unsealed/consumed) touched: NO"
    echo "SEALED config (cfg297/cfg299, if in this pod) energy/forces/stress parsed or printed: NO -- completion status only"
    if [[ "$STATE_STR" == COMPLETE ]]; then
      echo
      echo "FINAL ACQUISITION AUDIT"
      echo "TOTAL EXPECTED: ${#CIDS[@]}"
      echo "COMPLETED: ${#CIDS[@]}"
      echo "FAILED: 0"
    fi
  } > "$tmp"
  mv "$tmp" "$STATUS"
}

[[ "$(tmux display-message -p '#S' 2>/dev/null || true)" == "$SESSION" ]] || die "runner must execute inside tmux session $SESSION"
[[ -x "$QE" ]] || die "QE binary missing or not executable"
[[ "$(sha "$QE")" == "$QE_SHA" ]] || die "QE binary SHA256 mismatch"
[[ "$(sha "$AL_PSEUDO")" == "$AL_SHA" ]] || die "Al pseudopotential SHA256 mismatch"
[[ "$(sha "$NI_PSEUDO")" == "$NI_SHA" ]] || die "Ni pseudopotential SHA256 mismatch"
for c in "${CANONICALS[@]}"; do
  [[ -f "$c" ]] || die "canonical QE input missing: $c"
done

mkdir -p "$PROD"
STATE_STR="RUNNING"
render_status
echo "[$(utc)] Round285 pod${POD_NN} batch starting. ${#CIDS[@]} configs, sequential (single GPU)."

for i in "${!CIDS[@]}"; do
  CID="${CIDS[$i]}"
  ROLE="${ROLES[$i]}"
  CANONICAL="${CANONICALS[$i]}"
  ATTEMPT="$PROD/$CID/attempt_001"
  SCRATCH="$ATTEMPT/tmp"
  EXECUTION_INPUT="$ATTEMPT/execution.in"
  PREFIX="r285pod${POD_NN}_${CID}_a001"

  mkdir -p "$SCRATCH"

  CFG_STATE["$CID"]="RUNNING"
  render_status
  echo "[$(utc)] START $CID (role=$ROLE)"

  sed -e "s|^[[:space:]]*prefix[[:space:]]*=.*|  prefix = '$PREFIX',|" \
      -e "s|^[[:space:]]*pseudo_dir[[:space:]]*=.*|  pseudo_dir = '$PSEUDO_DIR',|" \
      -e "s|^[[:space:]]*outdir[[:space:]]*=.*|  outdir = '$SCRATCH',|" \
      "$CANONICAL" > "$EXECUTION_INPUT"

  {
    echo "CONFIG_ID=$CID"
    echo "ROLE=$ROLE"
    echo "PURPOSE=round285_production_dft_pod${POD_NN}"
    echo "CANONICAL_INPUT=$CANONICAL"
    echo "CANONICAL_INPUT_SHA256=$(sha "$CANONICAL")"
    echo "EXECUTION_INPUT=$EXECUTION_INPUT"
    echo "EXECUTION_INPUT_SHA256=$(sha "$EXECUTION_INPUT")"
    echo "QE_BINARY=$QE"
    echo "QE_BINARY_SHA256=$QE_SHA"
    echo "AL_PSEUDO_SHA256=$AL_SHA"
    echo "NI_PSEUDO_SHA256=$NI_SHA"
    echo "PREFIX=$PREFIX"
    echo "OUTDIR=$SCRATCH"
    echo "START_TIMESTAMP=$(utc)"
  } > "$ATTEMPT/execution_metadata.env"

  set +e
  "$QE" -in "$EXECUTION_INPUT" > "$ATTEMPT/qe.out" 2> "$ATTEMPT/qe.err"
  rc=$?
  set -e

  end=$(utc)
  output="$ATTEMPT/qe.out"
  # Completion-status checks ONLY -- these grep for fixed marker strings
  # (job-done / convergence banners), never for numeric energy, force, or
  # stress values. This applies identically to TRAIN and SEALED roles.
  job_done=NO; scf=NO; gpu_active=NO
  [[ $rc -eq 0 ]] && grep -q 'JOB DONE\.' "$output" && job_done=YES
  grep -q 'convergence has been achieved' "$output" && scf=YES
  grep -q 'GPU acceleration is ACTIVE' "$output" && gpu_active=YES
  out_sha=$(sha "$output" 2>/dev/null || echo NONE)

  {
    echo "END_TIMESTAMP=$end"
    echo "EXIT_CODE=$rc"
    echo "JOB_DONE=$job_done"
    echo "SCF_CONVERGED=$scf"
    echo "GPU_ACCELERATION_ACTIVE=$gpu_active"
    echo "OUTPUT_SHA256=$out_sha"
  } >> "$ATTEMPT/execution_metadata.env"

  cfg_status="COMPLETE"
  [[ $rc -eq 0 && "$job_done" == YES && "$scf" == YES ]] || cfg_status="FAILED"
  CFG_STATE["$CID"]="$cfg_status"

  if [[ "$cfg_status" == COMPLETE ]]; then
    # config_complete.env -- same key set the cfg109/cfg110 generation and
    # unsealing scripts use, so a future unsealing pass for cfg297/cfg299
    # can reuse that exact precedent. No energy/forces/stress fields here.
    {
      echo "CONFIG_ID=$CID"
      echo "EXIT_CODE=$rc"
      echo "JOB_DONE=YES"
      echo "SCF_CONVERGED=YES"
      echo "OUTPUT_SHA256=$out_sha"
    } > "$ATTEMPT/config_complete.env"
    echo "$cfg_status" > "$ATTEMPT/DONE_MARKER.txt"
  fi

  echo "[$end] DONE $CID rc=$rc JOB_DONE=$job_done SCF_CONVERGED=$scf GPU_ACTIVE=$gpu_active status=$cfg_status"

  if [[ "$cfg_status" == FAILED ]]; then
    STATE_STR="FAILED"
    render_status
    echo "[$(utc)] STOPPING BATCH: $CID failed (rc=$rc job_done=$job_done scf=$scf)"
    exit 1
  fi
  render_status
done

STATE_STR="COMPLETE"
render_status
sync
echo "[$(utc)] Round285 pod${POD_NN} batch complete. All ${#CIDS[@]} configs PASS."
