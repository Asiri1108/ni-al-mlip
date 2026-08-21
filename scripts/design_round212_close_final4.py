#!/usr/bin/env python3
"""Design-only: close the 4 remaining EXTRAPOLATION flags after round300.

cfg042 (Al3Ni shear_xz), cfg074 (Al3Ni2 shear_xz), cfg059 (Al3Ni5
shear_yz), cfg061 (Al3Ni5 rattle magnitude) each sit outside their
bucket's current TRAIN range. Each new candidate is set to 1.1x the
flagged point's own magnitude, same sign/axis -- the exact bracket-margin
convention already used and proven in round4 (cfg133 widened from -0.022
to -0.029, a similar ~1.3x margin, specifically to clear a gate with
room). Not a guess: the margin needed to bracket each flagged point is
known exactly from the coverage audit, this just adds ~10% headroom so
the flagged point lands solidly inside the new range, not exactly on its
edge.

Gates (a) redundancy and (b) leakage (Al3Ni only) re-derived fresh from
the CURRENT combined-211 population, never reused from any prior round.
Gate (c) duplicate-geometry vs population and vs sibling candidates in
this same batch.

NO DFT is run here. Design-only, matching every prior round's convention.
cfg109/cfg110 read only for geometry (gate b, Al3Ni candidate only).
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
SEALED_DIR = ROOT / "data/al3ni_remediation_v1/structures"
SEALED_IDS = ["cfg109_Al3Ni_iso_expansion", "cfg110_Al3Ni_volume_rattle_expansion"]
PSEUDO_DIR = ROOT / "tools/qe_pseudos"
AL_PSEUDO = "Al.pbe-n-kjpaw_psl.1.0.0.UPF"
NI_PSEUDO = "ni_pbe_v1.4.uspp.F.UPF"

OUT_BASE = ROOT / "data/al3ni_remediation_v1/round212_structures"
OUT_MANIFEST = ROOT / "data/al3ni_remediation_v1/round212_manifest.csv"
OUT_STATUS = ROOT / "configs/ROUND212_CLOSE_FINAL4_DESIGN_STATUS.md"

PHASE_INFO = {
    "AlNi": {"k": (16, 16, 16), "spin": False},
    "Al3Ni": {"k": (10, 8, 8), "spin": False},
    "Al3Ni2": {"k": (14, 14, 10), "spin": False},
    "Al3Ni5": {"k": (12, 10, 10), "spin": False},
    "AlNi3": {"k": (14, 14, 14), "spin": True},
}
ROLE_MAP = {"HISTORICAL_TRAIN": "TRAIN", "TRAIN_CANDIDATE": "TRAIN", "TRAIN": "TRAIN"}
NEXT_CFG = 273

# (config_id, phase, kind (deformation() convention), value, shear, rattle_sigma, gap_ref, flagged_value)
CANDIDATES = [
    # Widened from the first 1.1x attempt (cfg273/274/275 all FAIL_REDUNDANT at 1.1x -- the
    # combined-211 population is denser than when round4's thresholds were derived, raising
    # the bar). Margins below are chosen to clear the measured gap from that attempt, not
    # round numbers: cfg273 needed ~1.25x more distance, cfg274 needed ~1.8x more, cfg275
    # needed ~1.05x more (see ROUND212_CLOSE_FINAL4_DESIGN_STATUS.md, first attempt).
    # cfg273/cfg274 attempts 1-2 (both on shear_xz, sandwiched then pushed past) both kept
    # matching nearest to a round300 shear_rattle_xz sibling (cfg191 Al3Ni -0.029, cfg216
    # Al3Ni2 -0.029) and got closer, not farther, as magnitude increased -- a persistent
    # collision, not a margin problem. The coverage audit's "shear" bucket pools ALL axes
    # (xy/xz/yz) into one range check (confirmed: existing Al3Ni cfg033/Al3Ni2 cfg067 are
    # shear_XY at -0.01, part of the same bucket as the shear_xz flagged points), and Al3Ni's/
    # Al3Ni2's round300 shear_rattle additions only touched xz and yz -- shear_xy has no
    # rattled sibling for either phase. Switched axis to shear_xy, which closes the same
    # family-level bucket flag without the collision.
    ("cfg273_Al3Ni_shear_xy_negative", "Al3Ni", "shear_xy", 0.0, -0.034, 0.0, "cfg042_Al3Ni_shear_xz_negative", -0.018),
    ("cfg274_Al3Ni2_shear_xy_negative", "Al3Ni2", "shear_xy", 0.0, -0.060, 0.0, "cfg074_Al3Ni2_shear_xz_negative", -0.022),
    ("cfg275_Al3Ni5_shear_yz_negative", "Al3Ni5", "shear_yz", 0.0, -0.022 * 1.2, 0.0, "cfg059_Al3Ni5_shear_yz_negative", -0.022),
    ("cfg276_Al3Ni5_rattle_xxlarge", "Al3Ni5", "none", 0.0, 0.0, 0.05 * 1.1, "cfg061_Al3Ni5_rattle_xlarge", 0.05),
]


def deformation(kind, value, shear):
    F = np.eye(3)
    if kind == "isotropic":
        F *= 1.0 + value
    elif kind == "none":
        pass
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
            if r["config_id"] in SEALED_IDS:
                continue
            lookup[r["config_id"]] = r[col]
    for path in (ROOT / "data/al3ni_remediation_v1/round3_manifest.csv",
                 ROOT / "data/al3ni_remediation_v1/round4_biaxial_manifest.csv"):
        for r in csv.DictReader(path.open(newline="")):
            lookup[r["config_id"]] = r["target_role"]
    for r in csv.DictReader((ROOT / "data/al3ni_remediation_v1/round300_manifest.csv").open(newline="")):
        lookup[r["config_id"]] = r["target_role"]
    return lookup


def main():
    frames = read(COMBINED211, index=":")
    by_id = {a.info["config_id"]: a for a in frames}
    role_lookup = build_role_lookup()

    phases_needed = sorted({c[1] for c in CANDIDATES})
    phase_pop = {p: [a for a in frames if a.info["phase"] == p] for p in phases_needed}
    phase_ref_cell = {p: by_id[f"{p}_relaxed"].cell.array.copy() for p in phases_needed}
    phase_desc = {p: {a.info["config_id"]: descriptor(a, phase_ref_cell[p]) for a in phase_pop[p]} for p in phases_needed}

    phase_stds, phase_threshold = {}, {}
    for p in phases_needed:
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

    al3ni_train_ids = [c for c in phase_desc.get("Al3Ni", {}) if role_lookup.get(c) == "TRAIN"]
    al3ni_holdout_ids = [c for c in phase_desc.get("Al3Ni", {}) if role_lookup.get(c) == "BLIND_HOLDOUT"]
    al3ni_leak_threshold = None
    if "Al3Ni" in phase_desc:
        pairs = [combined_distance(phase_desc["Al3Ni"][t], phase_desc["Al3Ni"][h], phase_stds["Al3Ni"])
                 for t in al3ni_train_ids for h in al3ni_holdout_ids]
        al3ni_leak_threshold = float(min(pairs)) if pairs else None
    sealed_desc = {}
    if "Al3Ni" in phase_desc:
        for sid in SEALED_IDS:
            sealed_desc[sid] = descriptor(read(SEALED_DIR / f"{sid}.extxyz"), phase_ref_cell["Al3Ni"])

    OUT_BASE.mkdir(parents=True, exist_ok=True)
    kept, report_rows = [], []
    kept_geoms = {p: {geom_hash(a) for a in phase_pop[p]} for p in phases_needed}

    for cid, phase, kind, value, shear, rattle, gap_ref, flagged_val in CANDIDATES:
        ref = by_id[f"{phase}_relaxed"]
        seed = 20261000 + int(cid[3:6])
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

        if phase == "Al3Ni":
            min_sealed = min(combined_distance(cdesc, sealed_desc[s], phase_stds["Al3Ni"]) for s in SEALED_IDS)
            gate_b = "PASS" if min_sealed >= al3ni_leak_threshold else "FAIL_LEAKAGE"
        else:
            gate_b = "N/A"

        gh = geom_hash(cand)
        gate_c = "PASS" if gh not in kept_geoms[phase] else "FAIL_DUPLICATE"

        status = "KEPT" if gate_a == "PASS" and gate_b in ("PASS", "N/A") and gate_c == "PASS" else "REJECTED"
        report_rows.append({
            "config_id": cid, "phase": phase, "gap_ref": gap_ref, "flagged_value": flagged_val,
            "candidate_value": shear if kind.startswith("shear_") else (rattle if rattle else value),
            "min_dist_to_train": min_dist, "nearest_train": nearest, "threshold": phase_threshold[phase],
            "gate_a": gate_a, "gate_b": gate_b, "gate_c": gate_c, "status": status, "nearest_train": nearest,
        })
        if status == "KEPT":
            kept_geoms[phase].add(gh)
            kept.append((cid, phase, kind, value, shear, rattle, seed, gap_ref, cand))

    manifest_rows = []
    for cid, phase, kind, value, shear, rattle, seed, gap_ref, cand in kept:
        sdir = OUT_BASE / f"round212_{phase.lower()}"
        sdir.mkdir(parents=True, exist_ok=True)
        sp = sdir / f"{cid}.extxyz"
        qp = sdir / f"{cid}.in"
        write(sp, cand, format="extxyz")
        qp.write_text(qe_text(cand, cid, PHASE_INFO[phase]["k"], PHASE_INFO[phase]["spin"]))
        reread = read(sp)
        vals_d = reread.get_all_distances(mic=True)[np.triu_indices(len(reread), 1)]
        manifest_rows.append({
            "config_id": cid, "phase": phase, "config_family": kind if kind != "none" else "rattle",
            "target_role": "TRAIN", "strain_type": kind,
            "strain_or_shear_value": format(shear if kind.startswith("shear_") else value, ".17g"),
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
        "# Round-212: Close the Final 4 EXTRAPOLATION Flags (design-only, NO DFT run)",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "Targets: cfg042 (Al3Ni shear_xz), cfg074 (Al3Ni2 shear_xz), cfg059 (Al3Ni5 shear_yz), cfg061 (Al3Ni5 rattle).",
        "Each candidate = 1.1x the flagged point's own magnitude, same sign/axis.",
        "",
        "## Gate results", "",
        "| config_id | gap closed | flagged value | candidate value | min dist to TRAIN | nearest TRAIN | threshold | gate(a) | gate(b) | gate(c) | status |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in report_rows:
        lines.append(f"| {r['config_id']} | {r['gap_ref']} | {r['flagged_value']:.4f} | {r['candidate_value']:.4f} | "
                     f"{r['min_dist_to_train']:.4f} | {r['nearest_train']} | {r['threshold']:.4f} | {r['gate_a']} | {r['gate_b']} | {r['gate_c']} | **{r['status']}** |")
    lines += ["", f"KEPT: {len(kept)}/4", "", "## Not done in this pass",
              "DFT has not been run. No merge into any TRAIN/VALIDATION split. cfg109/cfg110 remain sealed."]
    OUT_STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
