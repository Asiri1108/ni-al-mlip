#!/usr/bin/env python3
"""Freeze and report a successful Dataset-100 MACE run without holdout access."""
import hashlib, os, platform, re, subprocess
from datetime import datetime, timezone
from pathlib import Path
R=Path('/workspace/ni_al'); NAME='dataset100_matpes_pbe_lora_v1'
LOG=R/f'logs/{NAME}/training_console.log'; STATUS=R/'configs/DATASET100_MACE_TRAINING_STATUS.txt'
MODEL=R/f'models/{NAME}/{NAME}.model'; COMPILED=R/f'models/{NAME}/{NAME}_compiled.model'
CONFIG=R/f'configs/{NAME}.yaml'; TRAIN=R/'data/datasets/ni_al_dataset100_train_65.extxyz'; VALID=R/'data/datasets/ni_al_dataset100_validation_15.extxyz'
BASE=R/'models/pilot25_matpes_pbe_lora_v1/pilot25_matpes_pbe_lora_v1.model'; FOUNDATION=R/f'runs/{NAME}/downloads/mace/MACEmatpespbeomatftmodel'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
text=LOG.read_text(errors='replace')
if 'Training complete' not in text or re.search(r'Traceback|CUDA out of memory|\bnan\b|\binf\b',text,re.I): raise RuntimeError('training log is not clean/complete')
if not MODEL.is_file() or not COMPILED.is_file(): raise RuntimeError('selected model outputs missing')
epochs=re.findall(r'Epoch (\d+):.*?loss=([0-9.eE+-]+).*?RMSE_E_per_atom=\s*([0-9.]+).*?RMSE_F=\s*([0-9.]+).*?RMSE_stress=\s*([0-9.]+)',text)
loads=re.findall(r'Loading checkpoint: (.+?epoch-(\d+)\.pt)',text)
if not epochs or not loads: raise RuntimeError('epoch/selected checkpoint evidence missing')
selected_path,selected_epoch=loads[-1]; selected=next((x for x in epochs if x[0]==selected_epoch),None)
if selected is None: raise RuntimeError('selected epoch metrics missing')
start=(R/f'logs/{NAME}/start_epoch_seconds.txt').read_text().strip(); end=str(int(datetime.now(timezone.utc).timestamp())); wall=int(end)-int(start)
gpu=(R/f'logs/{NAME}/gpu_info.csv').read_text().strip(); gpu_log=R/f'logs/{NAME}/gpu_monitor.csv'
peak='not_recorded'
if gpu_log.exists():
 vals=[]
 for line in gpu_log.read_text(errors='ignore').splitlines():
  m=re.search(r',\s*(\d+)\s*$',line)
  if m: vals.append(int(m.group(1)))
 if vals: peak=f'{max(vals)} MiB'
for p in (MODEL,COMPILED,Path(selected_path)): os.chmod(p,0o444)
status=f'''Ni-Al DATASET-100 MACE TRAINING STATUS

Timestamp UTC: {datetime.now(timezone.utc).isoformat()}
Run: {NAME}
Training completion status: COMPLETE

DATA AND LEAKAGE CONTROL
TRAIN: {TRAIN}
TRAIN SHA256: {sha(TRAIN)}
TRAIN configurations/labels: 65/65
VALIDATION: {VALID}
VALIDATION SHA256: {sha(VALID)}
VALIDATION configurations/labels: 15/15
Frozen TRAIN manifest SHA256: 87e3b96ebddc95beb910665985821a4df58919351d6f58df7cda8a355ac2047d
Frozen VALIDATION manifest SHA256: 87fc9debed6a93a8b8b823d188ff43444148a65c855e173c31da264c621bd42f
Frozen TEST manifest SHA256: 88af05d9bc39658683d940d45fad96422e214d2710af3783c1cdb69f8483e2e3
Frozen BLIND HOLDOUT manifest SHA256: e7814eda578b09694da546eebc60f3398c7ca85f86763d9b514c0de056fb75bf
TEST passed to MACE: NO
BLIND HOLDOUT passed to MACE: NO
MACE tests: []

METHOD
Foundation: MACE-MATPES-PBE-0 / mace-matpes-pbe-0
Foundation SHA256: {sha(FOUNDATION)}
Pilot-25 baseline model preserved: {BASE}
Pilot-25 baseline SHA256: {sha(BASE)}
LoRA: true; rank=4; alpha=1.0; multihead replay=false
Loss: WeightedEnergyForcesStressLoss
Weights: energy=1.0; forces=10.0; stress=1.0
Units: eV, Angstrom, eV/Angstrom, eV/Angstrom^3
Precision/device: float64 / CUDA
Optimizer: Adam; lr=0.001; weight_decay=0.0; AMSGrad=true
Batch sizes: train=2; validation=2
Epoch policy: max=100; patience=20; eval_interval=1
EMA: true; decay=0.995; clip_grad=10.0
E0s: estimated from approved TRAIN-65 only
Random seed: 20260811

COMMAND AND SOFTWARE
Config: {CONFIG}
Config SHA256: {sha(CONFIG)}
Exact command: env XDG_CACHE_HOME=/workspace/ni_al/runs/{NAME}/downloads TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 /workspace/ni_al/envs/mace-py312-cu128/bin/mace_run_train --config={CONFIG}
Python: {platform.python_version()}
MACE: 0.3.16
PyTorch: 2.8.0+cu128; CUDA 12.8
ASE: 3.29.0
GPU: {gpu}
Peak monitored GPU memory: {peak}
tmux session: ni_al_dataset100_mace_training
Wall time: {wall} seconds

TRAINING AND SELECTION
Last epoch: {epochs[-1][0]}
Selected validation checkpoint epoch: {selected_epoch}
Selected checkpoint: {selected_path}
Selected validation loss: {selected[1]}
Selected validation energy RMSE: {selected[2]} meV/atom
Selected validation force RMSE: {selected[3]} meV/Angstrom
Selected validation stress RMSE: {selected[4]} meV/Angstrom^3
Checkpoint count: {len(list((R/f'checkpoints/{NAME}').glob('*')))}

FROZEN MODEL
Primary: {MODEL}
Primary SHA256: {sha(MODEL)}
Compiled: {COMPILED}
Compiled SHA256: {sha(COMPILED)}
Selected checkpoint SHA256: {sha(Path(selected_path))}
Read-only freeze applied: YES

DATASET-100 MACE TRAINING COMPLETE
MODEL FROZEN: YES
TEST USED FOR TRAINING: NO
BLIND HOLDOUT USED FOR TRAINING: NO
READY FOR FINAL EVALUATION
'''
STATUS.write_text(status); subprocess.run(['sync'],check=True); print(status.splitlines()[-5:])
