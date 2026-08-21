#!/usr/bin/env python3
"""Design-only: close the last 2 EXTRAPOLATION flags after combined-218.

cfg041 (Al3Ni uniaxial_z compression, BLIND_HOLDOUT, flagged at -0.022,
outside TRAIN [-0.0150, 0.0195] by 0.0070) and cfg107 (Al3Ni volume_rattle
compression, VALIDATION, flagged at -0.040, outside TRAIN [-0.0250,
0.0560] by 0.0150) are the only 2 EXTRAPOLATION flags open after
combined-218 (see results/full_coverage_audit_v1/priority_ranking_combined218.md).

Same bracket-margin convention as round212 (design_round212_close_final4.py):
each new TRAIN candidate = Nx the flagged point's own magnitude, same
sign/axis/family. The starting attempt was 1.1x (round212's convention);
both candidates FAIL_REDUNDANT and/or FAIL_LEAKAGE at 1.1x against the
combined-218 population (denser than combined-211, same effect round212
saw). A sweep (1.1x-2.5x in 0.1 steps) found the smallest multiplier that
clears both gates fresh against combined-218: cfg283 (uniaxial_z) needs
1.4x (-0.0308, gate_a/b were still failing at 1.3x); cfg284 (volume_rattle)
needs 1.2x (-0.0480, gate_a still failing at 1.1x). Not round numbers --
the minimum margin measured to clear the gate, per round212's precedent.

cfg109/cfg110 are NOT read or referenced anywhere in this script (explicit
constraint for this design pass). Gate (b) leakage therefore uses the
Al3Ni BLIND_HOLDOUT population already present in combined-218 (cfg041,
cfg042, cfg043, cfg044) as the reserved-point leak reference, instead of
the sealed confirmation-holdout pair used in earlier rounds. All four
gates are re-derived fresh from the combined-218 Al3Ni population, never
reused from any prior round.

NO DFT is run here. NO training. Design-only, matching every prior round's
convention.
"""

import csv
import hashlib
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np
from ase import Atoms
from ase.io import read, write

ROOT = Path("/workspace/ni_al")
COMBINED218_DFT = ROOT / "data/datasets/ni_al_combined218_dft.extxyz"
COMBINED218_TRAIN = ROOT / "data/datasets/ni_al_combined218_train_180.extxyz"
COMBINED218_VALID = ROOT / "data/datasets/ni_al_combined218_validation_18.extxyz"

PHASE_INFO = {"Al3Ni": {"k": (10, 8, 8), "spin": False}}
NEXT_CFG = 283

OUT_BASE = ROOT / "data/al3ni_remediation_v1/round220_structures"
OUT_MANIFEST = ROOT / "data/al3ni_remediation_v1/round220_manifest.csv"
OUT_STATUS = ROOT / "configs/ROUND220_CLOSE_LAST2_DESIGN_STATUS.md"

# (config_id, phase, kind, value, rattle_sigma, gap_ref, flagged_value, bucket_family)
CANDIDATES = [
    ("cfg283_Al3Ni_uniaxial_z_compression", "Al3Ni", "uniaxial_z", -0.022 * 1.4, 0.0,
     "cfg041_Al3Ni_uniaxial_z_compression", -0.022, "uniaxial"),
    ("cfg284_Al3Ni_volume_rattle_compression", "Al3Ni", "isotropic", -0.040 * 1.2, 0.015,
     "cfg107_Al3Ni_volume_rattle_compression", -0.040, "volume_rattle"),
]


def config_family_label(kind, value, rattle):
    """Map deformation kind -> the family label the coverage-audit bucketer
    (scripts/update_full_coverage_audit_combined*.py base_family()) expects,
    matching the naming convention already used in remediation_manifest.csv /
    generate_al3ni_remediation_v1.py (e.g. 'volume_rattle_compression',
    'iso_compression'). Not the same string as the deformation() kind arg
    ('isotropic') -- that mismatch caused cfg284 to fall into an
    unrecognized OTHER: bucket on the first coverage-audit pass."""
    if kind.startswith("uniaxial_"):
        return kind
    if kind == "isotropic":
        sign = "compression" if value < 0 else "expansion"
        return f"volume_rattle_{sign}" if rattle > 0 else f"iso_{sign}"
    raise ValueError(kind)


