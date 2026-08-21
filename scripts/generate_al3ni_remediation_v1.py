#!/usr/bin/env python3
"""Generate and freeze the approved 10-point Al3Ni remediation design. No DFT."""
from __future__ import annotations
import csv, hashlib, json, math, os, tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from ase.io import read, write

R=Path('/workspace/ni_al'); BASE=R/'data/al3ni_remediation_v1'; STRUCT=BASE/'structures'; QE=BASE/'qe_inputs'
MAN=BASE/'remediation_manifest.csv'; SPLIT=BASE/'split_membership_manifest.csv'; SEEDS=BASE/'rattle_seed_manifest.csv'; HASHES=BASE/'artifact_sha256.csv'; PROV=BASE/'PROVENANCE.txt'; META=BASE/'generation_metadata.json'; STATUS=R/'configs/AL3NI_REMEDIATION_DESIGN_STATUS.txt'
PILOT=R/'data/processed/ni_al_pilot_dft_25.extxyz'; DATA100=R/'data/datasets/ni_al_dataset100_dft.extxyz'; BLIND=R/'data/datasets/ni_al_dataset100_blind_holdout_manifest.csv'
PSEUDO=R/'pseudo'; PSEUDO_NAMES=['Al.pbe-n-kjpaw_psl.1.0.0.UPF','ni_pbe_v1.4.uspp.F.UPF']
# Exact user-approved order and split. Seed = 20261000 + numeric ID, matching established convention.
DESIGN=[
 ('cfg101_Al3Ni_iso_compression','TRAIN','iso_compression','isotropic',-0.04,0.0,None),
 ('cfg102_Al3Ni_iso_compression','TRAIN','iso_compression','isotropic',-0.02,0.0,None),
 ('cfg103_Al3Ni_iso_expansion','TRAIN','iso_expansion','isotropic',+0.02,0.0,None),
 ('cfg104_Al3Ni_volume_rattle_compression','TRAIN','volume_rattle_compression','isotropic',-0.02,0.015,20261104),
 ('cfg105_Al3Ni_volume_rattle_expansion','TRAIN','volume_rattle_expansion','isotropic',+0.02,0.015,20261105),
 ('cfg106_Al3Ni_rattle_020','TRAIN','rattle_020','none',0.0,0.020,20261106),
 ('cfg107_Al3Ni_volume_rattle_compression','VALIDATION','volume_rattle_compression','isotropic',-0.04,0.015,20261107),
 ('cfg108_Al3Ni_rattle_030','VALIDATION','rattle_030','none',0.0,0.030,20261108),
 ('cfg109_Al3Ni_iso_expansion','CONFIRMATION_HOLDOUT','iso_expansion','isotropic',+0.04,0.0,None),
 ('cfg110_Al3Ni_volume_rattle_expansion','CONFIRMATION_HOLDOUT','volume_rattle_expansion','isotropic',+0.04,0.015,20261110),
]
def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def geom_hash(a):
 h=hashlib.sha256(); h.update(np.asarray(a.numbers,np.int64).tobytes()); h.update(np.asarray(a.positions,np.float64).tobytes()); h.update(np.asarray(a.cell.array,np.float64).tobytes()); h.update(np.asarray(a.pbc,np.bool_).tobytes()); return h.hexdigest()
def qe_text(a,cid):
 lines=['&CONTROL',"  calculation = 'scf',",f"  prefix = '{cid}',",f"  pseudo_dir = '{PSEUDO}',",f"  outdir = '{BASE/'qe_outputs'/cid/'tmp'}',","  tprnfor = .true.,","  tstress = .true.,","  disk_io = 'low',",'/','&SYSTEM','  ibrav = 0,',f'  nat = {len(a)},','  ntyp = 2,','  ecutwfc = 90.0,','  ecutrho = 720.0,',"  occupations = 'smearing',","  smearing = 'mv',",'  degauss = 0.010,','/','&ELECTRONS','  conv_thr = 1.0d-10,','  electron_maxstep = 200,','  mixing_beta = 0.30,',"  diagonalization = 'david',",'/','ATOMIC_SPECIES',f'Al 26.9815385 {PSEUDO_NAMES[0]}',f'Ni 58.6934 {PSEUDO_NAMES[1]}','CELL_PARAMETERS angstrom']
 lines += [' '.join(f'{x:.12f}' for x in row) for row in a.cell.array]; lines += ['ATOMIC_POSITIONS crystal']; lines += [f"{s} "+' '.join(f'{x:.12f}' for x in q) for s,q in zip(a.get_chemical_symbols(),a.get_scaled_positions(wrap=True))]; lines += ['K_POINTS automatic','10 8 8 0 0 0','']; return '\n'.join(lines)
