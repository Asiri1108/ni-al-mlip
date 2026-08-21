#!/usr/bin/env bash
set -uo pipefail
ROOT=/workspace/ni_al
QE="$ROOT/tools/qe_gpu/builds/sm_89_autoconf/PW/src/pw.x"
QH=66b7ea9f173b006854fc9e27dc9982c332dad295384803d612da7dad3edc7f8e
PD="$ROOT/tools/qe_pseudos"
AH=fd7b78921e6d0939095b681c328732668eaefd1dee6882fdbc03be463550cc97
NH=f76b86ce60cde3d83dfcc8df79ba05478db573d158289f1b226919442d977d25
NVROOT="$ROOT/tools/qe_gpu/nvhpc/Linux_x86_64/26.5"
case "${CHUNK_ID:-}" in 01|02|03|04|05|06|07|08|09|10) ;; *) echo 'ERROR: CHUNK_ID must be exactly 01 through 10' >&2; exit 2;; esac
SESSION="ni_al_prod_chunk_$CHUNK_ID"
POD_SESSION=""
case "${POD_ID:-}" in
  01) [ "$CHUNK_ID" = 06 ] || [ "$CHUNK_ID" = 01 ] || { echo 'ERROR: POD 01 owns only chunks 06 and 01' >&2; exit 3; }; POD_SESSION=ni_al_prod_pod_01 ;;
  02) [ "$CHUNK_ID" = 07 ] || [ "$CHUNK_ID" = 02 ] || { echo 'ERROR: POD 02 owns only chunks 07 and 02' >&2; exit 3; }; POD_SESSION=ni_al_prod_pod_02 ;;
  03) [ "$CHUNK_ID" = 04 ] || [ "$CHUNK_ID" = 08 ] || { echo 'ERROR: POD 03 owns only chunks 04 and 08' >&2; exit 3; }; POD_SESSION=ni_al_prod_pod_03 ;;
  04) [ "$CHUNK_ID" = 05 ] || [ "$CHUNK_ID" = 09 ] || { echo 'ERROR: POD 04 owns only chunks 05 and 09' >&2; exit 3; }; POD_SESSION=ni_al_prod_pod_04 ;;
  05) [ "$CHUNK_ID" = 10 ] || [ "$CHUNK_ID" = 03 ] || { echo 'ERROR: POD 05 owns only chunks 10 and 03' >&2; exit 3; }; POD_SESSION=ni_al_prod_pod_05 ;;
  '') ;;
  *) echo 'ERROR: invalid POD_ID' >&2; exit 3 ;;
esac
ACTUAL_SESSION="$(tmux display-message -p '#S' 2>/dev/null || true)"
if [ -z "${TMUX:-}" ] || { [ "$ACTUAL_SESSION" != "$SESSION" ] && [ "$ACTUAL_SESSION" != "$POD_SESSION" ]; }; then
  echo "ERROR: run only inside $SESSION or authorized $POD_SESSION" >&2; exit 3
