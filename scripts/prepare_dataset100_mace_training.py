#!/usr/bin/env python3
"""Materialize only frozen TRAIN/VALIDATION data and verify MACE preconditions."""

import csv, hashlib, os, shutil, tempfile
from pathlib import Path
import numpy as np
from ase.io import read, write

R=Path('/workspace/ni_al')
DATA=R/'data/datasets/ni_al_dataset100_dft.extxyz'
STATUS=R/'configs/DATASET100_SPLIT_STATUS.txt'
TRAIN_MAN=R/'data/datasets/ni_al_dataset100_train_manifest.csv'
VALID_MAN=R/'data/datasets/ni_al_dataset100_validation_manifest.csv'
TEST_MAN=R/'data/datasets/ni_al_dataset100_test_manifest.csv'
BLIND_MAN=R/'data/datasets/ni_al_dataset100_blind_holdout_manifest.csv'
TRAIN=R/'data/datasets/ni_al_dataset100_train_65.extxyz'
VALID=R/'data/datasets/ni_al_dataset100_validation_15.extxyz'
FOUNDATION_SRC=R/'runs/pilot25_matpes_pbe_lora_v1/downloads/mace/MACEmatpespbeomatftmodel'
FOUNDATION_DST=R/'runs/dataset100_matpes_pbe_lora_v1/downloads/mace/MACEmatpespbeomatftmodel'
EXPECTED={
 TRAIN_MAN:'87e3b96ebddc95beb910665985821a4df58919351d6f58df7cda8a355ac2047d',
 VALID_MAN:'87fc9debed6a93a8b8b823d188ff43444148a65c855e173c31da264c621bd42f',
 TEST_MAN:'88af05d9bc39658683d940d45fad96422e214d2710af3783c1cdb69f8483e2e3',
 BLIND_MAN:'e7814eda578b09694da546eebc60f3398c7ca85f86763d9b514c0de056fb75bf'}
FOUNDATION_SHA='e618ad582b84239905b9c3b77ce6e9ce111b0ecd1533223a1a6aac7a696b8aa0'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def publish_extxyz(path, frames):
 fd,name=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent); os.close(fd)
 tmp=Path(name)
 try:
  write(tmp,frames,format='extxyz'); data=tmp.read_bytes()
 finally:
  tmp.unlink(missing_ok=True)
 if path.exists():
  if path.read_bytes()!=data: raise RuntimeError(f'refusing divergent training input: {path}')
 else: path.write_bytes(data)

gate=STATUS.read_text()
if 'SPLITS FROZEN' not in gate or 'DATA LEAKAGE: NONE' not in gate: raise RuntimeError('split gate failed')
for p,h in EXPECTED.items():
 if sha(p)!=h: raise RuntimeError(f'frozen manifest changed: {p}')
frames=read(DATA,':'); by={a.info['config_id']:a for a in frames}
def select(manifest,count):
 rows=list(csv.DictReader(manifest.open()))
 if len(rows)!=count: raise RuntimeError(f'{manifest}: count mismatch')
 out=[]
 for row in rows:
  a=by[row['config_id']]
  if hashlib.sha256(np.asarray([a.get_potential_energy()],np.float64).tobytes()).hexdigest()!=row['energy_sha256_float64']: raise RuntimeError(row['config_id']+' energy digest')
  if hashlib.sha256(np.asarray(a.get_forces(),np.float64).tobytes()).hexdigest()!=row['forces_sha256_float64']: raise RuntimeError(row['config_id']+' force digest')
  if hashlib.sha256(np.asarray(a.get_stress(),np.float64).tobytes()).hexdigest()!=row['stress_sha256_float64']: raise RuntimeError(row['config_id']+' stress digest')
  out.append(a)
 return rows,out
tr,tf=select(TRAIN_MAN,65); vr,vf=select(VALID_MAN,15)
for forbidden in (TEST_MAN,BLIND_MAN):
 forbidden_ids={r['config_id'] for r in csv.DictReader(forbidden.open())}
 if forbidden_ids & ({r['config_id'] for r in tr}|{r['config_id'] for r in vr}): raise RuntimeError('holdout leakage')
publish_extxyz(TRAIN,tf); publish_extxyz(VALID,vf)
for path,source in ((TRAIN,tf),(VALID,vf)):
 check=read(path,':')
 if len(check)!=len(source): raise RuntimeError('training input readback count')
 for a,b in zip(source,check):
  if a.info['config_id']!=b.info['config_id'] or a.get_potential_energy()!=b.get_potential_energy() or not np.array_equal(a.get_forces(),b.get_forces()) or not np.array_equal(a.get_stress(),b.get_stress()): raise RuntimeError('training input label changed')
if sha(FOUNDATION_SRC)!=FOUNDATION_SHA: raise RuntimeError('foundation identity changed')
FOUNDATION_DST.parent.mkdir(parents=True,exist_ok=True)
if FOUNDATION_DST.exists() and sha(FOUNDATION_DST)!=FOUNDATION_SHA: raise RuntimeError('divergent foundation cache')
if not FOUNDATION_DST.exists(): shutil.copyfile(FOUNDATION_SRC,FOUNDATION_DST)
if sha(FOUNDATION_DST)!=FOUNDATION_SHA: raise RuntimeError('foundation copy failed')
print('TRAIN',len(tf),sha(TRAIN)); print('VALIDATION',len(vf),sha(VALID)); print('FOUNDATION',sha(FOUNDATION_DST)); print('TEST/BLIND EXCLUDED')
