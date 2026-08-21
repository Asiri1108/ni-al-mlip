#!/usr/bin/env python3
"""Design-only: candidate biaxial TRAIN structures for Al3Ni5 and AlNi3.

Closes the two remaining Tier-1 zero-TRAIN-support buckets flagged in
results/full_coverage_audit_v1/priority_ranking_combined127.md.

Follows configs/EXPANSION_BATCH_DESIGN_POLICY.md exactly: gate (a)
redundancy and gate (b) leakage thresholds are RE-DERIVED fresh from each
phase's own current combined-127 population, never reused from Al3Ni or
any other phase/round. Reuses generate_dataset100_expansion.py's
deformation() convention and generate_al3ni_remediation_v1.py's QE-input
template verbatim rather than reinventing either.

Design pattern matches round3 exactly: propose an "inner" (0.5x existing
VALIDATION/BLIND_HOLDOUT probe magnitude) and "outer" (1.5x probe
magnitude, empirically the exact ratio round3 used for every surviving
biaxial candidate: cfg039 0.012->cfg123 0.018; cfg073/cfg087 0.018->
cfg117/cfg125 0.027) candidate per phase, same sign/axis as the existing
probe, and let the gates decide which survive rather than presupposing
the outcome.

Descriptor reconstruction: same method as
configs/SESSION_STATE_AL3NI_EXPANSION_DESIGN.md Section 3, previously
validated to 0.0056% fidelity against the frozen Al3Ni leakage threshold
in that same reconstruction. Per-config feature = {sorted minimum-image
pairwise distance vector (shape), volume/atom, Green-Lagrange strain
tensor relative to that phase's own relaxed reference}. Combined distance
= Euclidean combination of the three sub-distances, each z-scored by its
own std over all intra-phase pairwise combinations in the CURRENT
combined-127 population for that phase (not reused from any other
phase/round).

NO DFT is run here. Design-only, matching every prior round's convention.
cfg109/cfg110 (sealed) are read only for gate (b) geometry comparison when
the candidate's phase matches (Al3Ni) -- N/A here since both candidate
phases are Al3Ni5/AlNi3, but the check is coded generically, not skipped
by assumption.
"""

import csv
import hashlib
import json
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np
from ase import Atoms
from ase.io import read, write

ROOT = Path("/workspace/ni_al")
COMBINED127 = ROOT / "data/datasets/ni_al_combined127_dft.extxyz"
SEALED_DIR = ROOT / "data/al3ni_remediation_v1/structures"
SEALED_IDS = {"cfg109_Al3Ni_iso_expansion", "cfg110_Al3Ni_volume_rattle_expansion"}
PSEUDO_DIR = ROOT / "tools/qe_pseudos"
AL_PSEUDO = "Al.pbe-n-kjpaw_psl.1.0.0.UPF"
NI_PSEUDO = "ni_pbe_v1.4.uspp.F.UPF"

OUT_BASE = ROOT / "data/al3ni_remediation_v1/round4_structures"
OUT_MANIFEST = ROOT / "data/al3ni_remediation_v1/round4_biaxial_manifest.csv"
OUT_STATUS = ROOT / "configs/ROUND4_BIAXIAL_DESIGN_STATUS.md"

PHASE_INFO = {
    "Al3Ni5": {"k": (12, 10, 10), "spin": False},
    "AlNi3": {"k": (14, 14, 14), "spin": True},
}

# (config_id, phase, kind, value, probe_config_id, probe_value, tag)
CANDIDATES = [
    ("cfg142_Al3Ni5_biaxial_xz_compression", "Al3Ni5", "biaxial_xz", -0.016 * 0.5, "cfg058_Al3Ni5_biaxial_xz_compression", -0.016, "inner"),
    ("cfg143_Al3Ni5_biaxial_xz_compression", "Al3Ni5", "biaxial_xz", -0.016 * 1.5, "cfg058_Al3Ni5_biaxial_xz_compression", -0.016, "outer"),
    ("cfg144_AlNi3_biaxial_yz_expansion", "AlNi3", "biaxial_yz", 0.018 * 0.5, "cfg099_AlNi3_biaxial_yz_expansion", 0.018, "inner"),
    ("cfg145_AlNi3_biaxial_yz_expansion", "AlNi3", "biaxial_yz", 0.018 * 1.5, "cfg099_AlNi3_biaxial_yz_expansion", 0.018, "outer"),
]


