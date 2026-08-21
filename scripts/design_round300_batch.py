#!/usr/bin/env python3
"""Generate and gate-check (NOT DFT) the 300-round scope roster.

Reads data/al3ni_remediation_v1/round300_scope_roster.csv (128 candidates,
from scripts/scope_round300_design.py) and, for each, builds the deformed
structure via the exact deformation()/PHASE_INFO convention from
generate_dataset100_expansion.py, then runs the same descriptor-based
gates as design_round4_biaxial_al3ni5_alni3.py: gate (a) redundancy vs
each phase's current TRAIN population (threshold re-derived fresh per
phase from combined-129, never reused from a prior round/phase), gate (b)
leakage vs sealed cfg109/cfg110 (Al3Ni candidates only -- the only phase
with sealed points; threshold re-derived from Al3Ni's current TRAIN-vs-
BLIND_HOLDOUT population, not reused from the frozen 0.734644), and gate
(c) duplicate-geometry vs the existing population AND vs every other KEPT
candidate in this same batch (this run proposes far more candidates per
phase at once than any prior round, so intra-batch collision is a real
risk gate (c) must catch that round3/round4 didn't need to).

Gate (d) (VALIDATION placement) does not apply -- every candidate here is
TRAIN role, matching every round since v1.

Writes structures + QE inputs ONLY for candidates that pass every
applicable gate. Does NOT run DFT. cfg109/cfg110 are read only for
geometry (gate b for Al3Ni candidates) -- labels never touched.
"""

import csv
import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np
from ase import Atoms
from ase.io import read, write

ROOT = Path("/workspace/ni_al")
COMBINED129 = ROOT / "data/datasets/ni_al_combined129_dft.extxyz"
ROSTER_CSV = ROOT / "data/al3ni_remediation_v1/round300_scope_roster.csv"
SEALED_DIR = ROOT / "data/al3ni_remediation_v1/structures"
SEALED_IDS = ["cfg109_Al3Ni_iso_expansion", "cfg110_Al3Ni_volume_rattle_expansion"]
PSEUDO_DIR = ROOT / "tools/qe_pseudos"
AL_PSEUDO = "Al.pbe-n-kjpaw_psl.1.0.0.UPF"
NI_PSEUDO = "ni_pbe_v1.4.uspp.F.UPF"

OUT_BASE = ROOT / "data/al3ni_remediation_v1/round300_structures"
OUT_MANIFEST = ROOT / "data/al3ni_remediation_v1/round300_manifest.csv"
OUT_STATUS = ROOT / "configs/ROUND300_DESIGN_STATUS.md"
GATE_REPORT_CSV = ROOT / "data/al3ni_remediation_v1/round300_gate_report.csv"

NEXT_CFG_START = 146  # highest existing is cfg145 (round4)

PHASE_INFO = {
    "AlNi": {"k": (16, 16, 16), "spin": False},
    "Al3Ni": {"k": (10, 8, 8), "spin": False},
    "Al3Ni2": {"k": (14, 14, 10), "spin": False},
    "Al3Ni5": {"k": (12, 10, 10), "spin": False},
    "AlNi3": {"k": (14, 14, 14), "spin": True},
}

ROLE_MAP = {"HISTORICAL_TRAIN": "TRAIN", "TRAIN_CANDIDATE": "TRAIN", "TRAIN": "TRAIN",
            "HISTORICAL_VALIDATION": "VALIDATION", "VALIDATION": "VALIDATION",
            "HISTORICAL_TEST": "TEST", "BLIND_HOLDOUT": "BLIND_HOLDOUT"}


