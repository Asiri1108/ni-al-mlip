#!/usr/bin/env python3
"""Generate and validate Dataset-100 structures and static QE inputs (no DFT)."""
from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter
from pathlib import Path

import numpy as np
from ase.io import read, write
from ase.geometry import get_distances

ROOT = Path("/workspace/ni_al")
BASE = ROOT / "data/expansion_026_100"
STRUCT = BASE / "structures"
QE = BASE / "qe_inputs"
VALID = BASE / "validation"
MANIFEST = BASE / "manifests/configs_026_100_design.csv"
FULL = ROOT / "data/processed/ni_al_pilot_dft_25.extxyz"
PSEUDO_DIR = ROOT / "pseudo"

PHASE_INFO = {
    "AlNi":   {"n": 2,  "formula": {"Al": 1, "Ni": 1}, "k": (16,16,16), "spin": False},
    "Al3Ni":  {"n": 16, "formula": {"Al":12, "Ni": 4}, "k": (10,8,8),   "spin": False},
    "Al3Ni2": {"n": 5,  "formula": {"Al": 3, "Ni": 2}, "k": (14,14,10), "spin": False},
    "Al3Ni5": {"n": 8,  "formula": {"Al": 3, "Ni": 5}, "k": (12,10,10), "spin": False},
    "AlNi3":  {"n": 4,  "formula": {"Al": 1, "Ni": 3}, "k": (14,14,14), "spin": True},
}