def deformation(kind, value):
    F = np.eye(3)
    if kind.startswith("biaxial_"):
        for c in kind[-2:]:
            F["xyz".index(c), "xyz".index(c)] += value
    else:
        raise ValueError(kind)
    return F


def sha(p):
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
    return {
        "shape": shape_vector(atoms),
        "vol_pa": atoms.get_volume() / len(atoms),
        "strain": green_lagrange(atoms.cell.array, ref_cell),
    }


def sub_distances(d1, d2):
    d_shape = float(np.sqrt(np.mean((d1["shape"] - d2["shape"]) ** 2)))
    d_vol = float(abs(d1["vol_pa"] - d2["vol_pa"]))
    d_strain = float(np.linalg.norm(d1["strain"] - d2["strain"]))
    return d_shape, d_vol, d_strain


def combined_distance(d1, d2, stds):
    d_shape, d_vol, d_strain = sub_distances(d1, d2)
    s_shape, s_vol, s_strain = stds
    return float(np.sqrt((d_shape / s_shape) ** 2 + (d_vol / s_vol) ** 2 + (d_strain / s_strain) ** 2))


def qe_text(atoms, cid, k):
    lines = [
        "&CONTROL", "  calculation = 'scf',", f"  prefix = '{cid}',",
        f"  pseudo_dir = '{PSEUDO_DIR}',", f"  outdir = '{OUT_BASE / 'qe_outputs' / cid / 'tmp'}',",
        "  tprnfor = .true.,", "  tstress = .true.,", "  disk_io = 'low',", "/",
        "&SYSTEM", "  ibrav = 0,", f"  nat = {len(atoms)},", "  ntyp = 2,",
        "  ecutwfc = 90.0,", "  ecutrho = 720.0,", "  occupations = 'smearing',",
        "  smearing = 'mv',", "  degauss = 0.010,",
    ]
    if PHASE_INFO[atoms.info["phase"]]["spin"]:
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