def write_new(path,data):
 if path.exists(): raise FileExistsError(f'refusing overwrite: {path}')
 path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
def main():
 if BASE.exists() and any(BASE.rglob('*')): raise FileExistsError(f'remediation directory is not empty: {BASE}')
 # Freeze immutable upstream identities before generation.
 upstream={str(PILOT):sha(PILOT),str(DATA100):sha(DATA100),str(BLIND):sha(BLIND),str(R/'scripts/generate_dataset100_expansion.py'):sha(R/'scripts/generate_dataset100_expansion.py')}
 allp=read(PILOT,':'); ref=next(a for a in allp if a.info.get('config_id')=='Al3Ni_relaxed').copy(); ref.calc=None
 dataset=read(DATA100,':'); dataset_ids={a.info['config_id'] for a in dataset}; blind_ids={r['config_id'] for r in csv.DictReader(BLIND.open())}; blind_frames=[a for a in dataset if a.info['config_id'] in blind_ids]
 if any(cid in dataset_ids for cid,*_ in DESIGN): raise RuntimeError('ID collision with Dataset-100')
 existing_geom={geom_hash(a) for a in dataset}; blind_geom={geom_hash(a) for a in blind_frames}
 for p in (STRUCT,QE,BASE/'qe_outputs'): p.mkdir(parents=True,exist_ok=True)
 rows=[]; objects=[]; seed_rows=[]
 ref_cell=ref.cell.array.copy(); ref_scaled=ref.get_scaled_positions(wrap=True)
 for cid,split,family,stype,strain,rattle,seed in DESIGN:
  a=ref.copy(); F=np.eye(3)
  if stype=='isotropic': F*=1+strain
  elif stype!='none': raise RuntimeError(stype)
  a.set_cell(a.cell.array@F.T,scale_atoms=True); strained_positions=a.positions.copy(); displacement=np.zeros_like(a.positions)
  if rattle:
   rng=np.random.default_rng(seed); displacement=rng.normal(0,rattle,(len(a),3)); displacement-=displacement.mean(axis=0); a.positions+=displacement; a.wrap()
  a.info={'config_id':cid,'phase':'Al3Ni','config_family':family,'config_type':family,'target_role':split,'strain_type':stype,'strain_value':float(strain),'rattle_sigma_A':float(rattle),'random_seed':int(seed) if seed is not None else 'NONE','source_structure':'Al3Ni_relaxed','confirmation_sealed':'YES' if split=='CONFIRMATION_HOLDOUT' else 'NO'}
  sp=STRUCT/f'{cid}.extxyz'; qp=QE/f'{cid}.in'; write(sp,a,format='extxyz'); qp.write_text(qe_text(a,cid))
  reread=read(sp); gh=geom_hash(reread); applied=np.diag(reread.cell.array@np.linalg.inv(ref_cell))-1
  # Minimum-image realized displacement from strained fractional reference.
  expected_scaled=ref_scaled; delta=reread.get_scaled_positions(wrap=True)-expected_scaled; delta-=np.round(delta); realized=delta@reread.cell.array
  component_rms=float(np.sqrt(np.mean(realized**2))); component_std=float(np.std(realized)); vector_rms=float(np.sqrt(np.mean(np.sum(realized**2,axis=1)))); max_disp=float(np.max(np.linalg.norm(realized,axis=1))); com=np.mean(realized,axis=0)
  row={'config_id':cid,'phase':'Al3Ni','split':split,'config_family':family,'config_type':family,'strain_type':stype,'requested_strain':format(strain,'.17g'),'actual_strain_x':format(applied[0],'.17g'),'actual_strain_y':format(applied[1],'.17g'),'actual_strain_z':format(applied[2],'.17g'),'requested_rattle_sigma_A':format(rattle,'.17g'),'random_seed':str(seed) if seed is not None else 'NONE','realized_component_rms_A':format(component_rms,'.17g'),'realized_component_std_A':format(component_std,'.17g'),'realized_vector_rms_A':format(vector_rms,'.17g'),'realized_max_displacement_A':format(max_disp,'.17g'),'realized_com_displacement_norm_A':format(float(np.linalg.norm(com)),'.17g'),'natoms':'16','source_structure':'Al3Ni_relaxed','structure_path':str(sp),'structure_sha256':sha(sp),'geometry_sha256':gh,'qe_input_path':str(qp),'qe_input_sha256':sha(qp),'qe_status':'READY_NOT_RUN','dft_status':'NOT_STARTED','confirmation_label_policy':'SEALED_AFTER_DFT' if split=='CONFIRMATION_HOLDOUT' else 'DEVELOPMENT'}
  rows.append(row); objects.append((row,reread))
  if seed is not None: seed_rows.append({'config_id':cid,'split':split,'random_seed':seed,'generator':'numpy.random.default_rng(seed).normal(0,sigma,(natoms,3)); subtract component-wise mean; add Cartesian displacement; wrap','requested_sigma_A':format(rattle,'.17g'),'seed_independent':'YES'})
 # Strict validation.
 errors=[]; geoms=[r['geometry_sha256'] for r in rows]
 if Counter(r['split'] for r in rows)!=Counter({'TRAIN':6,'VALIDATION':2,'CONFIRMATION_HOLDOUT':2}): errors.append('role counts')
 if len(set(geoms))!=10: errors.append('internal geometry duplicate')
 if set(geoms)&existing_geom: errors.append('exact overlap Dataset-100')
 if set(geoms)&blind_geom: errors.append('exact overlap blind')
 if len({r['random_seed'] for r in seed_rows})!=len(seed_rows): errors.append('seed reuse within remediation')
 existing_seeds={r['random_seed'] for r in csv.DictReader((R/'data/expansion_026_100/manifests/configs_026_100_design.csv').open())}
 if {str(r['random_seed']) for r in seed_rows}&existing_seeds: errors.append('seed reuse Dataset-100')
 for row,a in objects:
  if len(a)!=16 or Counter(a.symbols)!=Counter({'Al':12,'Ni':4}) or not a.pbc.all(): errors.append(row['config_id']+': composition/PBC')
  if a.get_volume()<=0 or not np.isfinite(a.positions).all(): errors.append(row['config_id']+': geometry')
  vals=a.get_all_distances(mic=True)[np.triu_indices(len(a),1)]; row['minimum_distance_A']=format(float(vals.min()),'.17g')
  if vals.min()<1.8: errors.append(row['config_id']+': close contact')
  txt=Path(row['qe_input_path']).read_text()
  for token in ['ecutwfc = 90.0','ecutrho = 720.0',"smearing = 'mv'",'degauss = 0.010','conv_thr = 1.0d-10','electron_maxstep = 200','mixing_beta = 0.30',"diagonalization = 'david'",*PSEUDO_NAMES,'10 8 8 0 0 0']:
   if token not in txt: errors.append(row['config_id']+': QE '+token)
 if errors: raise RuntimeError('\n'.join(errors))
 # Publish manifests only after validation.
 with MAN.open('w',newline='') as h: w=csv.DictWriter(h,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
 split_fields=['split','config_id','phase','config_family','requested_strain','requested_rattle_sigma_A','random_seed','structure_sha256','geometry_sha256','qe_input_sha256','label_access_policy']
 split_rows=[]
 for r in rows: split_rows.append({k:(('NEVER_TRAIN_VALIDATE_SELECT; SEALED_UNTIL_FINAL_MODEL_FROZEN' if r['split']=='CONFIRMATION_HOLDOUT' else ('TRAIN_DEVELOPMENT_ONLY' if r['split']=='TRAIN' else 'VALIDATION_SELECTION_ONLY')) if k=='label_access_policy' else r[k]) for k in split_fields})
 with SPLIT.open('w',newline='') as h: w=csv.DictWriter(h,fieldnames=split_fields); w.writeheader(); w.writerows(split_rows)
 with SEEDS.open('w',newline='') as h: w=csv.DictWriter(h,fieldnames=list(seed_rows[0])); w.writeheader(); w.writerows(seed_rows)
 artifacts=[]
 for r in rows:
  for kind,key in [('structure','structure_path'),('qe_input','qe_input_path')]:
   p=Path(r[key]); artifacts.append({'config_id':r['config_id'],'artifact_type':kind,'path':str(p),'size_bytes':p.stat().st_size,'sha256':sha(p)})
 with HASHES.open('w',newline='') as h: w=csv.DictWriter(h,fieldnames=list(artifacts[0])); w.writeheader(); w.writerows(artifacts)
 metadata={'generated_utc':datetime.now(timezone.utc).isoformat(),'generator':str(Path(__file__).resolve()),'generator_sha256':sha(Path(__file__).resolve()),'methodology_source':str(R/'scripts/generate_dataset100_expansion.py'),'upstream_sha256':upstream,'canonical_reference':{'dataset':str(PILOT),'config_id':'Al3Ni_relaxed','index':24,'geometry_sha256':geom_hash(ref)},'id_policy':'sequential post-Dataset-100 cfg101-cfg110; verified unused before assignment','seed_policy':'rattle-only; 20261000 + numeric config ID; independent of Dataset-100 seeds','split_counts':dict(Counter(r['split'] for r in rows)),'dft_started':False,'qe_binary_rebuilt':False,'blind_modified':False,'near_equivalent_controls_note':'cfg102/cfg103 are regenerated +/-0.02 controls and scientifically near historical Pilot Al3Ni_iso_m02/p02, but are not exact geometry-hash duplicates due canonical-reference serialization differences.'}
 META.write_text(json.dumps(metadata,indent=2)+'\n')
 prov=f'''AL3NI REMEDIATION V1 PROVENANCE

Generated UTC: {metadata['generated_utc']}
Canonical reference: {PILOT} frame Al3Ni_relaxed (index 24)
Reference geometry SHA256: {metadata['canonical_reference']['geometry_sha256']}
Generation implementation: established Dataset-100 deformation and Cartesian rattle method.
QE methodology: QE 7.6 PBE static SCF; ecutwfc 90 Ry; ecutrho 720 Ry; MV smearing/degauss 0.010 Ry; conv_thr 1e-10; electron_maxstep 200; mixing_beta 0.30; david; Al3Ni k-grid 10x8x8; unchanged pseudopotential filenames.

Frozen split: TRAIN=6; VALIDATION=2; CONFIRMATION_HOLDOUT=2.
Confirmation IDs: cfg109_Al3Ni_iso_expansion; cfg110_Al3Ni_volume_rattle_expansion.
Confirmation labels, once computed, must be sealed and may never be used for training, validation, early stopping, objective/hyperparameter/checkpoint selection, or model ranking. They remain inaccessible until the final candidate is frozen.

No DFT, retraining, QE rebuild, or LAMMPS run occurred during design generation.
Dataset-100 and its blind holdout were read only and remain unchanged.
'''; PROV.write_text(prov)
 # Status comes last and freezes hashes of all governing manifests.
 ids={s:[r['config_id'] for r in rows if r['split']==s] for s in ['TRAIN','VALIDATION','CONFIRMATION_HOLDOUT']}
 status=['AL3NI REMEDIATION V1 DESIGN STATUS','',f"Generated UTC: {metadata['generated_utc']}",f'Root: {BASE}','State: FROZEN BEFORE DFT','', 'COUNTS','TRAIN = 6','VALIDATION = 2','CONFIRMATION = 2','TOTAL = 10','', 'EXACT MEMBERSHIP']
 for s in ids: status += [s+':',*[f'  {x}' for x in ids[s]]]
 status += ['','FROZEN GOVERNING ARTIFACTS',f'Manifest: {MAN}',f'Manifest SHA256: {sha(MAN)}',f'Split manifest: {SPLIT}',f'Split manifest SHA256: {sha(SPLIT)}',f'Seed manifest: {SEEDS}',f'Seed manifest SHA256: {sha(SEEDS)}',f'Artifact hash manifest: {HASHES}',f'Artifact hash manifest SHA256: {sha(HASHES)}',f'Generation metadata: {META}',f'Generation metadata SHA256: {sha(META)}',f'Provenance: {PROV}',f'Provenance SHA256: {sha(PROV)}','', 'FINAL AUDIT','NEW CONFIGS: 10/10','All Al3Ni (Al12Ni4, 16 atoms): YES','DUPLICATE STRUCTURES: 0','OVERLAP WITH DATASET-100: 0','OVERLAP WITH CURRENT BLIND STRUCTURES: 0','CURRENT DATASET-100 BLIND HOLDOUT MODIFIED: NO','ALL CONFIG IDS FROZEN: YES','ALL RATTLE SEEDS FROZEN: YES','ALL STRUCTURE HASHES FROZEN: YES','ALL QE INPUT HASHES FROZEN: YES','ALL SPLIT MEMBERSHIP FROZEN: YES','Confirmation label-access policy frozen: YES','DFT STARTED: NO','RETRAINING STARTED: NO','LAMMPS STARTED: NO','', 'NOTE','cfg102/cfg103 are scientifically near the historical Pilot +/-0.02 isotropic controls, but exact geometry hashes do not overlap; this is recorded in generation_metadata.json.','', 'AL3NI REMEDIATION DESIGN FROZEN','NEW CONFIGS: 10','TRAIN: 6','VALIDATION: 2','CONFIRMATION HOLDOUT: 2','DFT STARTED: NO','CURRENT BLIND HOLDOUT MODIFIED: NO','READY FOR TARGETED DFT ACQUISITION','']
 STATUS.write_text('\n'.join(status)); os.sync(); print('\n'.join(status[-8:]))
if __name__=='__main__': main()
