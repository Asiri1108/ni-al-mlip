#!/usr/bin/env python3
"""One-shot frozen TEST-5 and BLIND-15 evaluation; contains no training code."""
import csv, hashlib, json, math, os, platform, subprocess, time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import torch
from ase.io import read
from mace.calculators import MACECalculator

R=Path('/workspace/ni_al'); OUT=R/'results/dataset100_final_evaluation_v1'; LOG=R/'logs/dataset100_final_evaluation_v1'
DATA=R/'data/datasets/ni_al_dataset100_dft.extxyz'; TRAIN=R/'data/datasets/ni_al_dataset100_train_manifest.csv'
TEST=R/'data/datasets/ni_al_dataset100_test_manifest.csv'; BLIND=R/'data/datasets/ni_al_dataset100_blind_holdout_manifest.csv'
NEW=R/'models/dataset100_matpes_pbe_lora_v1/dataset100_matpes_pbe_lora_v1.model'; OLD=R/'models/pilot25_matpes_pbe_lora_v1/pilot25_matpes_pbe_lora_v1.model'
STATUS=R/'configs/DATASET100_FINAL_EVALUATION_STATUS.txt'; GPA=160.21766208
EXPECTED={DATA:'12fabd203b91e31e9a602bbaa3a2a3f14341e6fa366b128903099e196b59a3aa',TRAIN:'87e3b96ebddc95beb910665985821a4df58919351d6f58df7cda8a355ac2047d',TEST:'88af05d9bc39658683d940d45fad96422e214d2710af3783c1cdb69f8483e2e3',BLIND:'e7814eda578b09694da546eebc60f3398c7ca85f86763d9b514c0de056fb75bf',NEW:'745f02582e604fed390d567198e4e4dfa783c71a61d749c58419659bc784a0d9',OLD:'94d8d4dade7322077d6d2343820a32678eafd7499d1762ee7f180b4ce4fc7719'}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def refs(a): return float(a.get_potential_energy()),np.asarray(a.get_forces(),float),np.asarray(a.get_stress(),float)
def stats(x):
 x=np.asarray(x,float); return float(np.mean(np.abs(x))),float(np.sqrt(np.mean(x*x))),float(np.max(np.abs(x)))
def predict(path, structures):
 calc=MACECalculator(model_paths=str(path),device='cuda',default_dtype='float64'); out={}
 for key,a in structures.items():
  w=a.copy(); w.calc=calc; out[key]=(float(w.get_potential_energy()),np.asarray(w.get_forces(),float),np.asarray(w.get_stress(),float))
 del calc; torch.cuda.empty_cache(); return out
def aggregate(rows, model):
 energy=[r[f'{model}_energy_error_mev_atom'] for r in rows]; rel=[r[f'{model}_relative_energy_error_mev_atom'] for r in rows]
 force=np.concatenate([np.asarray(r[f'_{model}_force_error']) for r in rows]); stress=np.concatenate([np.asarray(r[f'_{model}_stress_error_gpa']) for r in rows])
 e=stats(energy); re=stats(rel); f=stats(force); s=stats(stress)
 return {'energy_mae_mev_atom':e[0],'energy_rmse_mev_atom':e[1],'energy_max_abs_mev_atom':e[2],'relative_energy_mae_mev_atom':re[0],'relative_energy_rmse_mev_atom':re[1],'relative_energy_max_abs_mev_atom':re[2],'force_mae_evA':f[0],'force_rmse_evA':f[1],'force_max_component_error_evA':f[2],'stress_mae_gpa':s[0],'stress_rmse_gpa':s[1],'stress_max_component_error_gpa':s[2]}