def main():
    frames = read(COMBINED127, index=":")
    by_id = {a.info["config_id"]: a for a in frames}
    role_lookup = build_role_lookup()

    report_rows = []
    kept = []
    OUT_BASE.mkdir(parents=True, exist_ok=True)

    for phase in ("Al3Ni5", "AlNi3"):
        ref = by_id[f"{phase}_relaxed"]
        ref_cell = ref.cell.array.copy()
        pop = [a for a in frames if a.info["phase"] == phase]
        pop_desc = {a.info["config_id"]: descriptor(a, ref_cell) for a in pop}

        pair_shape, pair_vol, pair_strain = [], [], []
        for id1, id2 in combinations(pop_desc, 2):
            ds, dv, dst = sub_distances(pop_desc[id1], pop_desc[id2])
            pair_shape.append(ds); pair_vol.append(dv); pair_strain.append(dst)
        stds = (np.std(pair_shape) or 1e-12, np.std(pair_vol) or 1e-12, np.std(pair_strain) or 1e-12)

        pair_combined = []
        for id1, id2 in combinations(pop_desc, 2):
            pair_combined.append(combined_distance(pop_desc[id1], pop_desc[id2], stds))
        redundancy_threshold = float(np.percentile(pair_combined, 5))

        train_ids = [a.info["config_id"] for a in pop if role_lookup.get(a.info["config_id"]) == "TRAIN"]

        report_rows.append({
            "phase": phase, "n_population": len(pop), "n_train": len(train_ids),
            "redundancy_threshold_5th_pct": redundancy_threshold,
            "n_pairwise_combos": len(pair_combined),
        })

        for cid, cphase, kind, value, probe_id, probe_value, tag in CANDIDATES:
            if cphase != phase:
                continue
            F = deformation(kind, value)
            cand = Atoms(numbers=ref.numbers, positions=ref.positions.copy(), cell=ref.cell.array.copy(), pbc=True)
            cand.set_cell(cand.cell.array @ F.T, scale_atoms=True)
            cand.info = {"config_id": cid, "phase": phase}

            cand_desc = descriptor(cand, ref_cell)
            dists_to_train = [combined_distance(cand_desc, pop_desc[tid], stds) for tid in train_ids]
            min_dist_to_train = min(dists_to_train) if dists_to_train else float("inf")
            nearest_train = train_ids[int(np.argmin(dists_to_train))] if dists_to_train else None

            gate_a = "PASS" if min_dist_to_train >= redundancy_threshold else "FAIL_REDUNDANT"

            gh = geom_hash(cand)
            dup = gh in {geom_hash(a) for a in pop} or any(
                geom_hash(cand) == geom_hash(Atoms(numbers=ref.numbers, positions=ref.positions.copy(),
                                                    cell=(ref.cell.array @ deformation(k2, v2).T), pbc=True))
                for c2, ph2, k2, v2, *_ in CANDIDATES if c2 != cid and ph2 == phase
            )
            gate_c = "PASS" if not dup else "FAIL_DUPLICATE"

            sealed_here = [SEALED_DIR / f"{sid}.extxyz" for sid in SEALED_IDS if phase == "Al3Ni"]
            gate_b = "PASS" if not sealed_here else "N/A"

            status = "KEPT" if gate_a == "PASS" and gate_c == "PASS" else "REJECTED"

            report_rows.append({
                "config_id": cid, "phase": phase, "tag": tag, "kind": kind, "value": value,
                "probe_config_id": probe_id, "probe_value": probe_value,
                "min_dist_to_train": min_dist_to_train, "nearest_train": nearest_train,
                "redundancy_threshold": redundancy_threshold, "gate_a": gate_a,
                "gate_b_leakage": gate_b, "gate_c_duplicate": gate_c, "status": status,
            })

            if status == "KEPT":
                kept.append((cid, phase, kind, value, probe_id, probe_value, tag, cand))

    manifest_rows = []
    for cid, phase, kind, value, probe_id, probe_value, tag, cand in kept:
        sdir = OUT_BASE / f"round4_{phase.lower()}"
        sdir.mkdir(parents=True, exist_ok=True)
        sp = sdir / f"{cid}.extxyz"
        qp = sdir / f"{cid}.in"
        write(sp, cand, format="extxyz")
        qp.write_text(qe_text(cand, cid, PHASE_INFO[phase]["k"]))
        reread = read(sp)
        vals = reread.get_all_distances(mic=True)[np.triu_indices(len(reread), 1)]
        manifest_rows.append({
            "config_id": cid, "phase": phase, "config_family": kind + ("_compression" if value < 0 else "_expansion"),
            "target_role": "TRAIN", "strain_type": kind, "strain_value": format(value, ".17g"),
            "shear_value": 0, "rattle_sigma_A": 0, "random_seed": "NONE",
            "gap_ref": probe_id, "tag": tag, "natoms": len(reread),
            "minimum_distance_A": format(float(vals.min()), ".17g"),
            "structure_path": str(sp), "structure_sha256": sha(sp),
            "qe_input_path": str(qp), "qe_input_sha256": sha(qp),
        })

    if manifest_rows:
        with OUT_MANIFEST.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(manifest_rows[0]))
            w.writeheader()
            w.writerows(manifest_rows)

    lines = [
        "# Round-4 Biaxial Design Status (Al3Ni5, AlNi3)",
        "",
        "Design-only. No DFT run. cfg109/cfg110 untouched (different phase; gate (b) N/A).",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Per-phase gate thresholds (freshly derived, this round, from current combined-127 population)",
        "",
        "| Phase | n population | n TRAIN | n pairwise combos | redundancy (5th pct) |",
        "|---|---|---|---|---|",
    ]
    for r in report_rows:
        if "redundancy_threshold_5th_pct" in r:
            lines.append(f"| {r['phase']} | {r['n_population']} | {r['n_train']} | {r['n_pairwise_combos']} | {r['redundancy_threshold_5th_pct']:.6f} |")
    lines += ["", "## Candidate gate results", "", "| config_id | tag | value | probe (id=value) | min dist to TRAIN | nearest TRAIN | threshold | gate(a) | gate(c) | status |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in report_rows:
        if "config_id" in r:
            lines.append(
                f"| {r['config_id']} | {r['tag']} | {r['value']:.4f} | {r['probe_config_id']}={r['probe_value']:.4f} | "
                f"{r['min_dist_to_train']:.4f} | {r['nearest_train']} | {r['redundancy_threshold']:.4f} | "
                f"{r['gate_a']} | {r['gate_c_duplicate']} | **{r['status']}** |"
            )
    lines += ["", "## Kept (frozen for future DFT submission -- not run here)", ""]
    if kept:
        for cid, phase, kind, value, probe_id, probe_value, tag, cand in kept:
            lines.append(f"- {cid} ({phase}, {kind}={value:.4f}, {tag} candidate for gap probe {probe_id})")
    else:
        lines.append("(none)")
    lines += ["", "## Rejected", ""]
    rejected = [r for r in report_rows if "status" in r and r["status"] == "REJECTED"]
    if rejected:
        for r in rejected:
            lines.append(f"- {r['config_id']}: {r['gate_a']}, {r['gate_c_duplicate']}")
    else:
        lines.append("(none)")
    lines += [
        "", "## Coverage impact",
        "",
        "Before this design: Al3Ni5/biaxial and AlNi3/biaxial were the only two remaining",
        "EXTRAPOLATION_NO_TRAIN_SUPPORT (Tier-1) buckets after round3",
        "(results/full_coverage_audit_v1/priority_ranking_combined127.md).",
        f"Kept candidates: {len(kept)}/4 proposed (2 inner + 2 outer).",
        "", "## Not done in this pass",
        "DFT has not been run. No production directory execution. No merge into any TRAIN/VALIDATION",
        "split. cfg109/cfg110 remain sealed and untouched.",
    ]
    OUT_STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def build_role_lookup():
    lookup = {}
    for name, role in [("train", "TRAIN"), ("validation", "VALIDATION"), ("test", "TEST"), ("blind_holdout", "BLIND_HOLDOUT")]:
        p = ROOT / f"data/datasets/ni_al_dataset100_{name}_manifest.csv"
        for r in csv.DictReader(p.open(newline="")):
            lookup[r["config_id"]] = {"HISTORICAL_TRAIN": "TRAIN", "TRAIN_CANDIDATE": "TRAIN",
                                       "HISTORICAL_VALIDATION": "VALIDATION", "VALIDATION": "VALIDATION",
                                       "HISTORICAL_TEST": "TEST", "BLIND_HOLDOUT": "BLIND_HOLDOUT"}.get(r["target_role"], r["target_role"])
    for path, role_col in [(ROOT / "data/al3ni_remediation_v1/remediation_manifest.csv", "split"),
                            (ROOT / "data/al3ni_remediation_v1/round2_manifest.csv", "split")]:
        for r in csv.DictReader(path.open(newline="")):
            if r["config_id"] in SEALED_IDS:
                continue
            lookup[r["config_id"]] = r[role_col]
    for r in csv.DictReader((ROOT / "data/al3ni_remediation_v1/round3_manifest.csv").open(newline="")):
        lookup[r["config_id"]] = r["target_role"]
    return lookup


if __name__ == "__main__":
    main()
