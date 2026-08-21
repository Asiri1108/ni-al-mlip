#!/usr/bin/env python3
"""Generate 10 standalone, ready-to-run pod DFT scripts for the round300 batch.

Reads configs/ROUND300_POD_ASSIGNMENT.csv (the time-balanced LPT assignment
from scripts/assign_round300_pods.py) and data/al3ni_remediation_v1/
round300_manifest.csv (for each config's canonical QE input path), and
emits scripts/run_round300_pod01.sh .. run_round300_pod10.sh -- each a
self-contained file, generated programmatically (not hand-typed) so pod
membership is guaranteed to match the assignment CSV exactly.

Each script follows the exact established convention from
run_round3_pod01.sh: SHA256-pinned QE binary/pseudopotentials verified
before running, must execute inside its own named tmux session, writes a
live status file, per-config DONE_MARKER, protection assertions. Uses
distinct tmux session names, status file names, and a distinct production
directory from round3/round4's pods, so nothing here can collide with or
overwrite prior rounds' records.

This script only WRITES the 10 files. It does not run, launch, or tmux
anything.
"""

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path("/workspace/ni_al")
ASSIGNMENT_CSV = ROOT / "configs/ROUND300_POD_ASSIGNMENT.csv"
MANIFEST_CSV = ROOT / "data/al3ni_remediation_v1/round300_manifest.csv"
N_PODS = 10

