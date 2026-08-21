#!/usr/bin/env python3
"""Design-only: Al3Ni2 shear-gap closure (magnitude sweep, find the
minimum that clears redundancy) + AlNi thin-bucket closure (shear n=1,
volume_rattle n=2). No DFT, no training, cfg109/cfg110 never accessed
(neither phase is Al3Ni).

Al3Ni2: cfg074_Al3Ni2_shear_xz_negative (-0.022) is the flagged gap.
round300's 0.01-magnitude shear attempt failed 0/27 (too close to
relaxed). round212 already showed shear_xz collides with round300's
cfg216_Al3Ni2_shear_rattle_xz_negative (-0.029) sibling -- same axis,
increasing magnitude got CLOSER to that sibling, not farther. Using
shear_xy instead (no rattled sibling on that axis for Al3Ni2; the
coverage-audit "shear" bucket pools all axes, so this still closes the
cfg074 flag). Sweeps multiple magnitudes to find the minimum that clears
gate (a), rather than jumping to one guess.

AlNi: shear has only 1 TRAIN member (cfg081, shear_xy, -0.01). Rattled
siblings occupy shear_xz (+0.027, -0.029) and shear_yz (-0.045) -- xy
positive and yz positive are the only axis/sign combos with no nearby
collision. volume_rattle has 2 TRAIN members (cfg084 compression -0.025,
cfg170 expansion +0.046); adding one more (deeper compression) reaches
n=3.

Gate (a) threshold re-derived fresh per phase from current combined-211
population. Gate (b) N/A (neither phase is Al3Ni). Gate (c) duplicate
check vs population and sibling candidates in this batch.
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
COMBINED211 = ROOT / "data/datasets/ni_al_combined211_dft.extxyz"
PSEUDO_DIR = ROOT / "tools/qe_pseudos"
AL_PSEUDO = "Al.pbe-n-kjpaw_psl.1.0.0.UPF"
NI_PSEUDO = "ni_pbe_v1.4.uspp.F.UPF"

OUT_BASE = ROOT / "data/al3ni_remediation_v1/round213_structures"
OUT_MANIFEST = ROOT / "data/al3ni_remediation_v1/round213_manifest.csv"
OUT_STATUS = ROOT / "configs/ROUND213_AL3NI2_ALNI_DESIGN_STATUS.md"

PHASE_INFO = {"AlNi": {"k": (16, 16, 16), "spin": False}, "Al3Ni2": {"k": (14, 14, 10), "spin": False}}
ROLE_MAP = {"HISTORICAL_TRAIN": "TRAIN", "TRAIN_CANDIDATE": "TRAIN", "TRAIN": "TRAIN"}
NEXT_CFG = 277

# Al3Ni2 sweep: find the minimum magnitude (shear_xy, negative, same sign as cfg074) that
# clears gate (a). Not a single guess -- test several, report the smallest PASS.
AL3NI2_SWEEP = [-0.030, -0.038, -0.045, -0.050, -0.055]

# AlNi thin-bucket candidates: one guess each, adjusted empirically if needed.
ALNI_CANDIDATES = [
    ("shear_xy", 0.0, 0.030, 0.0, "shear", "close AlNi/shear thin bucket (n=1->3), axis 1/2"),
    ("shear_yz", 0.0, 0.030, 0.0, "shear", "close AlNi/shear thin bucket (n=1->3), axis 2/2"),
    ("isotropic", -0.040, 0.0, 0.02, "volume_rattle", "close AlNi/volume_rattle thin bucket (n=2->3), deeper compression"),
]


def deformation(kind, value, shear):
    F = np.eye(3)
    if kind == "isotropic":
        F *= 1.0 + value
    elif kind.startswith("shear_"):
        a, b = kind[-2:]
        F["xyz".index(a), "xyz".index(b)] += shear
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
    lines = [
        "&CONTROL", "  calculation = 'scf',", f"  prefix = '{cid}',",
        f"  pseudo_dir = '{PSEUDO_DIR}',", f"  outdir = '{OUT_BASE / 'qe_outputs' / cid / 'tmp'}',",
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
        "ATOMIC_SPECIES", f"Al 26.9815385 {AL_PSEUDO}", f"Ni 58.6934 {NI_PSEUDO}",
        "CELL_PARAMETERS angstrom",
    ]
    lines += [" ".join(f"{x:.12f}" for x in row) for row in atoms.cell.array]
    lines += ["ATOMIC_POSITIONS crystal"]
    lines += [f"{s} " + " ".join(f"{x:.12f}" for x in q) for s, q in zip(atoms.get_chemical_symbols(), atoms.get_scaled_positions(wrap=True))]
    lines += ["K_POINTS automatic", f"{k[0]} {k[1]} {k[2]} 0 0 0", ""]
    return "\n".join(lines)


def build_role_lookup():
    lookup = {}
    for name in ("train", "validation", "test", "blind_holdout"):
        for r in csv.DictReader((ROOT / f"data/datasets/ni_al_dataset100_{name}_manifest.csv").open(newline="")):
            lookup[r["config_id"]] = ROLE_MAP.get(r["target_role"], r["target_role"])
    for path, col in [(ROOT / "data/al3ni_remediation_v1/remediation_manifest.csv", "split"),
                       (ROOT / "data/al3ni_remediation_v1/round2_manifest.csv", "split")]:
        for r in csv.DictReader(path.open(newline="")):
            if "sealed" in str(r.get("confirmation_label_policy", "")).lower():
                continue
            lookup[r["config_id"]] = r[col]
    for path in (ROOT / "data/al3ni_remediation_v1/round3_manifest.csv",
                 ROOT / "data/al3ni_remediation_v1/round4_biaxial_manifest.csv",
                 ROOT / "data/al3ni_remediation_v1/round300_manifest.csv"):
        for r in csv.DictReader(path.open(newline="")):
            lookup[r["config_id"]] = r["target_role"]
    return lookup


def main():
    frames = read(COMBINED211, index=":")
    by_id = {a.info["config_id"]: a for a in frames}
    role_lookup = build_role_lookup()

    phases = ("AlNi", "Al3Ni2")
    phase_pop = {p: [a for a in frames if a.info["phase"] == p] for p in phases}
    phase_ref_cell = {p: by_id[f"{p}_relaxed"].cell.array.copy() for p in phases}
    phase_desc = {p: {a.info["config_id"]: descriptor(a, phase_ref_cell[p]) for a in phase_pop[p]} for p in phases}

    phase_stds, phase_threshold = {}, {}
    for p in phases:
        pop_desc = phase_desc[p]
        pairs = list(combinations(pop_desc, 2))
        pair_shape, pair_vol, pair_strain = [], [], []
        for id1, id2 in pairs:
            ds, dv, dst = sub_distances(pop_desc[id1], pop_desc[id2])
            pair_shape.append(ds); pair_vol.append(dv); pair_strain.append(dst)
        stds = (np.std(pair_shape) or 1e-12, np.std(pair_vol) or 1e-12, np.std(pair_strain) or 1e-12)
        phase_stds[p] = stds
        pair_combined = [combined_distance(pop_desc[id1], pop_desc[id2], stds) for id1, id2 in pairs]
        phase_threshold[p] = float(np.percentile(pair_combined, 5))

    cfg_counter = NEXT_CFG
    kept_geoms = {p: {geom_hash(a) for a in phase_pop[p]} for p in phases}
    report_rows, kept = [], []

    def try_candidate(phase, kind, value, shear, rattle, purpose, cid):
        nonlocal cfg_counter
        ref = by_id[f"{phase}_relaxed"]
        seed = 20261000 + cfg_counter
        F = deformation(kind, value, shear)
        cand = Atoms(numbers=ref.numbers, positions=ref.positions.copy(), cell=ref.cell.array.copy(), pbc=True)
        cand.set_cell(cand.cell.array @ F.T, scale_atoms=True)
        if rattle > 0:
            rng = np.random.default_rng(seed)
            disp = rng.normal(0, rattle, (len(cand), 3))
            disp -= disp.mean(axis=0)
            cand.positions += disp
            cand.wrap()
        cand.info = {"config_id": cid, "phase": phase}

        cdesc = descriptor(cand, phase_ref_cell[phase])
        train_ids = [c for c in phase_desc[phase] if role_lookup.get(c) == "TRAIN"]
        dists = [combined_distance(cdesc, phase_desc[phase][t], phase_stds[phase]) for t in train_ids]
        min_dist = min(dists)
        nearest = train_ids[int(np.argmin(dists))]
        gate_a = "PASS" if min_dist >= phase_threshold[phase] else "FAIL_REDUNDANT"
        gh = geom_hash(cand)
        gate_c = "PASS" if gh not in kept_geoms[phase] else "FAIL_DUPLICATE"
        status = "KEPT" if gate_a == "PASS" and gate_c == "PASS" else "REJECTED"
        row = {"config_id": cid, "phase": phase, "purpose": purpose, "kind": kind,
               "value": value if kind == "isotropic" else shear, "rattle": rattle,
               "min_dist_to_train": min_dist, "nearest_train": nearest, "threshold": phase_threshold[phase],
               "gate_a": gate_a, "gate_c": gate_c, "status": status}
        report_rows.append(row)
        if status == "KEPT":
            kept_geoms[phase].add(gh)
            kept.append((cid, phase, kind, value, shear, rattle, seed, cand, purpose))
        cfg_counter += 1
        return status

    # Al3Ni2 sweep: find the minimum magnitude that clears gate (a).
    sweep_results = []
    for mag in AL3NI2_SWEEP:
        cid = f"cfg{cfg_counter}_Al3Ni2_shear_xy_negative_sweep"
        status = try_candidate("Al3Ni2", "shear_xy", 0.0, mag, 0.0, "cfg074 gap sweep", cid)
        sweep_results.append((mag, status))
        if status == "KEPT":
            break  # smallest passing magnitude found; stop sweeping further

    # AlNi thin-bucket candidates.
    for kind, value, shear, rattle, family, purpose in ALNI_CANDIDATES:
        axis_tag = kind.split("_")[-1] if "_" in kind else "iso"
        sign_tag = "negative" if (shear if kind.startswith("shear") else value) < 0 else "positive"
        cid = f"cfg{cfg_counter}_AlNi_{family}_{axis_tag}_{sign_tag}"
        try_candidate("AlNi", kind, value, shear, rattle, purpose, cid)

    manifest_rows = []
    for cid, phase, kind, value, shear, rattle, seed, cand, purpose in kept:
        sdir = OUT_BASE / f"round213_{phase.lower()}"
        sdir.mkdir(parents=True, exist_ok=True)
        sp = sdir / f"{cid}.extxyz"
        qp = sdir / f"{cid}.in"
        write(sp, cand, format="extxyz")
        qp.write_text(qe_text(cand, cid, PHASE_INFO[phase]["k"], PHASE_INFO[phase]["spin"]))
        reread = read(sp)
        vals_d = reread.get_all_distances(mic=True)[np.triu_indices(len(reread), 1)]
        manifest_rows.append({
            "config_id": cid, "phase": phase, "config_family": kind, "target_role": "TRAIN",
            "strain_type": kind, "strain_or_shear_value": format(shear if kind.startswith("shear") else value, ".17g"),
            "rattle_sigma_A": rattle, "random_seed": seed if rattle > 0 else "NONE", "purpose": purpose,
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
        "# Round-213: Al3Ni2 shear-gap minimum + AlNi thin-bucket closure (design-only, NO DFT)",
        "", f"Generated UTC: {datetime.now(timezone.utc).isoformat()}", "",
        "## Al3Ni2 shear_xy_negative magnitude sweep (finding minimum that clears gate (a))", "",
        "| magnitude | status |", "|---|---|",
    ]
    for mag, status in sweep_results:
        lines.append(f"| {mag:.3f} | {status} |")
    passing = [m for m, s in sweep_results if s == "KEPT"]
    lines.append("")
    lines.append(f"Minimum passing magnitude: **{passing[0]:.3f}**" if passing else "**No magnitude in the sweep range passed.**")

    lines += ["", "## AlNi thin-bucket candidates", "",
              "| config_id | purpose | value | gate(a) | gate(c) | status |", "|---|---|---|---|---|---|"]
    for r in report_rows:
        if r["phase"] == "AlNi":
            lines.append(f"| {r['config_id']} | {r['purpose']} | {r['value']:.4f} | {r['gate_a']} | {r['gate_c']} | **{r['status']}** |")

    lines += ["", f"## Totals", "", f"Proposed: {len(report_rows)}", f"KEPT: {len(kept)}", "",
              "## Not done in this pass",
              "DFT has not been run. No merge into any TRAIN/VALIDATION split. Neither phase (AlNi, Al3Ni2)",
              "has any sealed data -- cfg109/cfg110 (Al3Ni-only) were never read, not even for geometry."]
    OUT_STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