fi
MANIFEST="$ROOT/configs/production_chunks/chunk_${CHUNK_ID}_manifest.csv"
CHECKPOINT="$ROOT/configs/production_chunks/chunk_${CHUNK_ID}_checkpoint.txt"
LOCAL_MANIFEST="/tmp/ni_al_chunk_${CHUNK_ID}_manifest_$$.csv"
CHUNK_DIR="$ROOT/data/expansion_026_100/production_gpu/chunk_$CHUNK_ID"
LOCK="$CHUNK_DIR/.chunk_lock"
[ -f "$MANIFEST" ] || { echo "ERROR: missing $MANIFEST" >&2; exit 4; }
MANIFEST_SHA256="$(sha256sum "$MANIFEST"|awk '{print $1}')"
cp "$MANIFEST" "$LOCAL_MANIFEST"
[ "$(sha256sum "$LOCAL_MANIFEST"|awk '{print $1}')" = "$MANIFEST_SHA256" ] || { echo 'ERROR: local manifest snapshot mismatch' >&2; exit 4; }
[ "$(sha256sum "$QE"|awk '{print $1}')" = "$QH" ] || { echo 'ERROR: QE hash mismatch' >&2; exit 20; }
[ "$(sha256sum "$PD/Al.pbe-n-kjpaw_psl.1.0.0.UPF"|awk '{print $1}')" = "$AH" ] || { echo 'ERROR: Al pseudo hash mismatch' >&2; exit 21; }
[ "$(sha256sum "$PD/ni_pbe_v1.4.uspp.F.UPF"|awk '{print $1}')" = "$NH" ] || { echo 'ERROR: Ni pseudo hash mismatch' >&2; exit 22; }
export PATH="$NVROOT/compilers/bin:$PATH" NVHPC_CUDA_HOME="$NVROOT/cuda/12.9"
export LD_LIBRARY_PATH="$NVROOT/compilers/lib:$NVROOT/cuda/12.9/lib64:$NVROOT/math_libs/12.9/lib64:${LD_LIBRARY_PATH:-}"
export CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=8 OMP_PROC_BIND=close OMP_PLACES=cores
mkdir -p "$CHUNK_DIR"
if ! mkdir "$LOCK" 2>/dev/null; then echo "ERROR: persistent lock exists: $LOCK; inspect/adopt, never duplicate" >&2; exit 5; fi
printf 'hostname=%s\npid=%s\nsession=%s\nstarted=%s\n' "$(hostname)" "$$" "$SESSION" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$LOCK/owner.txt"
cleanup(){ rm -f "$LOCAL_MANIFEST" "$LOCK/owner.txt" 2>/dev/null || true; rmdir "$LOCK" 2>/dev/null || true; }
trap cleanup EXIT
[ -f "$CHUNK_DIR/chunk_start_utc.txt" ] || date -u +%Y-%m-%dT%H:%M:%SZ > "$CHUNK_DIR/chunk_start_utc.txt"
current=NONE; overall=READY
val(){ local f=$1 k=$2; [ -f "$f" ] && sed -n "s/^$k=//p" "$f" | tail -1; }
update_global(){
  local state=$1 pod="${POD_ID:-standalone}" podfile="$ROOT/configs/production_chunks/pod_${POD_ID:-standalone}_status.txt" gs="$ROOT/configs/DATASET100_GPU_PRODUCTION_STATUS.txt" lock="$ROOT/configs/production_chunks/.global_status.flock" total=0 failures=0 accum=0 last=NONE f ext tmp
  tmp="${podfile}.tmp.$(hostname).$$"
  {
    echo 'DATASET-100 GPU POD STATUS'; echo "Updated UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)"; echo "Pod ID: $pod"; echo "Chunk ID: chunk_$CHUNK_ID"
    echo "Current config: $current"; echo "Current state: $state"; echo "QE binary SHA256: $QH"; echo "Al pseudopotential SHA256: $AH"; echo "Ni pseudopotential SHA256: $NH"
  } > "$tmp" && mv "$tmp" "$podfile"
  exec 9>"$lock"; flock -x 9
  while IFS= read -r -d '' f; do
    if grep -q '^STATE=COMPLETE$' "$f" && grep -q '^EXIT_CODE=0$' "$f" && grep -q '^JOB_DONE=YES$' "$f" && grep -q '^SCF_CONVERGED=YES$' "$f"; then total=$((total+1)); ext=$(val "$f" EXTERNAL_SECONDS); accum=$((accum+${ext:-0})); last=$(val "$f" FINISH_UTC); fi
  done < <(find "$ROOT/data/expansion_026_100/production_gpu" -name config_complete.env -type f -print0 2>/dev/null)
  while IFS= read -r -d '' f; do grep -q '^STATE=FAILED$' "$f" && failures=$((failures+1)) || true; done < <(find "$ROOT/data/expansion_026_100/production_gpu" -name active.env -type f -print0 2>/dev/null)
  tmp="${gs}.tmp.$(hostname).$$"
  {
    echo 'DATASET-100 GPU PRODUCTION STATUS — LOCKED AGGREGATE'; echo "Updated UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)"; echo "Last reporting Pod ID: $pod"
    echo "Last reporting chunk: chunk_$CHUNK_ID"; echo "Last current config: $current"; echo "Last state: $state"; echo "Completed configs: $total/75"; echo "Failed configs: $failures"
    echo "Accumulated external wall time: $accum seconds"; echo "Last completed time: $last"; echo "Derived from per-Pod statuses and validated per-config completion records under flock."
  } > "$tmp" && mv "$tmp" "$gs"
  flock -u 9; exec 9>&-
}
render(){
  local state=$1 now total completed=0 failed=0 pending=0 cfg phase inp ih est cdir cm active st
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ); total=$(($(wc -l < "$LOCAL_MANIFEST")-1))
  while IFS=, read -r chunk cfg phase inp ih est ignored; do
    [ "$chunk" = chunk_id ] && continue; cdir="$CHUNK_DIR/$cfg"; cm="$cdir/config_complete.env"; active="$cdir/active.env"
    if [ -f "$cm" ] && grep -q '^STATE=COMPLETE$' "$cm"; then completed=$((completed+1)); elif [ -f "$active" ] && grep -q '^STATE=FAILED$' "$active"; then failed=$((failed+1)); else pending=$((pending+1)); fi
  done < "$LOCAL_MANIFEST"
  {
    echo 'DATASET-100 GPU PRODUCTION CHUNK CHECKPOINT'; echo "Chunk ID: chunk_$CHUNK_ID"; echo "Overall state: $state"; echo "Current config: $current"
    echo "Completed configs: $completed"; echo "Pending configs: $pending"; echo "Failed configs: $failed"
    echo "Start timestamp: $(tr -d '\n' < "$CHUNK_DIR/chunk_start_utc.txt")"; echo "Finish timestamp: $([ "$state" = COMPLETE ] && echo "$now" || echo NOT_FINISHED)"
    echo "QE executable: $QE"; echo "QE binary SHA256: $QH"; echo "Al pseudopotential SHA256: $AH"; echo "Ni pseudopotential SHA256: $NH"
    echo 'Topology: MPI ranks=1; OpenMP threads=8; QE pools=1; OMP_PROC_BIND=close; OMP_PLACES=cores'; echo "Chunk output path: $CHUNK_DIR"; echo; echo 'CONFIG STATES'
    while IFS=, read -r chunk cfg phase inp ih est ignored; do
      [ "$chunk" = chunk_id ] && continue; cdir="$CHUNK_DIR/$cfg"; cm="$cdir/config_complete.env"; active="$cdir/active.env"; st=PENDING; [ -f "$active" ] && st=$(val "$active" STATE); [ -f "$cm" ] && st=COMPLETE
      echo "$cfg | phase=$phase | state=${st:-PENDING} | canonical_input=$inp | input_sha256=$ih | output=$cdir | JOB_DONE=$(val "$cm" JOB_DONE || echo PENDING) | SCF=$(val "$cm" SCF_CONVERGED || echo PENDING) | QE_WALL=$(val "$cm" QE_WALL || echo PENDING) | GPU=$(val "$cm" GPU_UTIL || echo PENDING)"
    done < "$LOCAL_MANIFEST"
  } > "$CHECKPOINT.tmp" && mv "$CHECKPOINT.tmp" "$CHECKPOINT"
  update_global "$state"
  timeout 15 sync "$CHECKPOINT" "$ROOT/configs/production_chunks/pod_${POD_ID:-standalone}_status.txt" "$ROOT/configs/DATASET100_GPU_PRODUCTION_STATUS.txt" || echo "WARNING: checkpoint sync acknowledgement timed out" >&2
}
render READY
while IFS=, read -r chunk cfg phase inp ih est ignored; do
  [ "$chunk" = chunk_id ] && continue
  cdir="$CHUNK_DIR/$cfg"; cm="$cdir/config_complete.env"; mkdir -p "$cdir"
  actual=$(sha256sum "$inp"|awk '{print $1}'); [ "$actual" = "$ih" ] || { current=$cfg; render FAILED_INPUT_HASH; echo "ERROR: input hash mismatch $cfg" >&2; exit 30; }
  if [ -f "$cm" ]; then
    if grep -q '^STATE=COMPLETE$' "$cm" && grep -q '^EXIT_CODE=0$' "$cm" && grep -q '^JOB_DONE=YES$' "$cm" && grep -q '^SCF_CONVERGED=YES$' "$cm" && [ "$(val "$cm" INPUT_SHA256)" = "$ih" ] && grep -q 'JOB DONE' "$(val "$cm" OUTPUT_PATH)"; then continue; fi
    current=$cfg; render FAILED_INVALID_COMPLETE; echo "ERROR: invalid prior COMPLETE record for $cfg; manual review required" >&2; exit 31
  fi
  if pgrep -x pw.x >/dev/null; then current=$cfg; render FAILED_OTHER_PW_ACTIVE; echo 'ERROR: another pw.x is active on this Pod' >&2; exit 32; fi
  current=$cfg; n=1; while [ -e "$cdir/attempt_$(printf '%03d' "$n")" ]; do n=$((n+1)); done; adir="$cdir/attempt_$(printf '%03d' "$n")"; mkdir -p "$adir/tmp"
  execin="$adir/execution.in"; sed -e "s|prefix = .*|prefix = 'prod_c${CHUNK_ID}_${cfg}',|" -e "s|pseudo_dir = .*|pseudo_dir = '$PD',|" -e "s|outdir = .*|outdir = '$adir/tmp',|" "$inp" > "$execin"
  launch="env CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=8 OMP_PROC_BIND=close OMP_PLACES=cores $QE -in $execin"
  printf 'STATE=PRE-LAUNCH\nCONFIG_ID=%s\nPHASE=%s\nINPUT_SHA256=%s\nEXECUTION_INPUT_SHA256=%s\nATTEMPT_DIR=%s\nOUTPUT_PATH=%s\nMONITOR_PATH=%s\nLAUNCH_COMMAND=%s\nMPI_RANKS=1\nOPENMP_THREADS=8\nQE_POOLS=1\nOMP_PROC_BIND=close\nOMP_PLACES=cores\n' "$cfg" "$phase" "$ih" "$(sha256sum "$execin"|awk '{print $1}')" "$adir" "$adir/qe.out" "$adir/nvidia_smi.csv" "$launch" > "$cdir/active.env"
  render PRE-LAUNCH
  s=$(date +%s); su=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  nvidia-smi --query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,power.draw,clocks.sm --format=csv -l 1 > "$adir/nvidia_smi.csv" 2> "$adir/nvidia_smi.err" & mon=$!
  "$QE" -in "$execin" > "$adir/qe.out" 2> "$adir/qe.err" & pid=$!
  printf 'STATE=RUNNING\nSTART_UTC=%s\nQE_PID=%s\nMONITOR_PID=%s\n' "$su" "$pid" "$mon" >> "$cdir/active.env"; render RUNNING
  set +e; wait "$pid"; rc=$?; set -e
  e=$(date +%s); eu=$(date -u +%Y-%m-%dT%H:%M:%SZ); kill "$mon" 2>/dev/null || true; wait "$mon" 2>/dev/null || true
  job=NO; conv=NO; grep -q 'JOB DONE' "$adir/qe.out" && job=YES; grep -q 'convergence has been achieved' "$adir/qe.out" && conv=YES
  wall=$(grep 'PWSCF.*WALL' "$adir/qe.out"|tail -1|tr -s ' ')
  met=$(awk -F, 'NR>1{g=$2+0;mm=$4+0;p=$5+0;n++;sg+=g;if(g>0){na++;sa+=g};if(g>mg)mg=g;if(mm>mxm)mxm=mm;sp+=p;if(p>mp)mp=p}END{printf "%.1f%%/%.1f%%/%.0f%%|%.0f_MiB|%.1f/%.1f_W",n?sg/n:0,na?sa/na:0,mg,mxm,n?sp/n:0,mp}' "$adir/nvidia_smi.csv" 2>/dev/null || echo 'MONITOR_FAILED|MONITOR_FAILED|MONITOR_FAILED')
  IFS='|' read -r util mem power <<< "$met"
  printf 'STATE=VALIDATING\nFINISH_UTC=%s\nEXIT_CODE=%s\nEXTERNAL_SECONDS=%s\nJOB_DONE=%s\nSCF_CONVERGED=%s\nQE_WALL=%s\nGPU_UTIL=%s\nGPU_MEMORY_PEAK=%s\nGPU_POWER=%s\nOUTPUT_SHA256=%s\n' "$eu" "$rc" "$((e-s))" "$job" "$conv" "$wall" "$util" "$mem" "$power" "$(sha256sum "$adir/qe.out"|awk '{print $1}')" >> "$cdir/active.env"; render VALIDATING
  if [ "$rc" -ne 0 ] || [ "$job" != YES ] || [ "$conv" != YES ] || [ -z "$wall" ]; then printf 'STATE=FAILED\n' >> "$cdir/active.env"; render FAILED; echo "ERROR: scientifically invalid QE result for $cfg" >&2; exit 40; fi
  cp "$cdir/active.env" "$cm"; printf 'STATE=COMPLETE\nSAFE_TO_REUSE=YES\n' >> "$cm"; printf 'STATE=COMPLETE\n' >> "$cdir/active.env"; render CONFIG_COMPLETE
done < "$LOCAL_MANIFEST"
current=NONE; date -u +%Y-%m-%dT%H:%M:%SZ > "$CHUNK_DIR/chunk_finish_utc.txt"; render COMPLETE
