#!/usr/bin/env python3
"""Write Dataset-100 provenance, benchmark, distribution, and sync reports."""
from __future__ import annotations
import csv, hashlib, socket
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path('/workspace/ni_al'); BASE=ROOT/'data/expansion_026_100'
MAN=BASE/'manifests/configs_026_100_design.csv'

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def stamp(p):
 s=p.stat(); return f"{p}|{s.st_size}|{datetime.fromtimestamp(s.st_mtime,timezone.utc).isoformat()}|{sha(p)}"

rows=list(csv.DictReader(MAN.open()))
now=datetime.now(timezone.utc).isoformat()

# Frozen Pilot artifact manifest: deliberate scientific/core result set.
artifacts=[
 ROOT/'data/processed/ni_al_pilot_dft_25.extxyz',
 ROOT/'data/datasets/ni_al_pilot_train_15.extxyz',ROOT/'data/datasets/ni_al_pilot_val_5.extxyz',ROOT/'data/datasets/ni_al_pilot_test_5.extxyz',
 ROOT/'models/pilot25_matpes_pbe_lora_v1/pilot25_matpes_pbe_lora_v1.model',
 ROOT/'models/pilot25_matpes_pbe_lora_v1/pilot25_matpes_pbe_lora_v1_compiled.model',
 ROOT/'checkpoints/pilot25_matpes_pbe_lora_v1/pilot25_matpes_pbe_lora_v1_run-20260811_epoch-88.pt',
 ROOT/'configs/pilot25_matpes_pbe_lora_v1.yaml',ROOT/'configs/pilot25_matpes_pbe_lora_v1_PROVENANCE.txt',
 ROOT/'configs/PILOT25_LORA_TRAINING_STATUS.txt',ROOT/'configs/PILOT25_TEST_EVALUATION_STATUS.txt',
 ROOT/'results/pilot25_test_evaluation_v1/pilot25_test_per_config.csv',ROOT/'results/pilot25_test_evaluation_v1/pilot25_test_summary.csv',
 ROOT/'results/pilot25_test_evaluation_v1/pilot25_test_force_before_after.png',ROOT/'results/pilot25_test_evaluation_v1/pilot25_test_stress_before_after.png',
 ROOT/'results/pilot25_test_evaluation_v1/pilot25_test_relative_energy_before_after.png',ROOT/'results/pilot25_test_evaluation_v1/pilot25_test_metric_improvement.png',
]
missing=[str(p) for p in artifacts if not p.is_file()]
pilot=["PILOT-25 FINAL ARTIFACTS MANIFEST",f"Generated UTC: {now}",f"Hostname: {socket.gethostname()}","Policy: immutable scientific record; do not alter, delete, or overwrite listed artifacts.","Pilot TEST-5 status: historical diagnostic test; inspected once; not the Dataset-100 blind publication holdout.","", "PATH|SIZE_BYTES|MTIME_UTC|SHA256"]
pilot += [stamp(p) for p in artifacts if p.is_file()]
pilot += ["",f"Missing expected artifacts: {len(missing)}"]+missing
(ROOT/'configs/PILOT25_FINAL_ARTIFACTS_MANIFEST.txt').write_text('\n'.join(pilot)+'\n')

# Exact historical CPU identities and reference observables.
cpu_cases=[
('small phase','AlNi','iso_m02','-382.87390925','0.00075144 0.00075144 0.00075144 0 0 0','110.54 110.54 110.54 0 0 0'),
('heavy Al3Ni phase','Al3Ni','iso_m02','-1847.59812698','0.00052102 0.00053576 0.00055385 0 0 0','76.65 78.81 81.47 0 0 0'),
('spin-relevant phase','AlNi3','iso_m02','-1069.46024652','0.00086473 0.00086447 0.00086447 0 0 0','127.21 127.17 127.17 0 0 0')]
cpu=["CPU-GPU EQUIVALENCE PLAN",f"Generated UTC: {now}","STATUS: PREPARED, NOT EXECUTED","Purpose: gate GPU Quantum ESPRESSO production by reproducing three completed CPU references with unchanged input methodology.","Required QE: 7.6 GPU build; PBE; identical pseudopotential bytes; ecutwfc=90 Ry; ecutrho=720 Ry; MV smearing; degauss=0.010 Ry; identical k meshes, spin, and convergence settings.","Acceptance: compare total energy, every Cartesian force component, and all six stress components; investigate any difference exceeding 1e-6 Ry total energy, 1e-5 Ry/bohr force, or 1e-7 Ry/bohr^3 stress before production.",""]
for purpose,phase,family,e,stress,kbar in cpu_cases:
 d=ROOT/f'data/raw_dft/diverse_pilot_01/{phase}/{family}'; inp=d/f'{phase}_{family}.in'; out=d/f'{phase}_{family}.out'
 cpu += [f"CASE: {purpose}",f"Phase/config: {phase}_{family}",f"Input: {inp}",f"Input SHA256: {sha(inp)}",f"CPU output: {out}",f"CPU output SHA256: {sha(out)}",f"CPU total energy: {e} Ry",f"CPU QE-printed stress order xx yy zz yz xz xy: {stress} Ry/bohr^3",f"CPU QE-printed diagonal stress: {kbar} kbar",f"Forces: use every 'atom ... force =' row in the immutable CPU output above (not a rounded transcription).",""]
