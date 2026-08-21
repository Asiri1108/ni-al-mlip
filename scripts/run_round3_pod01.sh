#!/usr/bin/env bash
# Round-3 production DFT batch, pod01 execution session: covers the
# ROUND3_POD_ASSIGNMENT.csv rows for pod_number 1-5 (9 configs), run
# sequentially on a single GPU. Does NOT touch cfg109/cfg110, any
# round1/round2 production tree, or pods 6-10. Status is written to
# configs/POD_01_STATUS.txt only.
set -uo pipefail

ROOT=/workspace/ni_al
BASE="$ROOT/data/al3ni_remediation_v1"
QEINPUTS_BASE="$BASE/round3_structures"
PROD="$BASE/round3_production_dft/pod01"
STATUS="$ROOT/configs/POD_01_STATUS.txt"
SESSION=ni_al_round3_pod01

QE="$ROOT/tools/qe_gpu/builds/sm_89_autoconf/PW/src/pw.x"
QE_SHA=66b7ea9f173b006854fc9e27dc9982c332dad295384803d612da7dad3edc7f8e
PSEUDO_DIR="$ROOT/tools/qe_pseudos"
AL_PSEUDO="$PSEUDO_DIR/Al.pbe-n-kjpaw_psl.1.0.0.UPF"
NI_PSEUDO="$PSEUDO_DIR/ni_pbe_v1.4.uspp.F.UPF"
AL_SHA=fd7b78921e6d0939095b681c328732668eaefd1dee6882fdbc03be463550cc97
NI_SHA=f76b86ce60cde3d83dfcc8df79ba05478db573d158289f1b226919442d977d25

# pod_folder:config_id, in ROUND3_POD_ASSIGNMENT.csv row order, filtered to
# pod_number 1-5 only.
CONFIGS=(
  pod_01:cfg117_Al3Ni2_biaxial_xy_compression
  pod_02:cfg118_AlNi3_volume_rattle_compression
  pod_03:cfg119_AlNi3_volume_rattle_compression
  pod_04:cfg121_Al3Ni5_uniaxial_x_expansion
  pod_05:cfg123_Al3Ni_biaxial_xy_expansion
  pod_01:cfg135_AlNi3_shear_rattle_xz_negative
  pod_02:cfg137_Al3Ni2_orthorhombic_xy
  pod_03:cfg139_AlNi_orthorhombic_yz
  pod_04:cfg141_AlNi3_orthorhombic_xz
)

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

STATE_STR="INIT"
declare -A CFG_STATE
for entry in "${CONFIGS[@]}"; do CFG_STATE["${entry#*:}"]="PENDING"; done

render_status() {
  local tmp="$STATUS.tmp.$$"
  {
    echo 'ROUND3 POD01 PRODUCTION DFT STATUS'
    echo
    echo "Updated UTC: $(utc)"
    echo "State: $STATE_STR"
    echo "tmux session: $SESSION"
    echo "Production root: $PROD"
    echo "Source: configs/ROUND3_POD_ASSIGNMENT.csv (pod_number 1-5 rows only)"
    echo "QE binary: $QE"
    echo "QE binary SHA256: $QE_SHA"
    echo
    echo 'PER-CONFIG TECHNICAL STATUS'
    for entry in "${CONFIGS[@]}"; do
      cid="${entry#*:}"
      printf '%s | %s\n' "$cid" "${CFG_STATE[$cid]}"
    done
    echo
    echo 'PROTECTION ASSERTIONS'
    echo 'Pods 6-10 modified: NO'
    echo 'round1/round2 production trees modified: NO'
    echo 'cfg109/cfg110 sealed confirmation data touched: NO'
    if [[ "$STATE_STR" == COMPLETE ]]; then
      echo
      echo 'FINAL ACQUISITION AUDIT'
      echo "TOTAL EXPECTED: ${#CONFIGS[@]}"
      echo "COMPLETED: ${#CONFIGS[@]}"
      echo 'FAILED: 0'
    fi
  } > "$tmp"
  mv "$tmp" "$STATUS"
}