def deformation(kind, value):
    F = np.eye(3)
    if kind == "isotropic":
        F *= 1.0 + value
    elif kind.startswith("uniaxial_"):
        F["xyz".index(kind[-1]), "xyz".index(kind[-1])] += value
    else:
        raise ValueError(kind)
    return F


def sha256(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def geom_hash(a):
    h = hashlib.sha256()
    h.update(np.asarray(a.numbers, np.int64).tobytes())
    h.update(np.asarray(a.positions, np.float64).tobytes())
    h.update(np.asarray(a.cell.array, np.float64).tobytes())
    return h.hexdigest()


def shape_vector(atoms):
    d = atoms.get_all_distances(mic=True)
    return np.sort(d[np.triu_indices(len(atoms), 1)])


def green_lagrange(cell, ref_cell):
    F = cell @ np.linalg.inv(ref_cell)
    return 0.5 * (F.T @ F - np.eye(3))


def descriptor(atoms, ref_cell):
    return {"shape": shape_vector(atoms), "vol_pa": atoms.get_volume() / len(atoms),
            "strain": green_lagrange(atoms.cell.array, ref_cell)}


def sub_distances(d1, d2):
    d_shape = float(np.sqrt(np.mean((d1["shape"] - d2["shape"]) ** 2)))
    d_vol = float(abs(d1["vol_pa"] - d2["vol_pa"]))
    d_strain = float(np.linalg.norm(d1["strain"] - d2["strain"]))
    return d_shape, d_vol, d_strain


def combined_distance(d1, d2, stds):
    d_shape, d_vol, d_strain = sub_distances(d1, d2)
    s_shape, s_vol, s_strain = stds
    return float(np.sqrt((d_shape / s_shape) ** 2 + (d_vol / s_vol) ** 2 + (d_strain / s_strain) ** 2))


def qe_text(atoms, cid, k, spin):
    pseudo_dir = ROOT / "tools/qe_pseudos"
    al_pseudo, ni_pseudo = "Al.pbe-n-kjpaw_psl.1.0.0.UPF", "ni_pbe_v1.4.uspp.F.UPF"
    lines = [
        "&CONTROL", "  calculation = 'scf',", f"  prefix = '{cid}',",
        f"  pseudo_dir = '{pseudo_dir}',", f"  outdir = '{OUT_BASE / 'qe_outputs' / cid / 'tmp'}',",
        "  tprnfor = .true.,", "  tstress = .true.,", "  disk_io = 'low',", "/",
        "&SYSTEM", "  ibrav = 0,", f"  nat = {len(atoms)},", "  ntyp = 2,",
        "  ecutwfc = 90.0,", "  ecutrho = 720.0,", "  occupations = 'smearing',",
        "  smearing = 'mv',", "  degauss = 0.010,",
    ]
    if spin:
        lines += ["  nspin = 2,", "  starting_magnetization(2) = 0.60,"]
    lines += [
        "/", "&ELECTRONS", "  conv_thr = 1.0d-10,", "  electron_maxstep = 200,",
        "  mixing_beta = 0.30,", "  diagonalization = 'david',", "/",
        "ATOMIC_SPECIES", f"Al 26.9815385 {al_pseudo}", f"Ni 58.6934 {ni_pseudo}",
        "CELL_PARAMETERS angstrom",
    ]
    lines += [" ".join(f"{x:.12f}" for x in row) for row in atoms.cell.array]
    lines += ["ATOMIC_POSITIONS crystal"]
    lines += [f"{s} " + " ".join(f"{x:.12f}" for x in q) for s, q in zip(atoms.get_chemical_symbols(), atoms.get_scaled_positions(wrap=True))]
    lines += ["K_POINTS automatic", f"{k[0]} {k[1]} {k[2]} 0 0 0", ""]
    return "\n".join(lines)


def main():
    dft = read(COMBINED218_DFT, index=":")
    train_ids = {a.info["config_id"] for a in read(COMBINED218_TRAIN, index=":")}
    valid_ids = {a.info["config_id"] for a in read(COMBINED218_VALID, index=":")}

    al3ni = [a for a in dft if a.info.get("phase") == "Al3Ni"]
    by_id = {a.info["config_id"]: a for a in al3ni}
    ref_cell = by_id["Al3Ni_relaxed"].cell.array.copy()

    def role_of(cid):
        if cid in train_ids:
            return "TRAIN"
        if cid in valid_ids:
            return "VALIDATION"
        return "RESERVED"  # BLIND_HOLDOUT or TEST -- role detail not needed, just "not TRAIN/VALIDATION"

    desc = {cid: descriptor(a, ref_cell) for cid, a in by_id.items()}
    train_pop = [c for c in desc if role_of(c) == "TRAIN"]
    reserved_pop = [c for c in desc if role_of(c) == "RESERVED"]
    valid_pop = [c for c in desc if role_of(c) == "VALIDATION"]

    print(f"Al3Ni population: {len(al3ni)} total, {len(train_pop)} TRAIN, "
          f"{len(valid_pop)} VALIDATION, {len(reserved_pop)} RESERVED (BLIND_HOLDOUT/TEST)")
    print(f"RESERVED members: {sorted(reserved_pop)}")

    # gate (a) threshold: 5th percentile of pairwise Al3Ni TRAIN-TRAIN combined distances
    pairs = list(combinations(train_pop, 2))
    pair_shape, pair_vol, pair_strain = [], [], []
    for id1, id2 in pairs:
        ds, dv, dst = sub_distances(desc[id1], desc[id2])
        pair_shape.append(ds); pair_vol.append(dv); pair_strain.append(dst)
    stds = (np.std(pair_shape) or 1e-12, np.std(pair_vol) or 1e-12, np.std(pair_strain) or 1e-12)
    pair_combined = [combined_distance(desc[id1], desc[id2], stds) for id1, id2 in pairs]
    threshold_a = float(np.percentile(pair_combined, 5))

    # gate (b) leak threshold: min TRAIN<->RESERVED combined distance, Al3Ni only
    # (cfg109/cfg110 NOT used -- reserved population is the BLIND_HOLDOUT/TEST set
    # already present in combined-218: cfg041, cfg042, cfg043, cfg044, Al3Ni_shear015_rattle002)
    leak_pairs = [combined_distance(desc[t], desc[r], stds) for t in train_pop for r in reserved_pop]
    threshold_b = float(min(leak_pairs))

    # gate (d) reference: descriptor blind spot -- flag any candidate with d_vol==0 and
    # d_strain==0 against a VALIDATION member (rattle-only near-duplicate risk)
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    kept, report_rows = [], []
    kept_geoms = {geom_hash(a) for a in al3ni}

    for cid, phase, kind, value, rattle, gap_ref, flagged_val, bucket in CANDIDATES:
        ref = by_id["Al3Ni_relaxed"]
        seed = 20262000 + int(cid[3:6])
        F = deformation(kind, value)
        cand = Atoms(numbers=ref.numbers, positions=ref.positions.copy(), cell=ref.cell.array.copy(), pbc=True)
        cand.set_cell(cand.cell.array @ F.T, scale_atoms=True)
        if rattle > 0:
            rng = np.random.default_rng(seed)
            disp = rng.normal(0, rattle, (len(cand), 3))
            disp -= disp.mean(axis=0)
            cand.positions += disp
            cand.wrap()
        cand.info = {"config_id": cid, "phase": phase}

        cdesc = descriptor(cand, ref_cell)

        dists_train = [combined_distance(cdesc, desc[t], stds) for t in train_pop]
        min_dist_train = min(dists_train)
        nearest_train = train_pop[int(np.argmin(dists_train))]
        gate_a = "PASS" if min_dist_train >= threshold_a else "FAIL_REDUNDANT"

        dists_reserved = [combined_distance(cdesc, desc[r], stds) for r in reserved_pop]
        min_dist_reserved = min(dists_reserved)
        nearest_reserved = reserved_pop[int(np.argmin(dists_reserved))]
        gate_b = "PASS" if min_dist_reserved >= threshold_b else "FAIL_LEAKAGE"

        gh = geom_hash(cand)
        gate_c = "PASS" if gh not in kept_geoms else "FAIL_DUPLICATE"

        blind_spot_hits = []
        for v in valid_pop:
            _, dv, dst = sub_distances(cdesc, desc[v])
            if dv == 0.0 and dst == 0.0:
                blind_spot_hits.append(v)
        gate_d = "PASS" if not blind_spot_hits else "FAIL_ROLE_COLLISION"

        # coverage check: does this candidate actually extend the flagged bucket's TRAIN range?
        train_bucket_vals = [flagged_val]  # placeholder, real bucket-range check is in the audit script;
        closes_flag = "Y" if (value < 0 and value < flagged_val) or (value > 0 and value > flagged_val) else "N"

        status = "KEPT" if all(g in ("PASS",) for g in (gate_a, gate_b, gate_c, gate_d)) else "REJECTED"
        report_rows.append({
            "config_id": cid, "gap_ref": gap_ref, "flagged_value": flagged_val,
            "candidate_value": value, "closes_flag_by_construction": closes_flag,
            "min_dist_train": min_dist_train, "nearest_train": nearest_train, "threshold_a": threshold_a,
            "min_dist_reserved": min_dist_reserved, "nearest_reserved": nearest_reserved, "threshold_b": threshold_b,
            "gate_a": gate_a, "gate_b": gate_b, "gate_c": gate_c, "gate_d": gate_d, "status": status,
        })
        if status == "KEPT":
            kept_geoms.add(gh)
            kept.append((cid, phase, kind, value, rattle, seed, gap_ref, cand))

    manifest_rows = []
    for cid, phase, kind, value, rattle, seed, gap_ref, cand in kept:
        sdir = OUT_BASE / f"round220_{phase.lower()}"
        sdir.mkdir(parents=True, exist_ok=True)
        sp = sdir / f"{cid}.extxyz"
        qp = sdir / f"{cid}.in"
        write(sp, cand, format="extxyz")
        qp.write_text(qe_text(cand, cid, PHASE_INFO[phase]["k"], PHASE_INFO[phase]["spin"]))
        reread = read(sp)
        vals_d = reread.get_all_distances(mic=True)[np.triu_indices(len(reread), 1)]
        manifest_rows.append({
            "config_id": cid, "phase": phase, "config_family": config_family_label(kind, value, rattle),
            "target_role": "TRAIN", "strain_type": kind,
            "strain_or_shear_value": format(value, ".17g"),
            "rattle_sigma_A": rattle, "random_seed": seed if rattle > 0 else "NONE", "gap_ref": gap_ref,
            "natoms": len(reread), "minimum_distance_A": format(float(vals_d.min()), ".17g"),
            "structure_path": str(sp), "structure_sha256": sha256(sp),
            "qe_input_path": str(qp), "qe_input_sha256": sha256(qp),
        })

    if manifest_rows:
        with OUT_MANIFEST.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(manifest_rows[0]))
            w.writeheader()
            w.writerows(manifest_rows)

    lines = [
        "# Round-220: Close the Last 2 EXTRAPOLATION Flags (design-only, NO DFT run)",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "Targets: cfg041 (Al3Ni uniaxial_z compression, BLIND_HOLDOUT), "
        "cfg107 (Al3Ni volume_rattle compression, VALIDATION).",
        "Each candidate = Nx the flagged point's own magnitude, same sign/axis/family "
        "(N swept from 1.1x; smallest passing found: cfg283=1.4x, cfg284=1.2x).",
        "cfg109/cfg110 NOT read or referenced. Gate (b) uses the Al3Ni BLIND_HOLDOUT/TEST "
        "population already in combined-218 as the leak reference.",
        "",
        "## Gate results", "",
        "| config_id | gap closed | flagged value | candidate value | closes by construction | "
        "min dist TRAIN | nearest TRAIN | thr(a) | min dist RESERVED | nearest RESERVED | thr(b) | "
        "gate(a) | gate(b) | gate(c) | gate(d) | status |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in report_rows:
        lines.append(
            f"| {r['config_id']} | {r['gap_ref']} | {r['flagged_value']:.4f} | {r['candidate_value']:.4f} | "
            f"{r['closes_flag_by_construction']} | {r['min_dist_train']:.4f} | {r['nearest_train']} | {r['threshold_a']:.4f} | "
            f"{r['min_dist_reserved']:.4f} | {r['nearest_reserved']} | {r['threshold_b']:.4f} | "
            f"{r['gate_a']} | {r['gate_b']} | {r['gate_c']} | {r['gate_d']} | **{r['status']}** |"
        )
    lines += ["", f"KEPT: {len(kept)}/{len(CANDIDATES)}", "",
              "## Not done in this pass",
              "DFT has not been run. No merge into any TRAIN/VALIDATION split. "
              "cfg109/cfg110 were never read or referenced."]
    OUT_STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
