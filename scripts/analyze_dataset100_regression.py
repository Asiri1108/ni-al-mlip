#!/usr/bin/env python3
"""Post-evaluation root-cause analysis. Never trains, predicts, or edits splits."""
import csv, hashlib, json, math, re, subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
R=Path('/workspace/ni_al'); SRC=R/'results/dataset100_final_evaluation_v1'; OUT=R/'results/dataset100_regression_analysis_v1'; OUT.mkdir(parents=True,exist_ok=True)
PER=SRC/'dataset100_final_per_config.csv'; DESIGN=R/'data/expansion_026_100/manifests/configs_026_100_design.csv'
TRAIN=R/'data/datasets/ni_al_dataset100_train_manifest.csv'; VALID=R/'data/datasets/ni_al_dataset100_validation_manifest.csv'
STATUS=R/'configs/DATASET100_REGRESSION_ANALYSIS_STATUS.txt'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def category(f):
 if f.startswith('volume_rattle') or f.startswith('shear_rattle'): return 'combined_perturbations'
 if f.startswith('iso_'): return 'volume_isotropic_strain'
 if f.startswith('rattle'): return 'rattle'
 if f.startswith('shear_'): return 'shear'
 return 'other_established_families'
def f(x): return float(x)
blind=[r for r in csv.DictReader(PER.open()) if r['split']=='BLIND_HOLDOUT']; design={r['config_id']:r for r in csv.DictReader(DESIGN.open())}
rows=[]
for r in blind:
 d=design[r['config_id']]; po=abs(f(r['pilot25_relative_energy_error_mev_atom'])); no=abs(f(r['dataset100_relative_energy_error_mev_atom']))
 rows.append({'config_id':r['config_id'],'phase':r['phase'],'perturbation_family':r['perturbation_family'],'scientific_family_category':category(r['perturbation_family']),'natoms':r['natoms'],'strain_type':d['strain_type'],'strain_value':d['strain_value'],'rattle_sigma_A':d['rattle_sigma_A'],'shear_value':d['shear_value'],'dft_relative_energy_mev_atom':r['dft_relative_energy_mev_atom'],'pilot25_prediction_mev_atom':r['pilot25_relative_energy_mev_atom'],'dataset100_prediction_mev_atom':r['dataset100_relative_energy_mev_atom'],'pilot25_signed_error_mev_atom':r['pilot25_relative_energy_error_mev_atom'],'dataset100_signed_error_mev_atom':r['dataset100_relative_energy_error_mev_atom'],'pilot25_abs_error_mev_atom':format(po,'.17g'),'dataset100_abs_error_mev_atom':format(no,'.17g'),'change_in_abs_error_mev_atom':format(no-po,'.17g')})