[[ "$(tmux display-message -p '#S' 2>/dev/null || true)" == "$SESSION" ]] || die "runner must execute inside tmux session $SESSION"
[[ -x "$QE" ]] || die "QE binary missing or not executable"
[[ "$(sha "$QE")" == "$QE_SHA" ]] || die "QE binary SHA256 mismatch"
[[ "$(sha "$AL_PSEUDO")" == "$AL_SHA" ]] || die "Al pseudopotential SHA256 mismatch"
[[ "$(sha "$NI_PSEUDO")" == "$NI_SHA" ]] || die "Ni pseudopotential SHA256 mismatch"

mkdir -p "$PROD"
STATE_STR="RUNNING"
render_status
echo "[$(utc)] Round3 pod01 batch starting. ${#CONFIGS[@]} configs (pods 1-5), sequential (single GPU)."

for entry in "${CONFIGS[@]}"; do
  podfolder="${entry%%:*}"
  CID="${entry#*:}"
  CANONICAL="$QEINPUTS_BASE/$podfolder/$CID.in"
  ATTEMPT="$PROD/$CID/attempt_001"
  SCRATCH="$ATTEMPT/tmp"
  EXECUTION_INPUT="$ATTEMPT/execution.in"
  PREFIX="r3pod01_${CID}_a001"

  if [[ -f "$ATTEMPT/DONE_MARKER.txt" && "$(cat "$ATTEMPT/DONE_MARKER.txt")" == "COMPLETE" ]]; then
    CFG_STATE["$CID"]="COMPLETE"
    render_status
    echo "[$(utc)] SKIP $CID (already COMPLETE from prior attempt, DONE_MARKER found)"
    continue
  fi

  [[ -f "$CANONICAL" ]] || die "canonical QE input missing: $CID ($CANONICAL)"
  mkdir -p "$SCRATCH"

  CFG_STATE["$CID"]="RUNNING"
  render_status
  echo "[$(utc)] START $CID (pod_number source: $podfolder)"

  sed -e "s|^[[:space:]]*prefix[[:space:]]*=.*|  prefix = '$PREFIX',|" \
      -e "s|^[[:space:]]*pseudo_dir[[:space:]]*=.*|  pseudo_dir = '$PSEUDO_DIR',|" \
      -e "s|^[[:space:]]*outdir[[:space:]]*=.*|  outdir = '$SCRATCH',|" \
      "$CANONICAL" > "$EXECUTION_INPUT"

  {
    echo "CONFIG_ID=$CID"
    echo "SOURCE_POD_FOLDER=$podfolder"
    echo "PURPOSE=round3_production_dft_pod01"
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
  job_done=NO; scf=NO
  [[ $rc -eq 0 ]] && grep -q 'JOB DONE\.' "$output" && job_done=YES
  grep -q 'convergence has been achieved' "$output" && scf=YES

  {
    echo "END_TIMESTAMP=$end"
    echo "EXIT_CODE=$rc"
    echo "JOB_DONE=$job_done"
    echo "SCF_CONVERGED=$scf"
    echo "OUTPUT_SHA256=$(sha "$output" 2>/dev/null || echo NONE)"
  } >> "$ATTEMPT/execution_metadata.env"

  cfg_status="COMPLETE"
  [[ $rc -eq 0 && "$job_done" == YES && "$scf" == YES ]] || cfg_status="FAILED"
  CFG_STATE["$CID"]="$cfg_status"
  echo "$cfg_status" > "$ATTEMPT/DONE_MARKER.txt"

  echo "[$end] DONE $CID rc=$rc JOB_DONE=$job_done SCF_CONVERGED=$scf status=$cfg_status"

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
echo "[$(utc)] Round3 pod01 batch complete. All ${#CONFIGS[@]} configs PASS."
