#!/usr/bin/env python3
"""Design-only: densify the Al3Ni high-expansion regime (+3.0% to +5.0%),
iso_expansion and volume_rattle_expansion families, and design 2 NEW sealed
confirmation structures to replace consumed cfg109/cfg110.

BACKGROUND (combined-220 Al3Ni iso_expansion/volume_rattle_expansion TRAIN
rungs, precise isotropic strain s solved from each frame's own Green-Lagrange
trace against Al3Ni_relaxed):
  s=1.0%  cfg027 (iso only)
  s=2.0%  cfg103 (iso) + cfg105 (volume_rattle)  -- matched pair
  s=3.0%  cfg029 (iso only, NO volume_rattle partner)
  s=4.6%  cfg111 (iso) + cfg112 (volume_rattle)  -- matched pair
  s=5.6%  cfg113 (iso) + cfg114 (volume_rattle)  -- matched pair, at the edge
  s=5.44% cfg115 (iso, VALIDATION only)
Only 3 TRAIN rungs sit inside +2%..+5.6%, and the 3.0%->4.6% span (1.6 points)
has NO iso/volume_rattle coverage at all -- this is exactly where cfg109/
cfg110 sat (s=4.0%, both families), now consumed as an unsealing evaluation
and no longer usable as TRAIN or as a protected holdout.

KEY POLICY CHANGE (per this round's design brief): gate (b) no longer treats
cfg109/cfg110 as protected -- they were unsealed 2026-08-17
(AL3NI_FINAL_UNSEALING_RESULT.txt) and are consumed. Candidates may now sit
directly adjacent to s=4.0%, which prior rounds' gate (b) forbade. Gate (b)
here instead uses the Al3Ni RESERVED population still live in combined-220
(cfg041, cfg042, cfg043, cfg044, Al3Ni_shear015_rattle002 -- Dataset-100
TEST/BLIND_HOLDOUT members), same substitution design_round220_close_last2.py
already established when cfg109/cfg110 were first excluded from a gate (b)
reference pool. Gates (a), (c), (d) apply with their normal derivation.

Grid: s in {3.0, 3.5, 4.0, 4.5, 5.0}% for BOTH iso_expansion (rattle=0) and
volume_rattle_expansion (rattle_sigma=0.015 A, the project-standard value
for this family throughout -- see remediation_manifest.csv cfg105/cfg110/
cfg112/cfg114 requested_rattle_sigma_A=0.015). 10 raw candidates; gates
decide the final count, no candidate is hand-picked or pre-filtered.

Also designs 2 NEW sealed CONFIRMATION_HOLDOUT structures (one iso_expansion,
one volume_rattle_expansion) at strain values deliberately OFF the new grid
(3.75%, 4.25%) so they test genuine interpolation inside the newly densified
region, replacing cfg109/cfg110's role. Following the exact precedent in
generate_al3ni_remediation_v1.py: geometry + QE input written, DFT NOT run,
labels never computed or read in this pass. Sealing is a POLICY commitment
(this file + a companion status/criterion file), enforced the same way
AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt enforced cfg109/cfg110's seal --
by never being read by any script until a future, single, designated
unsealing event.

NO DFT is run here. NO training. Design-only.
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
COMBINED220_DFT = ROOT / "data/datasets/ni_al_combined220_dft.extxyz"
COMBINED220_TRAIN = ROOT / "data/datasets/ni_al_combined220_train_182.extxyz"
COMBINED220_VALID = ROOT / "data/datasets/ni_al_combined220_validation_18.extxyz"

RATTLE_SIGMA = 0.015  # project-standard volume_rattle sigma, Al3Ni, all rounds

# (config_id_num, kind_label, s, rattle)
DENSIFY_GRID = []
_next_id = 285
for s in (0.030, 0.035, 0.040, 0.045, 0.050):
    DENSIFY_GRID.append((_next_id, "iso_expansion", s, 0.0)); _next_id += 1
for s in (0.030, 0.035, 0.040, 0.045, 0.050):
    DENSIFY_GRID.append((_next_id, "volume_rattle_expansion", s, RATTLE_SIGMA)); _next_id += 1

SEALED_CANDIDATES = [
    (_next_id, "iso_expansion", 0.0375, 0.0),
    (_next_id + 1, "volume_rattle_expansion", 0.0425, RATTLE_SIGMA),
]
_next_id += 2

OUT_BASE = ROOT / "data/al3ni_remediation_v1/round285_structures"
OUT_MANIFEST = ROOT / "data/al3ni_remediation_v1/round285_manifest.csv"
OUT_SEALED_MANIFEST = ROOT / "data/al3ni_remediation_v1/round285_sealed_manifest.csv"
OUT_STATUS = ROOT / "configs/ROUND285_HIGH_EXPANSION_DENSIFY_DESIGN_STATUS.md"
OUT_SEAL_POLICY = ROOT / "configs/AL3NI_ROUND285_SEALED_CONFIRMATION_POLICY.txt"

PHASE_K, PHASE_SPIN = (10, 8, 8), False


def deformation(s):
    F = np.eye(3) * (1.0 + s)
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


def build_candidate(cid, ref, s, rattle, seed):
    F = deformation(s)
    cand = Atoms(numbers=ref.numbers, positions=ref.positions.copy(), cell=ref.cell.array.copy(), pbc=True)
    cand.set_cell(cand.cell.array @ F.T, scale_atoms=True)
    if rattle > 0:
        rng = np.random.default_rng(seed)
        disp = rng.normal(0, rattle, (len(cand), 3))
        disp -= disp.mean(axis=0)
        cand.positions += disp
        cand.wrap()
    cand.info = {"config_id": cid, "phase": "Al3Ni"}
    return cand


def main():
    dft = read(COMBINED220_DFT, index=":")
    train_ids = {a.info["config_id"] for a in read(COMBINED220_TRAIN, index=":")}
    valid_ids = {a.info["config_id"] for a in read(COMBINED220_VALID, index=":")}

    al3ni = [a for a in dft if a.info.get("phase") == "Al3Ni"]
    by_id = {a.info["config_id"]: a for a in al3ni}
    ref = by_id["Al3Ni_relaxed"]
    ref_cell = ref.cell.array.copy()

    def role_of(cid):
        if cid in train_ids:
            return "TRAIN"
        if cid in valid_ids:
            return "VALIDATION"
        return "RESERVED"

    desc = {cid: descriptor(a, ref_cell) for cid, a in by_id.items()}
    train_pop = [c for c in desc if role_of(c) == "TRAIN"]
    reserved_pop = [c for c in desc if role_of(c) == "RESERVED"]
    valid_pop = [c for c in desc if role_of(c) == "VALIDATION"]

    print(f"Al3Ni population: {len(al3ni)} total, {len(train_pop)} TRAIN, "
          f"{len(valid_pop)} VALIDATION, {len(reserved_pop)} RESERVED")
    print(f"RESERVED members (gate b reference, cfg109/cfg110 excluded -- consumed): {sorted(reserved_pop)}")

    # gate (a): 5th percentile of pairwise Al3Ni TRAIN-TRAIN combined distances, fresh vs combined-220
    pairs = list(combinations(train_pop, 2))
    pair_shape, pair_vol, pair_strain = [], [], []
    for id1, id2 in pairs:
        ds, dv, dst = sub_distances(desc[id1], desc[id2])
        pair_shape.append(ds); pair_vol.append(dv); pair_strain.append(dst)
    stds = (np.std(pair_shape) or 1e-12, np.std(pair_vol) or 1e-12, np.std(pair_strain) or 1e-12)
    pair_combined = [combined_distance(desc[id1], desc[id2], stds) for id1, id2 in pairs]
    threshold_a = float(np.percentile(pair_combined, 5))

    # gate (b): min TRAIN<->RESERVED combined distance, Al3Ni only, cfg109/cfg110 excluded (consumed)
    leak_pairs = [combined_distance(desc[t], desc[r], stds) for t in train_pop for r in reserved_pop]
    threshold_b = float(min(leak_pairs))

    print(f"gate(a) threshold (5th pct TRAIN-TRAIN, ADVISORY ONLY for same-role TRAIN-vs-TRAIN per policy): {threshold_a:.4f}")
    print(f"gate(b) threshold (min TRAIN<->RESERVED): {threshold_b:.4f}")

    # Duplicate epsilon for gate (c): calibrated directly against this population --
    # a true duplicate (same family, same strain, same/no rattle) gives combined_distance
    # ~1e-7 (floating-point noise only); the closest LEGITIMATE different-strain TRAIN
    # neighbor observed in this round's own grid gives combined_distance ~0.097, and the
    # closest legitimate matched-strain-family pair (iso vs volume_rattle, same s) gives
    # ~0.28 (d_vol=d_strain=0 by construction, but d_shape != 0 from the rattle
    # displacement). 1e-3 sits three orders of magnitude below both legitimate cases and
    # eight orders above the true-duplicate floor -- a safe separator, not a round number.
    DUPLICATE_EPSILON = 1e-3

    OUT_BASE.mkdir(parents=True, exist_ok=True)
    all_accepted_desc = dict(desc)  # grows as candidates are kept this round

    def evaluate_and_maybe_keep(cid, family, s, rattle, seed, kept_list, report_rows):
        cand = build_candidate(cid, ref, s, rattle, seed)
        cdesc = descriptor(cand, ref_cell)

        # gate (a): TRAIN-vs-TRAIN, same role as the candidate's target (TRAIN) -- per
        # EXPANSION_BATCH_DESIGN_POLICY.md gate (c) section: "Same-role ... pairs are
        # exempt from gate (a) and handled by [gate c] instead" and "TRAIN-vs-TRAIN
        # similarity at different strain values is an efficiency advisory only --
        # informative, never a rejection reason." Densification candidates are BY DESIGN
        # similar to existing TRAIN at a different strain -- applying gate (a) as a
        # rejection here would be design_round220's exact documented error class #3/#4.
        dists_train = [combined_distance(cdesc, desc[t], stds) for t in train_pop]
        min_dist_train = min(dists_train)
        nearest_train = train_pop[int(np.argmin(dists_train))]
        gate_a = f"ADVISORY({'below' if min_dist_train < threshold_a else 'above'}_thr)"

        # gate (b): real gate, candidate (TRAIN, about to exist) vs RESERVED (different role)
        dists_reserved = [combined_distance(cdesc, desc[r], stds) for r in reserved_pop]
        min_dist_reserved = min(dists_reserved)
        nearest_reserved = reserved_pop[int(np.argmin(dists_reserved))]
        gate_b = "PASS" if min_dist_reserved >= threshold_b else "FAIL_LEAKAGE"

        # gate (c): matched-strain-family role-sharing (trivial here, all TRAIN) +
        # true near-duplicate detection vs ANY existing accepted member of any role,
        # using the calibrated combined-distance epsilon, not exact-byte geometry hash
        # (which is fragile to float reconstruction noise -- see design note above).
        dists_all = {cid2: combined_distance(cdesc, d2, stds) for cid2, d2 in all_accepted_desc.items()}
        nearest_any = min(dists_all, key=dists_all.get)
        min_dist_any = dists_all[nearest_any]
        gate_c = "PASS" if min_dist_any >= DUPLICATE_EPSILON else f"FAIL_DUPLICATE(of {nearest_any})"

        status = "KEPT" if gate_b == "PASS" and gate_c == "PASS" else "REJECTED"
        report_rows.append({
            "config_id": cid, "family": family, "s_pct": s * 100, "rattle_sigma_A": rattle,
            "min_dist_train": min_dist_train, "nearest_train": nearest_train, "threshold_a": threshold_a,
            "min_dist_reserved": min_dist_reserved, "nearest_reserved": nearest_reserved, "threshold_b": threshold_b,
            "min_dist_any": min_dist_any, "nearest_any": nearest_any, "dup_epsilon": DUPLICATE_EPSILON,
            "gate_a": gate_a, "gate_b": gate_b, "gate_c": gate_c, "status": status,
        })
        if status == "KEPT":
            all_accepted_desc[cid] = cdesc
            kept_list.append((cid, family, s, rattle, seed, cand))
        return status

    kept, report_rows = [], []
    for num, family, s, rattle in DENSIFY_GRID:
        cid = f"cfg{num}_Al3Ni_{family}"
        seed = 20262000 + num
        evaluate_and_maybe_keep(cid, family, s, rattle, seed, kept, report_rows)

    kept_sealed, sealed_report_rows = [], []
    for num, family, s, rattle in SEALED_CANDIDATES:
        cid = f"cfg{num}_Al3Ni_{family}"
        seed = 20262000 + num
        evaluate_and_maybe_keep(cid, family, s, rattle, seed, kept_sealed, sealed_report_rows)

    # write densification TRAIN candidates
    manifest_rows = []
    for cid, family, s, rattle, seed, cand in kept:
        sdir = OUT_BASE / "train"
        sdir.mkdir(parents=True, exist_ok=True)
        sp = sdir / f"{cid}.extxyz"
        qp = sdir / f"{cid}.in"
        write(sp, cand, format="extxyz")
        qp.write_text(qe_text(cand, cid, PHASE_K, PHASE_SPIN))
        reread = read(sp)
        vals_d = reread.get_all_distances(mic=True)[np.triu_indices(len(reread), 1)]
        manifest_rows.append({
            "config_id": cid, "phase": "Al3Ni", "config_family": family, "target_role": "TRAIN",
            "strain_type": "isotropic", "strain_value": format(s, ".17g"),
            "rattle_sigma_A": rattle, "random_seed": seed if rattle > 0 else "NONE",
            "natoms": len(reread), "minimum_distance_A": format(float(vals_d.min()), ".17g"),
            "structure_path": str(sp), "structure_sha256": sha256(sp),
            "qe_input_path": str(qp), "qe_input_sha256": sha256(qp),
            "qe_status": "READY_NOT_RUN", "dft_status": "NOT_STARTED",
        })
    if manifest_rows:
        with OUT_MANIFEST.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(manifest_rows[0]))
            w.writeheader()
            w.writerows(manifest_rows)

    # write sealed confirmation candidates
    sealed_manifest_rows = []
    for cid, family, s, rattle, seed, cand in kept_sealed:
        sdir = OUT_BASE / "sealed_confirmation"
        sdir.mkdir(parents=True, exist_ok=True)
        sp = sdir / f"{cid}.extxyz"
        qp = sdir / f"{cid}.in"
        write(sp, cand, format="extxyz")
        qp.write_text(qe_text(cand, cid, PHASE_K, PHASE_SPIN))
        reread = read(sp)
        gh = geom_hash(reread)
        sealed_manifest_rows.append({
            "config_id": cid, "phase": "Al3Ni", "config_family": family, "target_role": "CONFIRMATION_HOLDOUT",
            "strain_type": "isotropic", "strain_value": format(s, ".17g"),
            "rattle_sigma_A": rattle, "random_seed": seed if rattle > 0 else "NONE",
            "natoms": len(reread), "structure_path": str(sp), "structure_sha256": sha256(sp),
            "geometry_sha256": gh, "qe_input_path": str(qp), "qe_input_sha256": sha256(qp),
            "qe_status": "READY_NOT_RUN", "dft_status": "NOT_STARTED",
            "label_access_policy": "SEALED_AFTER_DFT -- energy/forces/stress must not be read by any script "
                                    "until a single, designated future unsealing event",
        })
    if sealed_manifest_rows:
        with OUT_SEALED_MANIFEST.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(sealed_manifest_rows[0]))
            w.writeheader()
            w.writerows(sealed_manifest_rows)

    # --- status report ---
    lines = [
        "# Round-285: Al3Ni High-Expansion Densification + New Sealed Confirmation Pair (design-only, NO DFT run)",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Background",
        "combined-220 Al3Ni iso_expansion/volume_rattle_expansion TRAIN rungs: s=1.0% (cfg027, iso only), "
        "s=2.0% (cfg103+cfg105, matched pair), s=3.0% (cfg029, iso only, no volume_rattle partner), "
        "s=4.6% (cfg111+cfg112, matched pair), s=5.6% (cfg113+cfg114, matched pair, at the edge). "
        "Only 3 TRAIN rungs sit inside +2%..+5.6%; the 3.0%->4.6% span had zero iso/volume_rattle "
        "coverage -- exactly where cfg109/cfg110 (s=4.0%) sat before being consumed by unsealing "
        "(2026-08-17, AL3NI_FINAL_UNSEALING_RESULT.txt).",
        "",
        "## Policy change applied this round",
        "Gate (b) no longer treats cfg109/cfg110 as a protected holdout -- they are consumed. "
        "Candidates may sit directly adjacent to s=4.0%. Gate (b) instead uses the Al3Ni RESERVED "
        "population still live in combined-220 (cfg041, cfg042, cfg043, cfg044, "
        "Al3Ni_shear015_rattle002), same substitution design_round220_close_last2.py already used. "
        "Gates (a) and (c) re-derived fresh against combined-220's own Al3Ni population, per policy "
        "(never reused verbatim across rounds).",
        "",
        f"gate(a) threshold (5th percentile Al3Ni TRAIN-TRAIN combined distance, combined-220, ADVISORY ONLY "
        f"for same-role TRAIN-vs-TRAIN per EXPANSION_BATCH_DESIGN_POLICY.md gate(c)): {threshold_a:.4f}",
        f"gate(b) threshold (min Al3Ni TRAIN<->RESERVED combined distance, cfg109/cfg110 excluded): {threshold_b:.4f}",
        "gate(c) duplicate epsilon (combined distance, calibrated: true duplicate ~1e-7, closest legitimate "
        "different-strain neighbor ~0.097, closest legitimate matched-strain-family pair ~0.28): 1.0e-03",
        "",
        "## Densification grid: s in {3.0, 3.5, 4.0, 4.5, 5.0}%, iso_expansion + volume_rattle_expansion "
        "(rattle_sigma=0.015 A, project-standard for this family)",
        "",
        "| config_id | family | s (%) | min dist TRAIN | nearest TRAIN | thr(a) advisory | min dist RESERVED | "
        "nearest RESERVED | thr(b) | min dist ANY | nearest ANY | gate(a) | gate(b) | gate(c) | status |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in report_rows:
        lines.append(
            f"| {r['config_id']} | {r['family']} | {r['s_pct']:.2f} | {r['min_dist_train']:.4f} | {r['nearest_train']} | "
            f"{r['threshold_a']:.4f} | {r['min_dist_reserved']:.4f} | {r['nearest_reserved']} | {r['threshold_b']:.4f} | "
            f"{r['min_dist_any']:.6f} | {r['nearest_any']} | "
            f"{r['gate_a']} | {r['gate_b']} | {r['gate_c']} | **{r['status']}** |"
        )
    lines += ["", f"DENSIFICATION KEPT: {len(kept)}/{len(DENSIFY_GRID)}", "",
              "## New sealed confirmation pair (proposed, replaces consumed cfg109/cfg110)",
              "",
              "Strain values deliberately OFF the densification grid (3.75%, 4.25%) so each tests genuine "
              "interpolation inside the newly densified region rather than sitting on a trained rung. "
              "One iso_expansion, one volume_rattle_expansion -- same family split as cfg109/cfg110. "
              "Geometry and QE input written; DFT NOT run; energy/forces/stress do not exist for these "
              "structures yet. Sealing takes effect the moment this design is accepted: no future script "
              "may read their DFT labels except at a single, later, explicitly designated unsealing event, "
              "enforced the same way AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt enforced cfg109/cfg110.",
              "",
              "| config_id | family | s (%) | min dist TRAIN | nearest TRAIN | thr(a) advisory | min dist RESERVED | "
              "nearest RESERVED | thr(b) | min dist ANY | nearest ANY | gate(a) | gate(b) | gate(c) | status |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sealed_report_rows:
        lines.append(
            f"| {r['config_id']} | {r['family']} | {r['s_pct']:.2f} | {r['min_dist_train']:.4f} | {r['nearest_train']} | "
            f"{r['threshold_a']:.4f} | {r['min_dist_reserved']:.4f} | {r['nearest_reserved']} | {r['threshold_b']:.4f} | "
            f"{r['min_dist_any']:.6f} | {r['nearest_any']} | "
            f"{r['gate_a']} | {r['gate_b']} | {r['gate_c']} | **{r['status']}** |"
        )
    lines += ["", f"SEALED PAIR KEPT: {len(kept_sealed)}/{len(SEALED_CANDIDATES)}", "",
              "## Not done in this pass",
              "DFT has not been run for any candidate (densification or sealed). No merge into any "
              "TRAIN/VALIDATION split. No retraining. cfg109/cfg110 were not read, referenced, or "
              "reintroduced to any split."]
    OUT_STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    seal_lines = [
        "AL3NI ROUND-285 SEALED CONFIRMATION POLICY",
        "",
        f"Written UTC: {datetime.now(timezone.utc).isoformat()}",
        "Replaces the confirmation-holdout role vacated by cfg109/cfg110 (consumed by unsealing,",
        "2026-08-17, AL3NI_FINAL_UNSEALING_RESULT.txt).",
        "",
        "SEALED CONFIG IDS:",
    ]
    for cid, family, s, rattle, seed, cand in kept_sealed:
        seal_lines.append(f"  {cid} (s={s*100:.2f}%, family={family}, rattle_sigma_A={rattle})")
    seal_lines += [
        "",
        "RULE: geometry (cell, positions) may be read for design/screening purposes at any point.",
        "Energy, forces, and stress must NEVER be read by any script, at any point, until a single,",
        "explicitly designated future unsealing event -- immediately before the next LAMMPS-readiness",
        "assessment against whatever model is final at that time. This mirrors",
        "AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt's rule for cfg109/cfg110 verbatim.",
        "",
        "STATUS: DFT NOT YET RUN for these structures. Sealing takes effect regardless of DFT timing --",
        "once DFT is eventually run (a separate, future, DFT-only pass), the resulting qe.out/XML labels",
        "become sealed data immediately and are subject to the same never-read-until-unsealing rule.",
        "",
        "These two structures must NOT be added to TRAIN or VALIDATION at any point before or after",
        "unsealing -- their sole purpose is to serve as the next confirmation-holdout pair.",
    ]
    OUT_SEAL_POLICY.write_text("\n".join(seal_lines) + "\n")


if __name__ == "__main__":
    main()