# Each tuple: role, family, strain_type, strain_value, shear_value, rattle_sigma.
DESIGN = {
"Al3Ni": [
 ("TRAIN_CANDIDATE","iso_compression","isotropic",-.01,0,0),("TRAIN_CANDIDATE","iso_expansion","isotropic",.01,0,0),
 ("TRAIN_CANDIDATE","iso_compression","isotropic",-.03,0,0),("TRAIN_CANDIDATE","iso_expansion","isotropic",.03,0,0),
 ("TRAIN_CANDIDATE","uniaxial_x_compression","uniaxial_x",-.015,0,0),("TRAIN_CANDIDATE","uniaxial_y_expansion","uniaxial_y",.015,0,0),
 ("TRAIN_CANDIDATE","orthorhombic_xy","orthorhombic_xy",.015,0,0),("TRAIN_CANDIDATE","shear_xy_negative","shear_xy",0,-.010,0),
 ("TRAIN_CANDIDATE","shear_xz_positive","shear_xz",0,.010,0),("TRAIN_CANDIDATE","rattle_small","none",0,0,.010),
 ("TRAIN_CANDIDATE","rattle_large","none",0,0,.040),("TRAIN_CANDIDATE","volume_rattle_compression","isotropic",-.025,0,.020),
 ("TRAIN_CANDIDATE","shear_rattle_yz","shear_yz",0,.020,.025),
 ("VALIDATION","biaxial_xy_expansion","biaxial_xy",.012,0,0),("VALIDATION","rattle_medium","none",0,0,.025),
 ("BLIND_HOLDOUT","uniaxial_z_compression","uniaxial_z",-.022,0,0),("BLIND_HOLDOUT","shear_xz_negative","shear_xz",0,-.018,0),
 ("BLIND_HOLDOUT","volume_rattle_expansion","isotropic",.035,0,.015),("BLIND_HOLDOUT","shear_rattle_xy_negative","shear_xy",0,-.025,.035)],
"Al3Ni5": [
 ("TRAIN_CANDIDATE","iso_compression","isotropic",-.01,0,0),("TRAIN_CANDIDATE","iso_expansion","isotropic",.01,0,0),
 ("TRAIN_CANDIDATE","iso_compression","isotropic",-.03,0,0),("TRAIN_CANDIDATE","iso_expansion","isotropic",.03,0,0),
 ("TRAIN_CANDIDATE","uniaxial_y_compression","uniaxial_y",-.015,0,0),("TRAIN_CANDIDATE","orthorhombic_yz","orthorhombic_yz",.015,0,0),
 ("TRAIN_CANDIDATE","shear_xy_negative","shear_xy",0,-.010,0),("TRAIN_CANDIDATE","shear_yz_positive","shear_yz",0,.010,0),
 ("TRAIN_CANDIDATE","rattle_small","none",0,0,.010),("TRAIN_CANDIDATE","rattle_large","none",0,0,.040),
 ("TRAIN_CANDIDATE","volume_rattle_compression","isotropic",-.025,0,.020),
 ("VALIDATION","uniaxial_x_expansion","uniaxial_x",.018,0,0),("VALIDATION","shear_rattle_xz_positive","shear_xz",0,.018,.025),
 ("BLIND_HOLDOUT","biaxial_xz_compression","biaxial_xz",-.016,0,0),("BLIND_HOLDOUT","shear_yz_negative","shear_yz",0,-.022,0),
 ("BLIND_HOLDOUT","volume_rattle_expansion","isotropic",.035,0,.015),("BLIND_HOLDOUT","rattle_xlarge","none",0,0,.050)],
"Al3Ni2": [
 ("TRAIN_CANDIDATE","iso_compression","isotropic",-.01,0,0),("TRAIN_CANDIDATE","iso_expansion","isotropic",.01,0,0),
 ("TRAIN_CANDIDATE","iso_compression","isotropic",-.03,0,0),("TRAIN_CANDIDATE","iso_expansion","isotropic",.03,0,0),
 ("TRAIN_CANDIDATE","uniaxial_z_expansion","uniaxial_z",.015,0,0),("TRAIN_CANDIDATE","shear_xy_negative","shear_xy",0,-.010,0),
 ("TRAIN_CANDIDATE","rattle_small","none",0,0,.010),("TRAIN_CANDIDATE","rattle_large","none",0,0,.040),
 ("TRAIN_CANDIDATE","volume_rattle_compression","isotropic",-.025,0,.020),
 ("VALIDATION","orthorhombic_xy","orthorhombic_xy",.016,0,0),("VALIDATION","shear_rattle_yz_positive","shear_yz",0,.018,.025),
 ("BLIND_HOLDOUT","biaxial_xy_compression","biaxial_xy",-.018,0,0),("BLIND_HOLDOUT","shear_xz_negative","shear_xz",0,-.022,0),
 ("BLIND_HOLDOUT","volume_rattle_expansion","isotropic",.035,0,.015)],
"AlNi": [
 ("TRAIN_CANDIDATE","iso_compression","isotropic",-.01,0,0),("TRAIN_CANDIDATE","iso_expansion","isotropic",.01,0,0),
 ("TRAIN_CANDIDATE","iso_compression","isotropic",-.03,0,0),("TRAIN_CANDIDATE","iso_expansion","isotropic",.03,0,0),
 ("TRAIN_CANDIDATE","uniaxial_x_expansion","uniaxial_x",.015,0,0),("TRAIN_CANDIDATE","shear_xy_negative","shear_xy",0,-.010,0),
 ("TRAIN_CANDIDATE","rattle_small","none",0,0,.010),("TRAIN_CANDIDATE","rattle_large","none",0,0,.040),
 ("TRAIN_CANDIDATE","volume_rattle_compression","isotropic",-.025,0,.020),
 ("VALIDATION","orthorhombic_yz","orthorhombic_yz",.016,0,0),("VALIDATION","shear_rattle_xz_positive","shear_xz",0,.018,.025),
 ("BLIND_HOLDOUT","biaxial_xz_compression","biaxial_xz",-.018,0,0),("BLIND_HOLDOUT","shear_rattle_yz_negative","shear_yz",0,-.022,.015)],
"AlNi3": [
 ("TRAIN_CANDIDATE","iso_compression","isotropic",-.01,0,0),("TRAIN_CANDIDATE","iso_expansion","isotropic",.01,0,0),
 ("TRAIN_CANDIDATE","iso_compression","isotropic",-.03,0,0),("TRAIN_CANDIDATE","iso_expansion","isotropic",.03,0,0),
 ("TRAIN_CANDIDATE","uniaxial_y_compression","uniaxial_y",-.015,0,0),("TRAIN_CANDIDATE","shear_xy_negative","shear_xy",0,-.010,0),
 ("TRAIN_CANDIDATE","rattle_small","none",0,0,.010),("TRAIN_CANDIDATE","rattle_large","none",0,0,.040),
 ("VALIDATION","orthorhombic_xz","orthorhombic_xz",.016,0,0),("VALIDATION","volume_rattle_compression","isotropic",-.025,0,.020),
 ("BLIND_HOLDOUT","biaxial_yz_expansion","biaxial_yz",.018,0,0),("BLIND_HOLDOUT","shear_rattle_xz_negative","shear_xz",0,-.022,.025)],
}

