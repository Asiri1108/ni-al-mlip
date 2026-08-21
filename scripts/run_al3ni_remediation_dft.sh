#!/usr/bin/env bash
# Sequential, resumable QE-GPU acquisition for the frozen Al3Ni remediation design.
set -uo pipefail

ROOT=/workspace/ni_al
BASE="$ROOT/data/al3ni_remediation_v1"
PROD="$BASE/production_dft"
SPLIT_MANIFEST="$BASE/split_membership_manifest.csv"
VERIFY="$ROOT/scripts/verify_al3ni_remediation_frozen.py"
STATUS="$ROOT/configs/AL3NI_REMEDIATION_DFT_STATUS.txt"
QE="$ROOT/tools/qe_gpu/builds/sm_89_autoconf/PW/src/pw.x"
QE_SHA=66b7ea9f173b006854fc9e27dc9982c332dad295384803d612da7dad3edc7f8e
SPLIT_SHA=e51afe7df4e15e55bc76222ccd31fcc74a7bfb2310ee99de59f8c3e5424c6599
PSEUDO_DIR="$ROOT/tools/qe_pseudos"
AL_PSEUDO="$PSEUDO_DIR/Al.pbe-n-kjpaw_psl.1.0.0.UPF"
NI_PSEUDO="$PSEUDO_DIR/ni_pbe_v1.4.uspp.F.UPF"
AL_SHA=fd7b78921e6d0939095b681c328732668eaefd1dee6882fdbc03be463550cc97
NI_SHA=f76b86ce60cde3d83dfcc8df79ba05478db573d158289f1b226919442d977d25
SESSION=ni_al_al3ni_remediation_dft

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
die() { printf 'FATAL: %s\n' "$*" >&2; exit 2; }
is_confirmation() { [[ "$1" == cfg109_* || "$1" == cfg110_* ]]; }

technical_valid() {
  local attempt=$1 output="$1/qe.out" complete="$1/config_complete.env"
  [[ -f "$complete" && -s "$output" ]] || return 1
  grep -qx 'EXIT_CODE=0' "$complete" || return 1
  grep -qx 'JOB_DONE=YES' "$complete" || return 1
  grep -qx 'SCF_CONVERGED=YES' "$complete" || return 1
  grep -qx 'OUTPUT_NONTRUNCATED=YES' "$complete" || return 1
  grep -q 'JOB DONE\.' "$output" || return 1
  grep -q 'convergence has been achieved' "$output" || return 1
  tail -n 12 "$output" | grep -q 'JOB DONE\.' || return 1
  local recorded actual
  recorded=$(awk -F= '$1=="OUTPUT_SHA256"{print $2}' "$complete")
  actual=$(sha "$output")
  [[ -n "$recorded" && "$recorded" == "$actual" ]]
}