TEMPLATE = """#!/usr/bin/env bash
# Round-300 production DFT, pod{pod_num:02d} execution session: {n_configs} configs
# (config_ids listed below), run sequentially on a single GPU. Generated
# programmatically by scripts/generate_round300_pod_scripts.py from
# configs/ROUND300_POD_ASSIGNMENT.csv -- do not hand-edit the CONFIGS array;
# regenerate from the assignment CSV instead. Does NOT touch cfg109/cfg110,
# or any round1/round2/round3/round4 production tree. Status is written to
# configs/ROUND300_POD_{pod_num:02d}_STATUS.txt only.
set -uo pipefail

ROOT=/workspace/ni_al
PROD="$ROOT/data/al3ni_remediation_v1/round300_production_dft/pod{pod_num:02d}"
STATUS="$ROOT/configs/ROUND300_POD_{pod_num:02d}_STATUS.txt"
SESSION=ni_al_round300_pod{pod_num:02d}

QE="$ROOT/tools/qe_gpu/builds/sm_89_autoconf/PW/src/pw.x"
QE_SHA=66b7ea9f173b006854fc9e27dc9982c332dad295384803d612da7dad3edc7f8e
PSEUDO_DIR="$ROOT/tools/qe_pseudos"
AL_PSEUDO="$PSEUDO_DIR/Al.pbe-n-kjpaw_psl.1.0.0.UPF"
NI_PSEUDO="$PSEUDO_DIR/ni_pbe_v1.4.uspp.F.UPF"
AL_SHA=fd7b78921e6d0939095b681c328732668eaefd1dee6882fdbc03be463550cc97
NI_SHA=f76b86ce60cde3d83dfcc8df79ba05478db573d158289f1b226919442d977d25

# config_id:canonical_qe_input_path, in ROUND300_POD_ASSIGNMENT.csv order
# (LPT time-balanced, pod {pod_num}). Estimated total: {est_minutes:.1f} min.
CONFIGS=(
{configs_block}
)

NVROOT=/workspace/ni_al/tools/qe_gpu/nvhpc/Linux_x86_64/26.5
export NVHPC_CUDA_HOME="$NVROOT/cuda/12.9"
export PATH="$NVROOT/compilers/bin:$NVHPC_CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$NVROOT/compilers/lib:$NVHPC_CUDA_HOME/lib64:$NVROOT/math_libs/12.9/lib64${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"
export CUDA_VISIBLE_DEVICES=0
export OMP_NUM_THREADS=8
export OMP_PROC_BIND=close
export OMP_PLACES=cores

utc() {{ date -u +%Y-%m-%dT%H:%M:%SZ; }}
sha() {{ sha256sum "$1" | awk '{{print $1}}'; }}
die() {{ printf 'FATAL: %s\\n' "$*"; exit 2; }}

STATE_STR="INIT"
declare -A CFG_STATE
for entry in "${{CONFIGS[@]}}"; do CFG_STATE["${{entry%%:*}}"]="PENDING"; done

render_status() {{
  local tmp="$STATUS.tmp.$$"
  {{
    echo 'ROUND300 POD{pod_num:02d} PRODUCTION DFT STATUS'
    echo
    echo "Updated UTC: $(utc)"
    echo "State: $STATE_STR"
    echo "tmux session: $SESSION"
    echo "Production root: $PROD"
    echo "Source: configs/ROUND300_POD_ASSIGNMENT.csv (pod_number {pod_num} rows only)"
    echo "QE binary: $QE"
    echo "QE binary SHA256: $QE_SHA"
    echo
    echo 'PER-CONFIG TECHNICAL STATUS'
    for entry in "${{CONFIGS[@]}}"; do
      cid="${{entry%%:*}}"
      printf '%s | %s\\n' "$cid" "${{CFG_STATE[$cid]}}"
    done
    echo
    echo 'PROTECTION ASSERTIONS'
    echo 'Other round300 pods modified: NO'
    echo 'round1/round2/round3/round4 production trees modified: NO'
    echo 'cfg109/cfg110 sealed confirmation data touched: NO'
    if [[ "$STATE_STR" == COMPLETE ]]; then
      echo
      echo 'FINAL ACQUISITION AUDIT'
      echo "TOTAL EXPECTED: ${{#CONFIGS[@]}}"
      echo "COMPLETED: ${{#CONFIGS[@]}}"
      echo 'FAILED: 0'
    fi
  }} > "$tmp"
  mv "$tmp" "$STATUS"
}}

[[ "$(tmux display-message -p '#S' 2>/dev/null || true)" == "$SESSION" ]] || die "runner must execute inside tmux session $SESSION"
[[ -x "$QE" ]] || die "QE binary missing or not executable"
[[ "$(sha "$QE")" == "$QE_SHA" ]] || die "QE binary SHA256 mismatch"
[[ "$(sha "$AL_PSEUDO")" == "$AL_SHA" ]] || die "Al pseudopotential SHA256 mismatch"
[[ "$(sha "$NI_PSEUDO")" == "$NI_SHA" ]] || die "Ni pseudopotential SHA256 mismatch"

mkdir -p "$PROD"
STATE_STR="RUNNING"
render_status
echo "[$(utc)] Round300 pod{pod_num:02d} batch starting. ${{#CONFIGS[@]}} configs, sequential (single GPU)."

for entry in "${{CONFIGS[@]}}"; do
  CID="${{entry%%:*}}"
  CANONICAL="${{entry#*:}}"
  ATTEMPT="$PROD/$CID/attempt_001"
  SCRATCH="$ATTEMPT/tmp"
  EXECUTION_INPUT="$ATTEMPT/execution.in"
  PREFIX="r300pod{pod_num:02d}_${{CID}}_a001"

  [[ -f "$CANONICAL" ]] || die "canonical QE input missing: $CID ($CANONICAL)"
  mkdir -p "$SCRATCH"

  CFG_STATE["$CID"]="RUNNING"
  render_status
  echo "[$(utc)] START $CID"

  sed -e "s|^[[:space:]]*prefix[[:space:]]*=.*|  prefix = '$PREFIX',|" \\
      -e "s|^[[:space:]]*pseudo_dir[[:space:]]*=.*|  pseudo_dir = '$PSEUDO_DIR',|" \\
      -e "s|^[[:space:]]*outdir[[:space:]]*=.*|  outdir = '$SCRATCH',|" \\
      "$CANONICAL" > "$EXECUTION_INPUT"

  {{
    echo "CONFIG_ID=$CID"
    echo "PURPOSE=round300_production_dft_pod{pod_num:02d}"
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
  }} > "$ATTEMPT/execution_metadata.env"

  set +e
  "$QE" -in "$EXECUTION_INPUT" > "$ATTEMPT/qe.out" 2> "$ATTEMPT/qe.err"
  rc=$?
  set -e

  end=$(utc)
  output="$ATTEMPT/qe.out"
  job_done=NO; scf=NO; gpu_active=NO
  [[ $rc -eq 0 ]] && grep -q 'JOB DONE\\.' "$output" && job_done=YES
  grep -q 'convergence has been achieved' "$output" && scf=YES
  grep -q 'GPU acceleration is ACTIVE' "$output" && gpu_active=YES

  {{
    echo "END_TIMESTAMP=$end"
    echo "EXIT_CODE=$rc"
    echo "JOB_DONE=$job_done"
    echo "SCF_CONVERGED=$scf"
    echo "GPU_ACCELERATION_ACTIVE=$gpu_active"
    echo "OUTPUT_SHA256=$(sha "$output" 2>/dev/null || echo NONE)"
  }} >> "$ATTEMPT/execution_metadata.env"

  cfg_status="COMPLETE"
  [[ $rc -eq 0 && "$job_done" == YES && "$scf" == YES ]] || cfg_status="FAILED"
  CFG_STATE["$CID"]="$cfg_status"
  echo "$cfg_status" > "$ATTEMPT/DONE_MARKER.txt"

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
echo "[$(utc)] Round300 pod{pod_num:02d} batch complete. All ${{#CONFIGS[@]}} configs PASS."
"""