cpu += ["Execution gate:","1. Stage and hash the exact established Al/Ni pseudopotentials.","2. Run these unchanged inputs on CPU and GPU builds with documented MPI/OpenMP settings.","3. Parse outputs using one script and compare tolerances above.","4. Approve GPU production only after all three cases pass.","DFT runs started by this plan: 0"]
(BASE/'gpu_benchmark/CPU_GPU_EQUIVALENCE_PLAN.txt').write_text('\n'.join(cpu)+'\n')

bench={ph:next(r for r in rows if r['phase']==ph and r['target_role']=='TRAIN_CANDIDATE') for ph in ['AlNi','Al3Ni2','AlNi3','Al3Ni5','Al3Ni']}
timing=["GPU TIMING BENCHMARK PLAN",f"Generated UTC: {now}","STATUS: PREPARED, NOT EXECUTED","Run only after CPU-GPU equivalence passes. Use the production GPU-QE executable and identical production settings.","Measure elapsed wall time and record GPU model, QE build, MPI ranks, OpenMP threads, convergence iterations, and success status.",""]
for ph,r in bench.items(): timing += [f"{ph}: {r['config_id']}",f"  input: {BASE/'qe_inputs'/ (r['config_id']+'.in')}"]
timing += ["","Assignment rule: estimate each configuration cost by phase benchmark time, then use measured relative device speeds to balance predicted total wall time. Do not split by equal configuration count.","Benchmark DFT runs started: 0"]
(BASE/'gpu_benchmark/GPU_TIMING_BENCHMARK_PLAN.txt').write_text('\n'.join(timing)+'\n')

with (BASE/'team_assignments/TEAM_DISTRIBUTION_TEMPLATE.csv').open('w',newline='') as f:
 fields=['machine_id','gpu_model','benchmark_AlNi_s','benchmark_Al3Ni2_s','benchmark_AlNi3_s','benchmark_Al3Ni5_s','benchmark_Al3Ni_s','relative_speed','assigned_config_ids','predicted_total_wall_time_s','actual_total_wall_time_s','status']
 w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
 for i in range(1,5): w.writerow({'machine_id':f'GPU-{i:02d}','status':'AWAITING_BENCHMARK'})

sync_plan=f"""VS CODE / GIT SYNCHRONIZATION PLAN
Generated UTC: {now}
Local RunPod project: {ROOT}
Git metadata in /workspace/ni_al: NOT PRESENT; destination repository path/remote must be supplied during the later transfer step.

COPY TO CANONICAL REPOSITORY
Generation and validation code:
- scripts/generate_dataset100_expansion.py
- scripts/prepare_dataset100_expansion_reports.py
- scripts/validate_and_split_pilot25.py
- scripts/qe_to_extxyz.py
Evaluation/training reproducibility:
- scripts/evaluate_pilot25_test_v1.py
- configs/pilot25_matpes_pbe_lora_v1.yaml
- configs/pilot25_matpes_pbe_lora_v1_PROVENANCE.txt
Manifests and plans:
- data/expansion_026_100/manifests/configs_026_100_design.csv
- data/expansion_026_100/validation/STRUCTURE_VALIDATION_REPORT.txt
- data/expansion_026_100/gpu_benchmark/*.txt
- data/expansion_026_100/team_assignments/TEAM_DISTRIBUTION_TEMPLATE.csv
Status/provenance:
- configs/PILOT25_FINAL_ARTIFACTS_MANIFEST.txt
- configs/PILOT25_LORA_TRAINING_STATUS.txt
- configs/PILOT25_TEST_EVALUATION_STATUS.txt
- configs/DATASET100_EXPANSION_PREPARATION.txt
- configs/VSCODE_SYNC_PLAN.txt
- results/pilot25_test_evaluation_v1/*.csv

COPY OR ARCHIVE OUTSIDE NORMAL GIT AS SCIENTIFIC DATA
- generated EXTXYZ structures and QE input files (75 each), subject to repository data policy
- canonical Pilot EXTXYZ datasets and result plots if repository policy permits

DO NOT COMMIT AS NORMAL GIT FILES
- envs/, downloads/caches, checkpoints/, large *.model binaries, QE scratch/output directories, credentials or authentication state

TRANSFER SAFETY
Verify destination branch and repository first; preserve paths; compare SHA256 after transfer; never overwrite a divergent canonical file silently. No external transfer was performed in this task.
"""
(ROOT/'configs/VSCODE_SYNC_PLAN.txt').write_text(sync_plan)