FIELDS = ["config_id","phase","config_family","config_type","target_role","strain_type","strain_value","rattle_sigma_A","shear_value","random_seed","n_atoms","source_structure","generation_status","validation_status","qe_input_status","qe_output_status","assigned_machine","gpu_model","wall_time_seconds","dft_status","sha256_input","sha256_output","notes"]

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def deformation(kind: str, value: float, shear: float) -> np.ndarray:
    F=np.eye(3)
    if kind == "isotropic": F *= 1.0 + value
    elif kind.startswith("uniaxial_"): F["xyz".index(kind[-1]),"xyz".index(kind[-1])] += value
    elif kind.startswith("biaxial_"):
        for c in kind[-2:]: F["xyz".index(c),"xyz".index(c)] += value
    elif kind.startswith("orthorhombic_"):
        a,b=kind[-2:]; F["xyz".index(a),"xyz".index(a)] += value; F["xyz".index(b),"xyz".index(b)] -= value
    elif kind.startswith("shear_"):
        a,b=kind[-2:]; F["xyz".index(a),"xyz".index(b)] += shear
    elif kind != "none": raise ValueError(kind)
    return F

def qe_text(atoms, cid, phase):
    info=PHASE_INFO[phase]; spin=info["spin"]
    system=["  ibrav = 0,",f"  nat = {len(atoms)},","  ntyp = 2,","  ecutwfc = 90.0,","  ecutrho = 720.0,","  occupations = 'smearing',","  smearing = 'mv',","  degauss = 0.010,"]
    if spin: system += ["  nspin = 2,","  starting_magnetization(2) = 0.60,"]
    lines=["&CONTROL","  calculation = 'scf',",f"  prefix = '{cid}',",f"  pseudo_dir = '{PSEUDO_DIR}',",f"  outdir = '{BASE / 'qe_outputs' / cid / 'tmp'}',","  tprnfor = .true.,","  tstress = .true.,","  disk_io = 'low',","/","&SYSTEM",*system,"/","&ELECTRONS","  conv_thr = 1.0d-10,","  electron_maxstep = 200,","  mixing_beta = 0.30,","  diagonalization = 'david',","/","ATOMIC_SPECIES","Al 26.9815385 Al.pbe-n-kjpaw_psl.1.0.0.UPF","Ni 58.6934 ni_pbe_v1.4.uspp.F.UPF","CELL_PARAMETERS angstrom"]
    lines += [" ".join(f"{x:.12f}" for x in row) for row in atoms.cell.array]
    lines += ["ATOMIC_POSITIONS crystal"]
    lines += [f"{s} " + " ".join(f"{x:.12f}" for x in p) for s,p in zip(atoms.get_chemical_symbols(),atoms.get_scaled_positions(wrap=True))]
    k=info["k"]; lines += ["K_POINTS automatic",f"{k[0]} {k[1]} {k[2]} 0 0 0",""]
    return "\n".join(lines)