def main():
 start=time.time(); OUT.mkdir(parents=True,exist_ok=True); LOG.mkdir(parents=True,exist_ok=True)
 gate=(R/'configs/DATASET100_MACE_TRAINING_STATUS.txt').read_text()
 if 'MODEL FROZEN: YES' not in gate or 'TEST USED FOR TRAINING: NO' not in gate or 'BLIND HOLDOUT USED FOR TRAINING: NO' not in gate: raise RuntimeError('frozen training gate failed')
 for p,h in EXPECTED.items():
  if sha(p)!=h: raise RuntimeError(f'identity changed: {p}')
 frames=read(DATA,':'); by={a.info['config_id']:a for a in frames}
 memberships={s:list(csv.DictReader(p.open())) for s,p in [('TEST',TEST),('BLIND_HOLDOUT',BLIND)]}
 if len(memberships['TEST'])!=5 or len(memberships['BLIND_HOLDOUT'])!=15: raise RuntimeError('evaluation membership count')
 eval_ids={r['config_id'] for rows in memberships.values() for r in rows}; train_rows=list(csv.DictReader(TRAIN.open()))
 if eval_ids & {r['config_id'] for r in train_rows}: raise RuntimeError('evaluation/train leakage')
 relaxed={r['phase']:by[r['config_id']] for r in train_rows if r['dataset_origin']=='Pilot-25' and r['config_type']=='relaxed'}
 if set(relaxed)!={'AlNi','Al3Ni','Al3Ni2','Al3Ni5','AlNi3'}: raise RuntimeError('phase relaxed references incomplete')
 structures={f'eval:{cid}':by[cid] for cid in eval_ids}; structures.update({f'relaxed:{p}':a for p,a in relaxed.items()})
 print('Evaluating previous frozen Pilot-25 model',flush=True); old=predict(OLD,structures)
 print('Evaluating frozen Dataset-100 model',flush=True); new=predict(NEW,structures)
 rows=[]
 for split,members in memberships.items():
  for m in members:
   cid=m['config_id']; a=by[cid]; de,df,ds=refs(a); phase=a.info['phase']; dre=(de-refs(relaxed[phase])[0])/len(a)*1000
   row={'split':split,'config_id':cid,'phase':phase,'perturbation_family':m['config_family'],'natoms':len(a),'dft_energy_eV':de,'dft_energy_per_atom_eV':de/len(a),'dft_relative_energy_mev_atom':dre,'source_record':a.info['source_record']}
   for label,pred in [('pilot25',old),('dataset100',new)]:
    pe,pf,ps=pred[f'eval:{cid}']; pre=(pe-pred[f'relaxed:{phase}'][0])/len(a)*1000
    ee=(pe-de)/len(a)*1000; fe=pf-df; se=(ps-ds)*GPA
    fs=stats(fe); ss=stats(se)
    row.update({f'{label}_energy_eV':pe,f'{label}_energy_error_mev_atom':ee,f'{label}_relative_energy_mev_atom':pre,f'{label}_relative_energy_error_mev_atom':pre-dre,f'{label}_force_mae_evA':fs[0],f'{label}_force_rmse_evA':fs[1],f'{label}_force_max_component_error_evA':fs[2],f'{label}_stress_mae_gpa':ss[0],f'{label}_stress_rmse_gpa':ss[1],f'{label}_stress_max_component_error_gpa':ss[2],f'_{label}_force_error':fe.reshape(-1),f'_{label}_stress_error_gpa':se.reshape(-1)})
   rows.append(row)
 public=[{k:v for k,v in r.items() if not k.startswith('_')} for r in rows]
 with (OUT/'dataset100_final_per_config.csv').open('w',newline='') as f: w=csv.DictWriter(f,fieldnames=list(public[0])); w.writeheader(); w.writerows(public)
 groups=[]
 definitions=[('overall','TEST+BLIND',rows),('split','TEST',[r for r in rows if r['split']=='TEST']),('split','BLIND_HOLDOUT',[r for r in rows if r['split']=='BLIND_HOLDOUT'])]
 for split in ['TEST','BLIND_HOLDOUT']:
  sr=[r for r in rows if r['split']==split]
  for p in sorted({r['phase'] for r in sr}): definitions.append(('phase',f'{split}:{p}',[r for r in sr if r['phase']==p]))
  for fam in sorted({r['perturbation_family'] for r in sr}): definitions.append(('perturbation_family',f'{split}:{fam}',[r for r in sr if r['perturbation_family']==fam]))
 keys=['energy_mae_mev_atom','energy_rmse_mev_atom','energy_max_abs_mev_atom','relative_energy_mae_mev_atom','relative_energy_rmse_mev_atom','relative_energy_max_abs_mev_atom','force_mae_evA','force_rmse_evA','force_max_component_error_evA','stress_mae_gpa','stress_rmse_gpa','stress_max_component_error_gpa']
 regression_rows=[]
 for gtype,gname,subset in definitions:
  if not subset: continue
  o=aggregate(subset,'pilot25'); n=aggregate(subset,'dataset100'); rec={'group_type':gtype,'group':gname,'count':len(subset)}
  for k in keys:
   rec['pilot25_'+k]=o[k]; rec['dataset100_'+k]=n[k]; rec['improvement_percent_'+k]=100*(o[k]-n[k])/o[k] if o[k]!=0 else (0 if n[k]==0 else -math.inf)
   if n[k]>o[k]+max(1e-14,abs(o[k])*1e-12): regression_rows.append({'group_type':gtype,'group':gname,'count':len(subset),'metric':k,'pilot25':o[k],'dataset100':n[k],'change_percent':100*(n[k]-o[k])/o[k] if o[k] else math.inf})
  groups.append(rec)
 with (OUT/'dataset100_final_summary.csv').open('w',newline='') as f: w=csv.DictWriter(f,fieldnames=list(groups[0])); w.writeheader(); w.writerows(groups)
 with (OUT/'dataset100_final_regressions.csv').open('w',newline='') as f:
  fields=['group_type','group','count','metric','pilot25','dataset100','change_percent']; w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(regression_rows)
 overall=next(x for x in groups if x['group']=='TEST+BLIND'); test=next(x for x in groups if x['group']=='TEST'); blind=next(x for x in groups if x['group']=='BLIND_HOLDOUT')
 primary=['energy_mae_mev_atom','energy_rmse_mev_atom','relative_energy_mae_mev_atom','relative_energy_rmse_mev_atom','force_mae_evA','force_rmse_evA','stress_mae_gpa','stress_rmse_gpa']
 material_overall=[k for k in primary if overall['dataset100_'+k]>overall['pilot25_'+k]*1.02]
 finite=all(np.isfinite(v) for r in public for k,v in r.items() if isinstance(v,(float,np.floating)))
 verdict='PASS' if finite and not material_overall else 'REVIEW REQUIRED'
 payload={'models':{'pilot25':str(OLD),'pilot25_sha256':sha(OLD),'dataset100':str(NEW),'dataset100_sha256':sha(NEW)},'splits':{'TEST':len(memberships['TEST']),'BLIND_HOLDOUT':len(memberships['BLIND_HOLDOUT'])},'overall':overall,'test':test,'blind_holdout':blind,'regressions':regression_rows,'material_overall_regressions':material_overall,'verdict':verdict}
 (OUT/'dataset100_final_metrics.json').write_text(json.dumps(payload,indent=2,default=float))
 def metric_lines(title,x):
  return [title,f"  Energy MAE/RMSE/max: {x['dataset100_energy_mae_mev_atom']:.6g} / {x['dataset100_energy_rmse_mev_atom']:.6g} / {x['dataset100_energy_max_abs_mev_atom']:.6g} meV/atom",f"  Relative-energy MAE/RMSE/max: {x['dataset100_relative_energy_mae_mev_atom']:.6g} / {x['dataset100_relative_energy_rmse_mev_atom']:.6g} / {x['dataset100_relative_energy_max_abs_mev_atom']:.6g} meV/atom",f"  Force MAE/RMSE/max component: {x['dataset100_force_mae_evA']:.6g} / {x['dataset100_force_rmse_evA']:.6g} / {x['dataset100_force_max_component_error_evA']:.6g} eV/A",f"  Stress MAE/RMSE/max component: {x['dataset100_stress_mae_gpa']:.6g} / {x['dataset100_stress_rmse_gpa']:.6g} / {x['dataset100_stress_max_component_error_gpa']:.6g} GPa"]
 status=['Ni-Al DATASET-100 FINAL FROZEN MODEL EVALUATION','',f'Generated UTC: {datetime.now(timezone.utc).isoformat()}',f'Frozen Dataset-100 model: {NEW}',f'SHA256: {sha(NEW)}',f'Previous frozen Pilot-25 model: {OLD}',f'SHA256: {sha(OLD)}','',f'TEST evaluated: 5','BLIND HOLDOUT evaluated: 15','Retraining after evaluation: NO','LAMMPS launched: NO','']
 status+=metric_lines('TEST-5 — DATASET-100 MODEL',test)+['']+metric_lines('BLIND-HOLDOUT-15 — DATASET-100 MODEL',blind)+['']+metric_lines('COMBINED INDEPENDENT-20 — DATASET-100 MODEL',overall)
 status+=['','COMPARISON AND REGRESSIONS',f'Per-metric subgroup regressions versus Pilot-25: {len(regression_rows)}',f'Material (>2%) overall primary-metric regressions: {len(material_overall)}']
 status += ([f"  {r['group']} | {r['metric']} | Pilot={r['pilot25']:.8g} New={r['dataset100']:.8g} change={r['change_percent']:.3f}%" for r in regression_rows] if regression_rows else ['  NONE'])
 status+=['','ARTIFACTS',f'Per-config CSV: {OUT/"dataset100_final_per_config.csv"}',f'Summary CSV: {OUT/"dataset100_final_summary.csv"}',f'Regressions CSV: {OUT/"dataset100_final_regressions.csv"}',f'Metrics JSON: {OUT/"dataset100_final_metrics.json"}',f'Wall time: {time.time()-start:.3f} s','',f'DATASET-100 MODEL VALIDATION: {verdict}','']
 STATUS.write_text('\n'.join(status)); subprocess.run(['sync'],check=True); print(json.dumps({'verdict':verdict,'overall':overall,'test':test,'blind':blind,'regression_count':len(regression_rows)},indent=2,default=float))
if __name__=='__main__': main()