phase=Counter(r['phase'] for r in rows); role=Counter(r['target_role'] for r in rows); fam=Counter(r['config_family'] for r in rows)
report=f"""DATASET-100 EXPANSION PREPARATION
Generated UTC: {now}
Hostname: {socket.gethostname()}

PILOT-25 FROZEN STATE
The canonical 25 configurations, 15/5/5 split, epoch-88-selected LoRA model, training provenance/status, and one-time TEST evaluation are preserved and hashed in configs/PILOT25_FINAL_ARTIFACTS_MANIFEST.txt. Pilot TEST-5 remains a historical diagnostic test, not the Dataset-100 final holdout. No Pilot artifact was changed.

SCIENTIFIC RATIONALE
Pilot fine-tuning clearly improved held-out energy, force, and stress errors. Expansion emphasizes Al3Ni force/relative-energy coverage, Al3Ni5 stress, and controlled volume/shear response across all phases. Defects, surfaces, and large supercells are deferred until bulk/strain coverage is mature.

EXACT PHASE ALLOCATION
Al3Ni=19; Al3Ni5=17; Al3Ni2=14; AlNi=13; AlNi3=12; total=75.
Al3Ni receives the largest allocation because its force behavior remains the principal Pilot weakness. Al3Ni5 receives the second-largest allocation and additional strain/shear structures because its stress error remains important.

TARGET ROLES
TRAIN_CANDIDATE=50; VALIDATION=10; BLIND_HOLDOUT=15.
The 15 new blind-holdout identities are frozen in the design manifest before Dataset-100 training and must never be used for optimization, early stopping, hyperparameter tuning, or data-selection decisions. Validation and blind roles use distinct perturbation parameters/families to reduce near-duplicate leakage.

CONFIGURATION FAMILY ALLOCATION (stable manifest labels)
{'; '.join(f'{k}={v}' for k,v in sorted(fam.items()))}
These labels span isotropic compression/expansion, uniaxial/biaxial/orthorhombic strain, signed shear, independent deterministic rattles, volume+rattle, and shear+rattle combinations. Random seeds are unique and recorded.

PREPARATION RESULTS
Design manifest rows: 75 (configurations 026-100)
Generated structures: 75
Validated structures: 75/75
QE static-SCF inputs: 75/75, prepared and NOT RUN
DFT runs started: 0
Minimum interatomic distance: 2.281594 A
Exact duplicate structures: 0
Raw DFT modified: NO

QE METHODOLOGY PRESERVED
QE 7.6; PBE; ecutwfc=90 Ry; ecutrho=720 Ry; Marzari-Vanderbilt smearing; degauss=0.010 Ry; conv_thr=1e-10; electron_maxstep=200; mixing_beta=0.30; david diagonalization; phase-specific k meshes; AlNi3 nspin=2 and Ni starting magnetization=0.60. Inputs reference Al.pbe-n-kjpaw_psl.1.0.0.UPF and ni_pbe_v1.4.uspp.F.UPF.

EXECUTION GATES / REVIEW REQUIRED
1. Exact pseudopotential files were not found under /workspace. Before any QE execution, stage the established files at /workspace/ni_al/pseudo and verify their hashes/identity; do not substitute.
2. Build/validate GPU QE 7.6, then pass the three-case CPU-GPU equivalence plan.
3. Benchmark one representative new configuration per phase.
4. Finalize four-GPU assignments only from measured wall times; TEAM_DISTRIBUTION_TEMPLATE.csv intentionally contains no production assignment.
5. Preserve BLIND_HOLDOUT identities and access discipline before future training.

CPU-GPU EQUIVALENCE PLAN
Prepared for completed CPU references AlNi_iso_m02, Al3Ni_iso_m02, and spin-relevant AlNi3_iso_m02. Exact input/output paths and hashes plus reference energy/stress are recorded. Not executed.

GPU TIMING PLAN
Prepared one TRAIN_CANDIDATE per phase. Workload balancing will use measured per-phase time and relative GPU speed, not equal configuration counts. Not executed.

VS CODE SYNCHRONIZATION
Plan written to configs/VSCODE_SYNC_PLAN.txt. No external transfer performed. Scripts/manifests/configs/status reports belong in source control; environments, caches, checkpoints, large models, and QE scratch do not.

COMPLETION STATUS
Scientifically consistent preparation complete. QE input text is ready, but production execution remains gated on exact pseudopotential staging and CPU-GPU equivalence. No DFT, MACE training, or LAMMPS was launched.
"""
(ROOT/'configs/DATASET100_EXPANSION_PREPARATION.txt').write_text(report)
print('REPORTS_WRITTEN',len(rows),len(artifacts)-len(missing),'MISSING_PILOT',len(missing))