def main():
    assignment_rows = list(csv.DictReader(ASSIGNMENT_CSV.open(newline="")))
    manifest_rows = list(csv.DictReader(MANIFEST_CSV.open(newline="")))
    qe_input_by_id = {r["config_id"]: r["qe_input_path"] for r in manifest_rows}

    if len(assignment_rows) != 82:
        raise RuntimeError(f"expected 82 assigned candidates, found {len(assignment_rows)}")

    by_pod = defaultdict(list)
    for r in assignment_rows:
        by_pod[int(r["pod_number"])].append(r)

    if set(by_pod) != set(range(1, N_PODS + 1)):
        raise RuntimeError(f"expected pods 1-{N_PODS}, found {sorted(by_pod)}")

    total_written = 0
    for pod_num in range(1, N_PODS + 1):
        rows = by_pod[pod_num]
        missing = [r["config_id"] for r in rows if r["config_id"] not in qe_input_by_id]
        if missing:
            raise RuntimeError(f"pod {pod_num}: config(s) missing from manifest: {missing}")

        configs_block_lines = []
        for r in rows:
            path = qe_input_by_id[r["config_id"]]
            if not Path(path).is_file():
                raise RuntimeError(f"pod {pod_num}: QE input file does not exist on disk: {path}")
            configs_block_lines.append(f'  {r["config_id"]}:{path}')
        configs_block = "\n".join(configs_block_lines)
        est_minutes = sum(float(r["estimated_seconds"]) for r in rows) / 60

        script = TEMPLATE.format(
            pod_num=pod_num, n_configs=len(rows), configs_block=configs_block, est_minutes=est_minutes,
        )
        out_path = ROOT / f"scripts/run_round300_pod{pod_num:02d}.sh"
        out_path.write_text(script)
        out_path.chmod(0o755)
        total_written += 1
        print(f"wrote {out_path} ({len(rows)} configs, {est_minutes:.1f} min estimated)")

    print(f"\n{total_written}/{N_PODS} pod scripts written. Not launched -- no tmux session started.")


if __name__ == "__main__":
    main()