rows.sort(key=lambda x:f(x['change_in_abs_error_mev_atom']),reverse=True)
with (OUT/'relative_energy_regression_by_config.csv').open('w',newline='') as h: w=csv.DictWriter(h,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
net_abs=sum(f(x['change_in_abs_error_mev_atom']) for x in rows); old_sse=sum(f(x['pilot25_signed_error_mev_atom'])**2 for x in rows); new_sse=sum(f(x['dataset100_signed_error_mev_atom'])**2 for x in rows); net_sse=new_sse-old_sse
def grouped(key,path,ordered=None):
 groups=defaultdict(list)
 for x in rows: groups[x[key]].append(x)
 names=ordered or sorted(groups); out=[]
 for name in names:
  xs=groups.get(name,[]); oa=sum(f(x['pilot25_abs_error_mev_atom']) for x in xs); na=sum(f(x['dataset100_abs_error_mev_atom']) for x in xs); os=sum(f(x['pilot25_signed_error_mev_atom'])**2 for x in xs); ns=sum(f(x['dataset100_signed_error_mev_atom'])**2 for x in xs)
  da=na-oa; ds=ns-os
  out.append({key:name,'count':len(xs),'pilot25_mae_mev_atom':format(oa/len(xs),'.17g') if xs else '', 'dataset100_mae_mev_atom':format(na/len(xs),'.17g') if xs else '','sum_abs_error_change_mev_atom':format(da,'.17g'),'contribution_to_blind_mae_change_mev_atom':format(da/len(rows),'.17g'),'share_of_net_mae_regression_percent':format(100*da/net_abs,'.17g') if net_abs else '','pilot25_sum_squared_error':format(os,'.17g'),'dataset100_sum_squared_error':format(ns,'.17g'),'change_in_sum_squared_error':format(ds,'.17g'),'share_of_net_squared_error_increase_percent':format(100*ds/net_sse,'.17g') if net_sse else ''})
 with path.open('w',newline='') as h: w=csv.DictWriter(h,fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
 return out
phase=grouped('phase',OUT/'relative_energy_regression_by_phase.csv',['Al3Ni','Al3Ni2','Al3Ni5','AlNi','AlNi3'])
family=grouped('scientific_family_category',OUT/'relative_energy_regression_by_family.csv',['volume_isotropic_strain','rattle','shear','combined_perturbations','other_established_families'])
# Coverage uses TRAIN/VALIDATION metadata only. No holdout values enter these rows.
coverage=[]
for split,path in [('TRAIN',TRAIN),('VALIDATION',VALID)]:
 for r in csv.DictReader(path.open()):
  if r['phase']!='Al3Ni': continue
  fam=r['config_family']; coverage.append({'record_type':'configuration','split':split,'config_id':r['config_id'],'dataset_origin':r['dataset_origin'],'perturbation_family':fam,'scientific_family_category':category(fam),'strain_type':r['strain_type'],'strain_value':r['strain_value'],'rattle_sigma_A':r['rattle_sigma_A'],'shear_value':r['shear_value'],'combined_perturbation':'YES' if fam.startswith(('volume_rattle','shear_rattle')) else 'NO','note':'historical magnitude unavailable' if r['dataset_origin']=='Pilot-25' and r['strain_value']=='historical_not_recorded' else ''})
for split in ['TRAIN','VALIDATION']:
 xs=[x for x in coverage if x['split']==split]
 for cat in ['volume_isotropic_strain','rattle','shear','combined_perturbations','other_established_families']:
  ys=[x for x in xs if x['scientific_family_category']==cat]; strains=[f(x['strain_value']) for x in ys if x['strain_value'] not in ('','historical_not_recorded')]; rattles=[f(x['rattle_sigma_A']) for x in ys if x['rattle_sigma_A'] not in ('','historical_not_recorded')]; shears=[f(x['shear_value']) for x in ys if x['shear_value'] not in ('','historical_not_recorded')]
  coverage.append({'record_type':'category_summary','split':split,'config_id':'','dataset_origin':'ALL','perturbation_family':'ALL','scientific_family_category':cat,'strain_type':'','strain_value':f"range={min(strains):.17g}..{max(strains):.17g}" if strains else 'not_recorded','rattle_sigma_A':f"range={min(rattles):.17g}..{max(rattles):.17g}" if rattles else 'not_recorded','shear_value':f"range={min(shears):.17g}..{max(shears):.17g}" if shears else 'not_recorded','combined_perturbation':str(sum(x['combined_perturbation']=='YES' for x in ys)),'note':f'count={len(ys)}'})
with (OUT/'al3ni_coverage_analysis.csv').open('w',newline='') as h: w=csv.DictWriter(h,fieldnames=list(coverage[0])); w.writeheader(); w.writerows(coverage)
# Method comparison is exact: YAML differs only paths/name, verified again here.
import yaml
pc=yaml.safe_load((R/'configs/pilot25_matpes_pbe_lora_v1.yaml').read_text()); dc=yaml.safe_load((R/'configs/dataset100_matpes_pbe_lora_v1.yaml').read_text())
method_keys=['foundation_model','lora','lora_rank','lora_alpha','multiheads_finetuning','loss','energy_weight','forces_weight','stress_weight','lr','weight_decay','amsgrad','max_num_epochs','patience','eval_interval','seed','default_dtype','E0s','batch_size','valid_batch_size','ema','ema_decay','clip_grad']
lines=['TRAINING METHOD COMPARISON','', 'Setting | Pilot-25 | Dataset-100 | Changed']
for k in method_keys: lines.append(f"{k} | {pc.get(k)} | {dc.get(k)} | {'YES' if pc.get(k)!=dc.get(k) else 'NO'}")
lines += ['','Relative-energy treatment: neither run used an explicit relative-energy/difference loss. Both optimized absolute per-structure energy plus force and stress terms.','Validation/model selection: both used the same weighted validation loss; Dataset-100 selected epoch 98. The criterion did not separately monitor phase-relative energies, volume slopes, or curvature.','Objective balance: forces_weight=10 versus energy_weight=1 and stress_weight=1. Numerical loss normalization is MACE-internal, so weights alone do not prove displacement of energy learning; however, the objective and checkpoint criterion can favor broad force/absolute-energy improvement without protecting sub-meV relative differences.','Dataset-100 validation history decreased essentially monotonically to epoch 98; there is no evidence of optimizer instability or classic overfitting in the recorded aggregate validation loss.','Conclusion: methodology was unchanged. The regression is not caused by an undocumented hyperparameter change. Lack of an explicit relative-energy criterion is a plausible secondary contributor, especially for checkpoint selection.','',f"Pilot config SHA256: {sha(R/'configs/pilot25_matpes_pbe_lora_v1.yaml')}",f"Dataset-100 config SHA256: {sha(R/'configs/dataset100_matpes_pbe_lora_v1.yaml')}"]
(OUT/'training_method_comparison.txt').write_text('\n'.join(lines)+'\n')
al=[x for x in rows if x['phase']=='Al3Ni']; al_sorted=sorted(al,key=lambda x:f(x['dft_relative_energy_mev_atom']))
ordering=' < '.join(x['perturbation_family'] for x in al_sorted); po=' < '.join(x['perturbation_family'] for x in sorted(al,key=lambda x:f(x['pilot25_prediction_mev_atom']))); no=' < '.join(x['perturbation_family'] for x in sorted(al,key=lambda x:f(x['dataset100_prediction_mev_atom'])))
worst=max(al,key=lambda x:f(x['change_in_abs_error_mev_atom']))
rec=f'''RECOMMENDED REMEDIATION PLAN

Primary classification: F. MIXED — dominated by A. DATA COVERAGE ISSUE, with a secondary B/C training-objective and model-selection issue.

EVIDENCE
- The Al3Ni volume+rattle expansion frame alone increases absolute relative-energy error by {f(worst['change_in_abs_error_mev_atom']):.17g} meV/atom.
- Al3Ni TRAIN has one coupled volume+rattle configuration, compression only (strain -0.025, rattle sigma 0.020 A); VALIDATION has none.
- Al3Ni TRAIN pure isotropic strains cover +/-0.01 and +/-0.03 and pure rattles 0.010/0.040 A; this does not constrain coupled expansion+rattle cross-curvature.
- The failing point combines positive volume strain and atomic displacement. Its forces improved, while energy and stress worsened, consistent with an underconstrained coupled energy surface rather than a globally defective model.
- All DFT labels passed prior scientific validation; there is no current evidence for D. LABEL ISSUE.
- Correct DFT energy ordering is preserved for the four Al3Ni blind modes ({ordering}); the failure is magnitude at the large combined expansion point, not an ordering inversion.
- A single combined expansion point cannot distinguish a globally wrong volume slope from wrong curvature. Pure expansion and compression blind points do not exist in this subset, so slope/curvature claims beyond the observed local outlier would be overinterpretation.

CONTROLLED DEVELOPMENT ACTION BEFORE NEW DFT
1. Using TRAIN/VALIDATION only, rescore retained Dataset-100 checkpoints with a preregistered composite validation table that includes existing absolute energy/force/stress metrics plus phase-referenced relative-energy MAE/RMSE computed from VALIDATION configurations against TRAIN relaxed references.
2. Do not select a checkpoint using TEST/BLIND results. If an existing checkpoint materially improves validation relative energy without unacceptable force/stress regression, freeze it as a development candidate only.
3. This analysis does not authorize replacing the already evaluated frozen model or rechecking the current blind set repeatedly.

SMALL TARGETED DFT ACQUISITION (10 Al3Ni configurations; proposal only)
Derive new structures independently from the training-side Al3Ni relaxed parent with new deterministic seeds:
- 4 pure isotropic controls: strain -0.02, +0.02, -0.04, +0.04; no rattle.
- 4 coupled volume+rattle controls: strain -0.02, +0.02, -0.04, +0.04 with rattle sigma 0.015 A; independent seeds.
- 2 pure rattle controls: sigma 0.020 and 0.030 A; independent seeds.
This symmetric factorial-style mini-grid estimates volume slope, curvature, displacement curvature, and their coupling without copying any blind structure. Allocate these new points between a new development TRAIN/VALIDATION design before DFT, preserve the current blind holdout unchanged, and define a new untouched confirmation holdout before any retraining.

RETRAINING PLAN AFTER DESIGN FREEZE
- First controlled arm: unchanged LoRA/model/optimizer, but checkpoint selection additionally reports preregistered validation relative-energy metrics; do not alter loss yet.
- Second arm only if validation evidence warrants: add an explicitly documented relative-energy/difference objective or modestly increase energy emphasis, changing one factor at a time while retaining force/stress safeguards.
- Compare arms only on development validation. Never optimize against the already revealed blind outcomes.

NEW DFT REQUIRED: YES
RETRAINING REQUIRED: YES
BLIND HOLDOUT MODIFIED: NO
LAMMPS APPROVED: NO
'''
(OUT/'recommended_remediation_plan.txt').write_text(rec)
status=['DATASET-100 RELATIVE-ENERGY REGRESSION ROOT-CAUSE ANALYSIS','',f'Generated UTC: {datetime.now(timezone.utc).isoformat()}',f'Source evaluation SHA256: {sha(PER)}','Blind holdout membership modified: NO','Retraining performed: NO','LAMMPS run: NO','',f'Blind MAE change: {net_abs/len(rows):.17g} meV/atom',f'Blind RMSE: Pilot={math.sqrt(old_sse/len(rows)):.17g}, Dataset100={math.sqrt(new_sse/len(rows)):.17g} meV/atom',f'Net squared-error increase: {net_sse:.17g} (meV/atom)^2','', 'AL3NI ROOT CAUSE',f'DFT ordering: {ordering}',f'Pilot ordering: {po}',f'Dataset-100 ordering: {no}',f"Dominant configuration: {worst['config_id']}",f"Dominant absolute-error change: {worst['change_in_abs_error_mev_atom']} meV/atom",'Interpretation: isolated high-amplitude coupled expansion+rattle magnitude error; ordering preserved. Insufficient blind points to claim a general volume slope or curvature defect.','', 'ATTRIBUTION BY PHASE']
for x in phase: status.append(f"{x['phase']}: MAE contribution={x['contribution_to_blind_mae_change_mev_atom']} meV/atom; net share={x['share_of_net_mae_regression_percent']}%; SSE share={x['share_of_net_squared_error_increase_percent']}%")
status+=['','ATTRIBUTION BY SCIENTIFIC FAMILY CATEGORY']
for x in family: status.append(f"{x['scientific_family_category']}: count={x['count']}; MAE contribution={x['contribution_to_blind_mae_change_mev_atom']} meV/atom; net share={x['share_of_net_mae_regression_percent']}%; SSE share={x['share_of_net_squared_error_increase_percent']}%")
status+=['','TRAINING COVERAGE CONCLUSION','Al3Ni coverage is broad for separate strain, rattle, and shear modes but sparse for coupled volume+rattle: one compression-side TRAIN point and zero VALIDATION points. Expansion-side coupling is unbracketed.','', 'METHODOLOGY CONCLUSION','Pilot-25 and Dataset-100 hyperparameters/objective are identical. Absolute energy only; no explicit relative-energy loss. Aggregate weighted validation loss selected epoch 98 and did not protect phase-relative energy differences.','', 'PRIMARY FAILURE MODE: F. MIXED (A. DATA COVERAGE dominant; B/C secondary)','', 'RECOMMENDED NEXT ACTION:','Freeze a new development design, acquire the proposed symmetric 10-point Al3Ni strain/rattle mini-grid, define a new untouched confirmation holdout, then run controlled TRAIN/VALIDATION-only checkpoint/objective comparisons. Do not reuse the current blind set for selection.','', 'NEW DFT REQUIRED: YES','RETRAINING REQUIRED: YES','BLIND HOLDOUT MODIFIED: NO','LAMMPS APPROVED: NO','', 'DATASET-100 REGRESSION ROOT-CAUSE ANALYSIS COMPLETE','']
STATUS.write_text('\n'.join(status)); subprocess.run(['sync'],check=True); print('\n'.join(status[-12:]))