def deformation(kind, value, shear):
    F = np.eye(3)
    if kind == "isotropic":
        F *= 1.0 + value
    elif kind == "none":
        pass
    elif kind.startswith("uniaxial_"):
        F["xyz".index(kind[-1]), "xyz".index(kind[-1])] += value
    elif kind.startswith("biaxial_"):
        for c in kind[-2:]:
            F["xyz".index(c), "xyz".index(c)] += value
    elif kind.startswith("orthorhombic_"):
        a, b = kind[-2:]
        F["xyz".index(a), "xyz".index(a)] += value
        F["xyz".index(b), "xyz".index(b)] -= value
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
    for name, _ in [("train", "TRAIN"), ("validation", "VALIDATION"), ("test", "TEST"), ("blind_holdout", "BLIND_HOLDOUT")]:
        p = ROOT / f"data/datasets/ni_al_dataset100_{name}_manifest.csv"
        for r in csv.DictReader(p.open(newline="")):
            lookup[r["config_id"]] = ROLE_MAP.get(r["target_role"], r["target_role"])
    for path, role_col in [(ROOT / "data/al3ni_remediation_v1/remediation_manifest.csv", "split"),
                            (ROOT / "data/al3ni_remediation_v1/round2_manifest.csv", "split")]:
        for r in csv.DictReader(path.open(newline="")):
            if r["config_id"] in SEALED_IDS:
                continue
            lookup[r["config_id"]] = r[role_col]
    for path in (ROOT / "data/al3ni_remediation_v1/round3_manifest.csv",
                 ROOT / "data/al3ni_remediation_v1/round4_biaxial_manifest.csv"):
        for r in csv.DictReader(path.open(newline="")):
            lookup[r["config_id"]] = r["target_role"]
    return lookup