def main():
    for p in (STRUCT,QE,VALID,MANIFEST.parent,BASE/"qe_outputs",BASE/"team_assignments",BASE/"gpu_benchmark"): p.mkdir(parents=True,exist_ok=True)
    all_atoms=read(FULL,index=":")
    relaxed={a.info["phase"]:a for a in all_atoms if a.info.get("config_type")=="relaxed"}
    assert set(relaxed)==set(PHASE_INFO)
    assert sum(map(len,DESIGN.values()))==75
    rows=[]; generated=[]; num=26
    for phase, entries in DESIGN.items():
        for role,family,stype,sval,shear,rattle in entries:
            cid=f"cfg{num:03d}_{phase}_{family}"
            seed=20261000+num
            atoms=relaxed[phase].copy(); atoms.calc=None
            F=deformation(stype,sval,shear)
            atoms.set_cell(atoms.cell.array @ F.T,scale_atoms=True)
            if rattle:
                rng=np.random.default_rng(seed); disp=rng.normal(0,rattle,(len(atoms),3)); disp-=disp.mean(axis=0)
                atoms.positions += disp; atoms.wrap()
            atoms.info={"config_id":cid,"phase":phase,"config_family":family,"config_type":family,"target_role":role,"strain_type":stype,"strain_value":float(sval),"rattle_sigma_A":float(rattle),"shear_value":float(shear),"random_seed":int(seed),"source_structure":f"{phase}_relaxed"}
            sp=STRUCT/f"{cid}.extxyz"; qp=QE/f"{cid}.in"
            if sp.exists() or qp.exists(): raise FileExistsError(f"Refusing overwrite: {sp} or {qp}")
            write(sp,atoms,format="extxyz"); qp.write_text(qe_text(atoms,cid,phase))
            row={k:"" for k in FIELDS}; row.update({"config_id":cid,"phase":phase,"config_family":family,"config_type":family,"target_role":role,"strain_type":stype,"strain_value":sval,"rattle_sigma_A":rattle,"shear_value":shear,"random_seed":seed,"n_atoms":len(atoms),"source_structure":f"{phase}_relaxed","generation_status":"GENERATED","validation_status":"PENDING","qe_input_status":"READY_NOT_RUN","qe_output_status":"NOT_RUN","dft_status":"NOT_RUN","sha256_input":sha(qp),"notes":f"structure={sp}; qe_input={qp}"})
            rows.append(row); generated.append((row,atoms,sp,qp)); num+=1
    assert num==101

    errors=[]; fingerprints=set(); min_dist=math.inf
    for row,atoms,sp,qp in generated:
        phase=row["phase"]; expected=PHASE_INFO[phase]
        if len(atoms)!=expected["n"] or Counter(atoms.get_chemical_symbols())!=Counter(expected["formula"]): errors.append(f"{row['config_id']}: composition/atom-count mismatch")
        if not np.isfinite(atoms.cell.array).all() or atoms.get_volume()<=0: errors.append(f"{row['config_id']}: invalid cell")
        if not atoms.pbc.all() or not np.isfinite(atoms.positions).all(): errors.append(f"{row['config_id']}: invalid PBC/positions")
        d=atoms.get_all_distances(mic=True); vals=d[np.triu_indices(len(atoms),1)]
        md=float(vals.min()) if vals.size else math.inf; min_dist=min(min_dist,md)
        if md<1.8: errors.append(f"{row['config_id']}: close contact {md:.6f} A")
        key=hashlib.sha256(("".join(atoms.get_chemical_symbols())+np.array2string(np.round(atoms.cell.array,8))+np.array2string(np.round(atoms.get_scaled_positions(wrap=True),8))).encode()).hexdigest()
        if key in fingerprints: errors.append(f"{row['config_id']}: exact duplicate")
        fingerprints.add(key)
        txt=qp.read_text()
        for required in ("ecutwfc = 90.0","ecutrho = 720.0","smearing = 'mv'","degauss = 0.010","conv_thr = 1.0d-10","Al.pbe-n-kjpaw_psl.1.0.0.UPF","ni_pbe_v1.4.uspp.F.UPF"):
            if required not in txt: errors.append(f"{row['config_id']}: missing QE setting {required}")
        row["validation_status"]="FAIL" if any(e.startswith(row["config_id"]+":") for e in errors) else "PASS"

    roles=Counter(r["target_role"] for r in rows); phases=Counter(r["phase"] for r in rows)
    if roles!=Counter({"TRAIN_CANDIDATE":50,"VALIDATION":10,"BLIND_HOLDOUT":15}): errors.append(f"role counts wrong: {roles}")
    if phases!=Counter({"Al3Ni":19,"Al3Ni5":17,"Al3Ni2":14,"AlNi":13,"AlNi3":12}): errors.append(f"phase counts wrong: {phases}")
    with MANIFEST.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    report=["DATASET-100 STRUCTURE VALIDATION REPORT","",f"Generated structures: {len(rows)}",f"Valid structures: {sum(r['validation_status']=='PASS' for r in rows)}",f"QE inputs checked: {len(rows)}",f"Unique config_ids: {len(set(r['config_id'] for r in rows))}",f"Exact duplicate fingerprints: {len(rows)-len(fingerprints)}",f"Minimum interatomic distance: {min_dist:.6f} A",f"Role counts: {dict(roles)}",f"Phase counts: {dict(phases)}","All cells finite and positive: YES" if not any("invalid cell" in e for e in errors) else "All cells finite and positive: NO","All coordinates finite and PBC enabled: YES" if not any("PBC/positions" in e for e in errors) else "All coordinates finite and PBC enabled: NO","Composition and atom counts correct: YES" if not any("composition" in e for e in errors) else "Composition and atom counts correct: NO","Pilot files modified: NO","DFT executed: NO","", "Errors:"] + (errors if errors else ["NONE"])
    (VALID/"STRUCTURE_VALIDATION_REPORT.txt").write_text("\n".join(report)+"\n")
    if errors: raise SystemExit("Validation failed:\n"+"\n".join(errors))
    print(f"GENERATED={len(rows)} VALID={len(rows)} QE_INPUTS={len(rows)} MIN_DISTANCE_A={min_dist:.6f}")

if __name__=="__main__": main()