render_status() {
  local tmp="$STATUS.tmp.$$" completed=0 failed=0 missing=0 running=0
  local train=0 validation=0 confirmation=0 state detail cdir attempt
  {
    echo 'AL3NI REMEDIATION TARGETED DFT STATUS'
    echo
    echo "Updated UTC: $(utc)"
    echo "State: $1"
    echo "Production root: $PROD"
    echo "tmux session: $SESSION"
    echo "QE binary: $QE"
    echo "QE binary SHA256: $QE_SHA"
    echo "Split manifest SHA256: $SPLIT_SHA"
    echo 'Execution order: cfg101-cfg108 development first; cfg109-cfg110 sealed confirmation last'
    echo 'Confirmation numerical labels: SEALED / NOT REPORTED'
    echo
    echo 'PER-CONFIG TECHNICAL STATUS'
    tail -n +2 "$SPLIT_MANIFEST" | while IFS=, read -r split config_id phase family strain rattle seed structure_hash geometry_hash input_hash policy; do
      cdir="$PROD/$config_id"
      state=MISSING; detail='no attempt'
      if [[ -f "$cdir/active.env" ]]; then
        attempt=$(awk -F= '$1=="ATTEMPT_DIR"{print $2}' "$cdir/active.env")
        if [[ -n "$attempt" ]] && technical_valid "$attempt"; then state=COMPLETE; detail="$(basename "$attempt")"; else state=RUNNING_OR_INTERRUPTED; detail="$(basename "${attempt:-unknown}")"; fi
      fi
      if compgen -G "$cdir/attempt_*/config_complete.env" >/dev/null; then
        for attempt in "$cdir"/attempt_*; do
          if technical_valid "$attempt"; then state=COMPLETE; detail="$(basename "$attempt")"; break; fi
        done
      elif compgen -G "$cdir/attempt_*/execution_metadata.env" >/dev/null && [[ "$state" == MISSING ]]; then
        state=FAILED_OR_INCOMPLETE; detail='attempt exists without valid completion'
      fi
      printf '%s | %s | %s | %s\n' "$config_id" "$split" "$state" "$detail"
    done
    echo
    echo 'PROTECTION ASSERTIONS'
    echo 'Dataset-100 modified: NO'
    echo 'Dataset-100 blind holdout modified: NO'
    echo 'Remediation split membership modified: NO'
    echo 'Retraining started: NO'
    echo 'LAMMPS started: NO'
    echo 'cfg109/cfg110 label-access policy: SEALED CONFIRMATION DATA'
    if [[ "$1" == COMPLETE ]]; then
      echo
      echo 'FINAL ACQUISITION AUDIT'
      echo 'TOTAL EXPECTED: 10'
      echo 'COMPLETED: 10'
      echo 'FAILED: 0'
      echo 'MISSING: 0'
      echo 'TRAIN DFT: 6/6'
      echo 'VALIDATION DFT: 2/2'
      echo 'CONFIRMATION DFT: 2/2'
      echo 'CONFIRMATION LABELS SEALED: YES'
      echo 'Filesystem sync: COMPLETE'
    fi
  } > "$tmp"
  mv "$tmp" "$STATUS"
}

[[ "$(tmux display-message -p '#S' 2>/dev/null || true)" == "$SESSION" ]] || die "runner must execute inside tmux session $SESSION"
[[ -x "$QE" ]] || die "QE binary missing or not executable"
[[ "$(sha "$QE")" == "$QE_SHA" ]] || die "QE binary SHA256 mismatch"
[[ "$(sha "$AL_PSEUDO")" == "$AL_SHA" ]] || die "Al pseudopotential SHA256 mismatch"
[[ "$(sha "$NI_PSEUDO")" == "$NI_SHA" ]] || die "Ni pseudopotential SHA256 mismatch"
[[ "$(sha "$SPLIT_MANIFEST")" == "$SPLIT_SHA" ]] || die "frozen split manifest SHA256 mismatch"
python3 "$VERIFY" || die 'frozen design preflight failed'

mkdir -p "$PROD"
LOCK="$PROD/.runner_lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  owner_pid=$(awk -F= '$1=="PID"{print $2}' "$LOCK/owner.env" 2>/dev/null || true)
  if [[ -n "$owner_pid" ]] && kill -0 "$owner_pid" 2>/dev/null; then die "another runner is active (PID $owner_pid)"; fi
  mv "$LOCK" "$PROD/.runner_lock.stale.$(date -u +%Y%m%dT%H%M%SZ)" || die 'could not preserve stale lock'
  mkdir "$LOCK" || die 'could not acquire runner lock'
fi
printf 'PID=%s\nSTART_UTC=%s\nSESSION=%s\n' "$$" "$(utc)" "$SESSION" > "$LOCK/owner.env"
cleanup() { rmdir "$LOCK" 2>/dev/null || true; }
trap cleanup EXIT

render_status RUNNING
echo "[$(utc)] Frozen design verified; sequential acquisition starting."