def main():
    frames = read(COMBINED129, index=":")
    by_id = {a.info["config_id"]: a for a in frames}
    roster = list(csv.DictReader(ROSTER_CSV.open(newline="")))
    role_lookup = build_role_lookup()

    phase_pop = {phase: [a for a in frames if a.info["phase"] == phase] for phase in PHASE_INFO}
    phase_ref_cell = {phase: by_id[f"{phase}_relaxed"].cell.array.copy() for phase in PHASE_INFO}
    phase_desc = {phase: {a.info["config_id"]: descriptor(a, phase_ref_cell[phase]) for a in phase_pop[phase]}
                  for phase in PHASE_INFO}

    phase_stds, phase_threshold = {}, {}
    for phase in PHASE_INFO:
        pop_desc = phase_desc[phase]
        pairs = list(combinations(pop_desc, 2))
        pair_shape, pair_vol, pair_strain = [], [], []
        for id1, id2 in pairs:
            ds, dv, dst = sub_distances(pop_desc[id1], pop_desc[id2])
            pair_shape.append(ds); pair_vol.append(dv); pair_strain.append(dst)
        stds = (np.std(pair_shape) or 1e-12, np.std(pair_vol) or 1e-12, np.std(pair_strain) or 1e-12)
        phase_stds[phase] = stds
        pair_combined = [combined_distance(pop_desc[id1], pop_desc[id2], stds) for id1, id2 in pairs]
        phase_threshold[phase] = float(np.percentile(pair_combined, 5))

    # Gate (b), Al3Ni only: re-derive leakage threshold fresh from CURRENT Al3Ni
    # TRAIN-vs-BLIND_HOLDOUT population (same method as the frozen 0.734644, not reused verbatim).
    al3ni_train_ids = [cid for cid in phase_desc["Al3Ni"] if role_lookup.get(cid) == "TRAIN"]
    al3ni_holdout_ids = [cid for cid in phase_desc["Al3Ni"] if role_lookup.get(cid) == "BLIND_HOLDOUT"]
    al3ni_leak_pairs = [combined_distance(phase_desc["Al3Ni"][t], phase_desc["Al3Ni"][h], phase_stds["Al3Ni"])
                         for t in al3ni_train_ids for h in al3ni_holdout_ids]
    al3ni_leak_threshold = float(min(al3ni_leak_pairs)) if al3ni_leak_pairs else None

    sealed_desc = {sid: descriptor(read(SEALED_DIR / f"{sid}.extxyz"), phase_ref_cell["Al3Ni"]) for sid in SEALED_IDS}
    sealed_geoms = {sid: geom_hash(read(SEALED_DIR / f"{sid}.extxyz")) for sid in SEALED_IDS}

    OUT_BASE.mkdir(parents=True, exist_ok=True)
    cfg_counter = NEXT_CFG_START
    kept_geoms_by_phase = defaultdict(set)
    for phase in PHASE_INFO:
        kept_geoms_by_phase[phase] |= {geom_hash(a) for a in phase_pop[phase]}

    gate_rows, manifest_rows, kept = [], [], []

    for row in roster:
        phase = row["phase"]
        st = row["strain_type"]
        val = float(row["strain_or_shear_value"])
        rattle = float(row["rattle_sigma_A"])
        family = row["family"]

        ref = by_id[f"{phase}_relaxed"]
        seed = 20261000 + cfg_counter
        if st.startswith("shear"):
            F = deformation(st, 0.0, val)
        else:
            F = deformation(st, val, 0.0)

        cand = Atoms(numbers=ref.numbers, positions=ref.positions.copy(), cell=ref.cell.array.copy(), pbc=True)
        cand.set_cell(cand.cell.array @ F.T, scale_atoms=True)
        if rattle > 0:
            rng = np.random.default_rng(seed)
            disp = rng.normal(0, rattle, (len(cand), 3))
            disp -= disp.mean(axis=0)
            cand.positions += disp
            cand.wrap()

        sign_word = {"pos": "positive" if family in ("shear", "shear_rattle") else "expansion",
                     "neg": "negative" if family in ("shear", "shear_rattle") else "compression",
                     "n/a": ""}[row["sign"]]
        axis_tag = st.split("_", 1)[1] if "_" in st and st != "none" else ""
        name_parts = [p for p in [family, axis_tag, sign_word] if p]
        cid = f"cfg{cfg_counter}_{phase}_{'_'.join(name_parts)}"
        cand.info = {"config_id": cid, "phase": phase}

        cdesc = descriptor(cand, phase_ref_cell[phase])

        train_ids = [c for c in phase_desc[phase] if role_lookup.get(c) == "TRAIN"]
        dists = [combined_distance(cdesc, phase_desc[phase][t], phase_stds[phase]) for t in train_ids]
        min_dist = min(dists) if dists else float("inf")
        nearest = train_ids[int(np.argmin(dists))] if dists else None
        gate_a = "PASS" if min_dist >= phase_threshold[phase] else "FAIL_REDUNDANT"

        if phase == "Al3Ni":
            sealed_dists = {sid: combined_distance(cdesc, sealed_desc[sid], phase_stds["Al3Ni"]) for sid in SEALED_IDS}
            min_sealed = min(sealed_dists.values())
            gate_b = "PASS" if min_sealed >= al3ni_leak_threshold else "FAIL_LEAKAGE"
        else:
            gate_b = "N/A"

        gh = geom_hash(cand)
        gate_c = "PASS" if gh not in kept_geoms_by_phase[phase] and gh not in sealed_geoms.values() else "FAIL_DUPLICATE"

        status = "KEPT" if gate_a == "PASS" and gate_b in ("PASS", "N/A") and gate_c == "PASS" else "REJECTED"

        gate_rows.append({
            "config_id": cid, "phase": phase, "family": family, "strain_type": st, "value": val,
            "rattle_sigma_A": rattle, "magnitude_source": row["magnitude_source"],
            "min_dist_to_train": min_dist, "nearest_train": nearest, "redundancy_threshold": phase_threshold[phase],
            "gate_a": gate_a, "leakage_threshold": al3ni_leak_threshold if phase == "Al3Ni" else "",
            "gate_b": gate_b, "gate_c": gate_c, "status": status,
        })

        if status == "KEPT":
            kept_geoms_by_phase[phase].add(gh)
            kept.append((cid, phase, family, st, val, rattle, seed, cand, row["magnitude_source"]))
        cfg_counter += 1

    for cid, phase, family, st, val, rattle, seed, cand, mag_source in kept:
        sdir = OUT_BASE / f"round300_{phase.lower()}"
        sdir.mkdir(parents=True, exist_ok=True)
        sp = sdir / f"{cid}.extxyz"
        qp = sdir / f"{cid}.in"
        write(sp, cand, format="extxyz")
        qp.write_text(qe_text(cand, cid, PHASE_INFO[phase]["k"], PHASE_INFO[phase]["spin"]))
        reread = read(sp)
        vals_d = reread.get_all_distances(mic=True)[np.triu_indices(len(reread), 1)]
        manifest_rows.append({
            "config_id": cid, "phase": phase, "config_family": family, "target_role": "TRAIN",
            "strain_type": st, "strain_or_shear_value": format(val, ".17g"), "rattle_sigma_A": rattle,
            "random_seed": seed if rattle > 0 else "NONE", "magnitude_source": mag_source,
            "natoms": len(reread), "minimum_distance_A": format(float(vals_d.min()), ".17g"),
            "structure_path": str(sp), "structure_sha256": sha256(sp),
            "qe_input_path": str(qp), "qe_input_sha256": sha256(qp),
        })

    if manifest_rows:
        with OUT_MANIFEST.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(manifest_rows[0]))
            w.writeheader()
            w.writerows(manifest_rows)

    with GATE_REPORT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(gate_rows[0]))
        w.writeheader()
        w.writerows(gate_rows)

    by_phase_kept = defaultdict(int)
    by_phase_total = defaultdict(int)
    by_family_kept = defaultdict(int)
    fail_a = fail_b = fail_c = 0
    for r in gate_rows:
        by_phase_total[r["phase"]] += 1
        if r["status"] == "KEPT":
            by_phase_kept[r["phase"]] += 1
            by_family_kept[r["family"]] += 1
        if r["gate_a"] == "FAIL_REDUNDANT":
            fail_a += 1
        if r["gate_b"] == "FAIL_LEAKAGE":
            fail_b += 1
        if r["gate_c"] == "FAIL_DUPLICATE":
            fail_c += 1

    lines = [
        "# Round-300 Batch: Generated and Gate-Checked (design-only, NO DFT run)",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"Source roster: {ROSTER_CSV} ({len(roster)} proposed)",
        "cfg109/cfg110 (sealed): geometry-only read for gate (b), Al3Ni candidates only. Labels never touched.",
        "",
        "## Per-phase gate thresholds (freshly derived this round, from current combined-129 population)",
        "",
        "| Phase | n population | n TRAIN | redundancy threshold (5th pct) | leakage threshold (Al3Ni only) |",
        "|---|---|---|---|---|",
    ]
    for phase in PHASE_INFO:
        leak = f"{al3ni_leak_threshold:.6f}" if phase == "Al3Ni" else "N/A"
        lines.append(f"| {phase} | {len(phase_pop[phase])} | {sum(1 for c in phase_desc[phase] if role_lookup.get(c)=='TRAIN')} | {phase_threshold[phase]:.6f} | {leak} |")

    lines += [
        "",
        "## Results",
        "",
        f"Proposed: {len(roster)}",
        f"KEPT: {sum(by_phase_kept.values())}",
        f"REJECTED: {len(roster) - sum(by_phase_kept.values())}",
        f"  - failed gate (a) redundancy: {fail_a}",
        f"  - failed gate (b) leakage: {fail_b}",
        f"  - failed gate (c) duplicate: {fail_c}",
        "",
        "## Per-phase kept/proposed",
        "",
        "| Phase | Kept | Proposed |",
        "|---|---|---|",
    ]
    for phase in PHASE_INFO:
        lines.append(f"| {phase} | {by_phase_kept[phase]} | {by_phase_total[phase]} |")
    lines += ["", "## Per-family kept", "", "| Family | Kept |", "|---|---|"]
    for fam in sorted(by_family_kept):
        lines.append(f"| {fam} | {by_family_kept[fam]} |")

    current_total = 131
    projected = current_total + len(kept)
    lines += [
        "",
        "## Sizing outcome",
        "",
        f"Current project total: {current_total}",
        f"KEPT this round: {len(kept)}",
        f"Projected total if DFT'd and merged: {current_total} + {len(kept)} = **{projected}** ({projected/300*100:.0f}% of the 300 milestone)",
        "",
        "## What this does NOT do",
        "",
        "- Does NOT run DFT. Structures and QE inputs are frozen and ready, not submitted.",
        "- Does NOT merge anything into any TRAIN/VALIDATION file.",
        "- cfg109/cfg110 remain sealed; only geometry was read for gate (b) (Al3Ni candidates only).",
        "",
        f"Full per-candidate gate results: `{GATE_REPORT_CSV}`",
        f"Frozen manifest (KEPT only): `{OUT_MANIFEST}`",
    ]
    OUT_STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