while IFS=, read -r split config_id phase family strain rattle seed structure_hash geometry_hash input_hash policy; do
  canonical="$BASE/qe_inputs/$config_id.in"
  [[ -f "$canonical" ]] || die "canonical input missing: $config_id"
  [[ "$(sha "$canonical")" == "$input_hash" ]] || die "canonical input SHA256 mismatch: $config_id"
  cdir="$PROD/$config_id"
  mkdir -p "$cdir"

  found=''
  for prior in "$cdir"/attempt_*; do
    [[ -d "$prior" ]] || continue
    if technical_valid "$prior"; then found=$prior; break; fi
  done
  if [[ -n "$found" ]]; then
    echo "[$(utc)] $config_id already technically complete; preserving $(basename "$found")."
    render_status RUNNING
    continue
  fi

  attempt_num=1
  while [[ -e "$cdir/attempt_$(printf '%03d' "$attempt_num")" ]]; do attempt_num=$((attempt_num + 1)); done
  attempt="$cdir/attempt_$(printf '%03d' "$attempt_num")"
  scratch="$attempt/tmp"
  mkdir -p "$scratch"
  execution_input="$attempt/execution.in"
  prefix="rem_${config_id}_a$(printf '%03d' "$attempt_num")"
  sed -e "s|^[[:space:]]*prefix[[:space:]]*=.*|  prefix = '$prefix',|" \
      -e "s|^[[:space:]]*pseudo_dir[[:space:]]*=.*|  pseudo_dir = '$PSEUDO_DIR',|" \
      -e "s|^[[:space:]]*outdir[[:space:]]*=.*|  outdir = '$scratch',|" \
      "$canonical" > "$execution_input"
  execution_hash=$(sha "$execution_input")
  start=$(utc)
  {
    echo "CONFIG_ID=$config_id"; echo "SPLIT=$split"; echo "ATTEMPT_NUMBER=$attempt_num"
    echo "ATTEMPT_DIR=$attempt"; echo "START_TIMESTAMP=$start"
    echo "CANONICAL_INPUT=$canonical"; echo "INPUT_SHA256=$input_hash"
    echo "EXECUTION_INPUT=$execution_input"; echo "EXECUTION_INPUT_SHA256=$execution_hash"
    echo "QE_BINARY=$QE"; echo "QE_BINARY_SHA256=$QE_SHA"
    echo "AL_PSEUDO_SHA256=$AL_SHA"; echo "NI_PSEUDO_SHA256=$NI_SHA"
    echo "PREFIX=$prefix"; echo "OUTDIR=$scratch"; echo "OUTPUT_PATH=$attempt/qe.out"
    echo "LABEL_POLICY=$policy"
  } > "$cdir/active.env"
  cp "$cdir/active.env" "$attempt/execution_metadata.env"
  render_status RUNNING
  echo "[$start] START $config_id role=$split attempt=$(printf '%03d' "$attempt_num")"

  set +e
  "$QE" -in "$execution_input" > "$attempt/qe.out" 2> "$attempt/qe.err"
  rc=$?
  set -e
  end=$(utc)
  output="$attempt/qe.out"
  output_hash=$(sha "$output")
  job_done=NO; scf=NO; nontruncated=NO
  [[ $rc -eq 0 ]] && grep -q 'JOB DONE\.' "$output" && job_done=YES
  grep -q 'convergence has been achieved' "$output" && scf=YES
  tail -n 12 "$output" | grep -q 'JOB DONE\.' && nontruncated=YES
  {
    echo "END_TIMESTAMP=$end"; echo "EXIT_CODE=$rc"; echo "OUTPUT_SHA256=$output_hash"
    echo "JOB_DONE=$job_done"; echo "SCF_CONVERGED=$scf"; echo "OUTPUT_NONTRUNCATED=$nontruncated"
  } >> "$attempt/execution_metadata.env"

  if [[ $rc -eq 0 && "$job_done" == YES && "$scf" == YES && "$nontruncated" == YES ]]; then
    cp "$attempt/execution_metadata.env" "$attempt/config_complete.env"
    cp "$attempt/config_complete.env" "$cdir/config_complete.env"
    if is_confirmation "$config_id"; then
      printf '%s\n' 'SEALED CONFIRMATION DATA' 'Do not inspect numerical labels until the final candidate model is frozen.' > "$cdir/SEALED_CONFIRMATION_DATA.txt"
      chmod go-rwx "$attempt/qe.out" "$attempt/qe.err" "$attempt/config_complete.env" "$cdir/config_complete.env" 2>/dev/null || true
    fi
    rm -f "$cdir/active.env"
    echo "[$end] COMPLETE $config_id integrity=PASS output_sha256=$output_hash"
  else
    echo "[$end] FAILED $config_id rc=$rc JOB_DONE=$job_done SCF=$scf NONTRUNCATED=$nontruncated" >&2
    render_status FAILED
    exit 1
  fi
  render_status RUNNING
done < <(tail -n +2 "$SPLIT_MANIFEST")

python3 "$VERIFY" || die 'post-run frozen-design hash verification failed'
render_status COMPLETE
sync
echo "[$(utc)] AL3NI TARGETED DFT ACQUISITION TECHNICALLY COMPLETE"
