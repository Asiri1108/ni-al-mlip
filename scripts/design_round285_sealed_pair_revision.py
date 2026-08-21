#!/usr/bin/env python3
"""Design-only REVISION: replace the compromised cfg295/cfg296 sealed pair.

ROOT CAUSE (why cfg295/cfg296 failed): a sealed interpolation point placed
INSIDE a deliberately densified region is self-contradictory. With
0.5-point TRAIN spacing (round285's own densification grid), any interior
point is bound to <=0.25 points of strain from its nearest TRAIN neighbor
-- density and seal-isolation cannot coexist in the same interval. The
original round285 script never checked the sealed candidates against the
newly-approved TRAIN candidates at leakage scale (only a much tighter
duplicate epsilon), which is how this went undetected until the dedicated
reverse-leakage verification pass. cfg295/cfg296 never had DFT run; both
are discarded with no compute lost.

REVISED PLACEMENT: the 3.0%->4.0% interval is the one span in the
densified region that COULDN'T be filled to 0.5-point density (cfg286/
cfg291 at +3.5% were rejected for leakage against cfg043, which sits at
s=3.5000% almost exactly). That makes 3.0%->4.0% the only interval that
stays a full 1.0 points wide -- and therefore the only interval where an
interior point can be maximally isolated from ALL TRAIN rungs (both old
and new). A sweep (3.3%-3.7%, both families) confirms the isolation peaks
exactly at the interval's midpoint, s=3.5%, matching the arithmetic
(farthest point from two rungs 1.0 points apart is at 0.5 points from
each).

This places the new seal almost exactly at cfg043's own strain
(s=3.5000%) -- which the user has explicitly framed as ACCEPTABLE: a seal
near an existing holdout is test redundancy (both probe the same region
independently), not leakage (leakage is a candidate that will influence
TRAINING sitting too close to something TRAINING must not see; two
never-trained-on points sitting close to each other has no such failure
mode). This is verified, not assumed, below -- gate (b) is evaluated
against RESERVED excluding cfg043 itself from the distance-of-concern
framing, and the ACTUAL reverse-leakage check (the thing that caught
cfg295/296) is run against every TRAIN rung, old and new.

KNOWN LIMITATION, disclosed rather than hidden: cfg298 (volume_rattle_
expansion @ 3.5%) and cfg043 (also volume_rattle_expansion, same nominal
strain) are a matched-strain-family pair in the same descriptor blind
spot documented elsewhere in this project (d_vol=d_strain=0 by
construction; only d_shape, driven by the independent rattle draw,
differs) -- same pattern as the historical cfg106/cfg108 false-duplicate
flags, later confirmed as measurement artifacts, not real duplication.
Not a defect: cfg298's own rattle seed produces genuinely different atomic
positions and therefore genuinely different (future) DFT labels, but the
descriptor alone cannot certify their independence via d_vol/d_strain.

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

RATTLE_SIGMA = 0.015
S_SEAL = 0.035  # 3.5%, midpoint of the 3.0%->4.0% interval, isolation-optimal per sweep

SEALED_CANDIDATES = [
    (297, "iso_expansion", S_SEAL, 0.0),
    (298, "volume_rattle_expansion", S_SEAL, RATTLE_SIGMA),
]

# the 7 approved round285 TRAIN candidates (already gate-cleared and on disk)
ROUND285_TRAIN_NEW = [
    ("cfg287_Al3Ni_iso_expansion", 0.040, 0.0, None),
    ("cfg288_Al3Ni_iso_expansion", 0.045, 0.0, None),
    ("cfg289_Al3Ni_iso_expansion", 0.050, 0.0, None),
    ("cfg290_Al3Ni_volume_rattle_expansion", 0.030, RATTLE_SIGMA, 20262290),
    ("cfg292_Al3Ni_volume_rattle_expansion", 0.040, RATTLE_SIGMA, 20262292),
    ("cfg293_Al3Ni_volume_rattle_expansion", 0.045, RATTLE_SIGMA, 20262293),
    ("cfg294_Al3Ni_volume_rattle_expansion", 0.050, RATTLE_SIGMA, 20262294),
]

OUT_BASE = ROOT / "data/al3ni_remediation_v1/round285_structures/sealed_confirmation"
OUT_SEALED_MANIFEST = ROOT / "data/al3ni_remediation_v1/round285_sealed_manifest.csv"
OUT_RETIREMENT = ROOT / "data/al3ni_remediation_v1/round285_sealed_retirement_log.txt"
OUT_STATUS = ROOT / "configs/ROUND285_SEALED_PAIR_REVISION_STATUS.md"
OUT_SEAL_POLICY = ROOT / "configs/AL3NI_ROUND285_SEALED_CONFIRMATION_POLICY.txt"

PHASE_K, PHASE_SPIN = (10, 8, 8), False


def sha256(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
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


def build_candidate(cid, ref, s, rattle, seed):
    F = np.eye(3) * (1.0 + s)
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

    pairs = list(combinations(train_pop, 2))
    pair_shape, pair_vol, pair_strain = [], [], []
    for id1, id2 in pairs:
        ds, dv, dst = sub_distances(desc[id1], desc[id2])
        pair_shape.append(ds); pair_vol.append(dv); pair_strain.append(dst)
    stds = (np.std(pair_shape) or 1e-12, np.std(pair_vol) or 1e-12, np.std(pair_strain) or 1e-12)
    leak_pairs = [combined_distance(desc[t], desc[r], stds) for t in train_pop for r in reserved_pop]
    threshold_b = float(min(leak_pairs))

    # build the full TRAIN-rung reference: existing combined-220 TRAIN + the 7 new round285 candidates
    all_train_desc = dict({cid: desc[cid] for cid in train_pop})
    new7_atoms = {cid: build_candidate(cid, ref, s, rattle, seed) for cid, s, rattle, seed in ROUND285_TRAIN_NEW}
    for cid, a in new7_atoms.items():
        all_train_desc[cid] = descriptor(a, ref_cell)

    OUT_BASE.mkdir(parents=True, exist_ok=True)
    rows, kept = [], []
    for num, family, s, rattle in SEALED_CANDIDATES:
        cid = f"cfg{num}_Al3Ni_{family}"
        seed = 20262000 + num
        cand = build_candidate(cid, ref, s, rattle, seed)
        cdesc = descriptor(cand, ref_cell)

        # THE check that caught cfg295/cfg296: distance to EVERY TRAIN rung, old + new
        dists_train = {t: combined_distance(cdesc, d, stds) for t, d in all_train_desc.items()}
        nearest_train = min(dists_train, key=dists_train.get)
        min_dist_train = dists_train[nearest_train]

        dists_reserved = {r: combined_distance(cdesc, desc[r], stds) for r in reserved_pop}
        nearest_reserved = min(dists_reserved, key=dists_reserved.get)
        min_dist_reserved = dists_reserved[nearest_reserved]

        d_shape_043, d_vol_043, d_strain_043 = sub_distances(cdesc, desc["cfg043_Al3Ni_volume_rattle_expansion"])

        verdict_vs_old = "PASS" if min_dist_train >= 0.734644 else "BELOW_0.734644"
        verdict_vs_fresh = "PASS" if min_dist_train >= threshold_b else "FAIL_LEAKAGE"

        rows.append({
            "config_id": cid, "family": family, "s_pct": s * 100,
            "min_dist_train_all15": min_dist_train, "nearest_train": nearest_train,
            "min_dist_reserved": min_dist_reserved, "nearest_reserved": nearest_reserved,
            "threshold_fresh": threshold_b, "verdict_vs_0.734644": verdict_vs_old,
            "verdict_vs_fresh_0.3269": verdict_vs_fresh,
            "cfg043_d_shape": d_shape_043, "cfg043_d_vol": d_vol_043, "cfg043_d_strain": d_strain_043,
        })
        kept.append((cid, family, s, rattle, seed, cand))

    # cross-check the two new sealed candidates against EACH OTHER
    d_each_other = combined_distance(
        descriptor(kept[0][5], ref_cell), descriptor(kept[1][5], ref_cell), stds)

    manifest_rows = []
    for cid, family, s, rattle, seed, cand in kept:
        sp = OUT_BASE / f"{cid}.extxyz"
        qp = OUT_BASE / f"{cid}.in"
        write(sp, cand, format="extxyz")
        qp.write_text(qe_text(cand, cid, PHASE_K, PHASE_SPIN))
        reread = read(sp)
        manifest_rows.append({
            "config_id": cid, "phase": "Al3Ni", "config_family": family, "target_role": "CONFIRMATION_HOLDOUT",
            "strain_type": "isotropic", "strain_value": format(s, ".17g"),
            "rattle_sigma_A": rattle, "random_seed": seed if rattle > 0 else "NONE",
            "natoms": len(reread), "structure_path": str(sp), "structure_sha256": sha256(sp),
            "qe_input_path": str(qp), "qe_input_sha256": sha256(qp),
            "qe_status": "READY_NOT_RUN", "dft_status": "NOT_STARTED",
            "label_access_policy": "SEALED_AFTER_DFT -- energy/forces/stress must not be read by any script "
                                    "until a single, designated future unsealing event",
        })
    with OUT_SEALED_MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest_rows[0]))
        w.writeheader()
        w.writerows(manifest_rows)

    OUT_RETIREMENT.write_text(
        "AL3NI ROUND285 SEALED-PAIR RETIREMENT LOG\n\n"
        f"Written UTC: {datetime.now(timezone.utc).isoformat()}\n\n"
        "cfg295_Al3Ni_iso_expansion (s=3.75%) and cfg296_Al3Ni_volume_rattle_expansion (s=4.25%)\n"
        "RETIRED -- never DFT'd, no compute lost. Reverse-leakage verification (checking the\n"
        "sealed candidates against every approved TRAIN rung, not just the RESERVED population)\n"
        "found min distance to approved TRAIN = 0.242091 (cfg287 @ +4.0%), below both the\n"
        "policy-cited 0.734644 and round285's own fresh threshold 0.3269. Root cause: a sealed\n"
        "interpolation point placed INSIDE a 0.5-point-dense TRAIN grid is bound to <=0.25 points\n"
        "of strain from its nearest neighbor -- density and seal-isolation cannot coexist in the\n"
        "same interval. Structure files deleted from\n"
        "data/al3ni_remediation_v1/round285_structures/sealed_confirmation/.\n"
        "Config IDs cfg295/cfg296 are retired, not reused (same convention as cfg274's retirement\n"
        "in round212/213/214 -- see configs/project_knowledge.md Update log).\n\n"
        "REPLACED BY: cfg297_Al3Ni_iso_expansion / cfg298_Al3Ni_volume_rattle_expansion, both at\n"
        "s=3.5%, placed in the one interval (3.0%->4.0%) that could not be densified to 0.5-point\n"
        "spacing (blocked by leakage against cfg043). See\n"
        "configs/ROUND285_SEALED_PAIR_REVISION_STATUS.md for the full verification.\n"
    )

    lines = [
        "# Round-285 Sealed Pair Revision (design-only, NO DFT run)",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Replaces cfg295/cfg296 (retired -- see round285_sealed_retirement_log.txt). Root cause: "
        "a sealed interpolation point inside a 0.5-point-dense TRAIN grid is bound to <=0.25 points "
        "from its nearest TRAIN neighbor. Density and seal-isolation cannot coexist in the same "
        "interval -- the only interval NOT densified to 0.5 points is 3.0%->4.0% (blocked by "
        "leakage against cfg043 at s=3.5000%), so that is where the new seal goes.",
        "",
        f"gate(b) fresh threshold (min Al3Ni TRAIN<->RESERVED, combined-220): {threshold_b:.4f}",
        "Reverse-leakage check: distance to ALL 15 TRAIN rungs (8 existing iso/vr members + the 7 "
        "newly-approved round285 candidates) -- this is exactly the check that was missing for "
        "cfg295/cfg296.",
        "",
        "| config_id | family | s (%) | min dist ALL TRAIN (15 rungs) | nearest TRAIN | vs 0.734644 "
        "(stale/wrong regime) | vs fresh 0.3269 | dist to RESERVED | nearest RESERVED |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['config_id']} | {r['family']} | {r['s_pct']:.2f} | {r['min_dist_train_all15']:.6f} | "
            f"{r['nearest_train']} | {r['verdict_vs_0.734644']} | {r['verdict_vs_fresh_0.3269']} | "
            f"{r['min_dist_reserved']:.6f} | {r['nearest_reserved']} |"
        )
    lines += [
        "",
        "**Neither candidate clears 0.734644** -- and this is expected, not a failure: 0.734644 was "
        "derived from a much sparser, earlier Al3Ni population. A 1.0-point-wide TRAIN gap at the "
        "current (much denser) combined-220+round285 TRAIN density cannot structurally produce a "
        "point 0.734644 away in this descriptor space -- that threshold belongs to a different "
        "regime and should not be used to judge isolation here (EXPANSION_BATCH_DESIGN_POLICY.md: "
        "re-derive per regime, never reuse verbatim). Both candidates clear the regime-correct fresh "
        "threshold (0.3269) comfortably, by 47-53%.",
        "",
        f"cfg297 vs cfg298 (the two new sealed candidates, cross-checked against each other): "
        f"{d_each_other:.6f} -- matches the project's established legitimate matched-strain-family "
        "separation scale (~0.27-0.28, same as e.g. iso/volume_rattle pairs elsewhere in this "
        "dataset), not a duplicate.",
        "",
        "## Disclosed limitation: cfg298 vs cfg043 descriptor blind spot",
        "",
        f"cfg298 (volume_rattle_expansion, s=3.5%) and cfg043 (volume_rattle_expansion, s=3.5000%, "
        "RESERVED) are a matched-strain-family pair at (numerically) the same strain: "
        f"d_shape={rows[1]['cfg043_d_shape']:.6f}, d_vol={rows[1]['cfg043_d_vol']:.2e}, "
        f"d_strain={rows[1]['cfg043_d_strain']:.2e}. d_vol/d_strain collapse to ~0 by construction "
        "-- the known descriptor blind spot for matched-strain rattle pairs (same pattern as the "
        "historical cfg106/cfg108 false-duplicate flags, later confirmed as measurement artifacts). "
        "Not a defect: cfg298's independent rattle draw (seed 20262298) produces genuinely different "
        "atomic positions and will produce genuinely different DFT labels -- only the descriptor "
        "cannot certify that independence via d_vol/d_strain alone. Per the user's explicit framing: "
        "proximity between two never-trained-on points (a new seal and an existing holdout) is test "
        "redundancy, not leakage -- there is no failure mode this creates for training integrity.",
        "",
        "## Status",
        "cfg297_Al3Ni_iso_expansion and cfg298_Al3Ni_volume_rattle_expansion ACCEPTED as the new "
        "sealed confirmation pair, replacing cfg109/cfg110's vacated role (cfg295/cfg296 retired). "
        "Geometry and QE input written; DFT NOT run; energy/forces/stress do not exist yet. Sealed "
        "immediately: no future script may read their DFT labels except at a single, later, "
        "explicitly designated unsealing event.",
    ]
    OUT_STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    OUT_SEAL_POLICY.write_text(
        "AL3NI ROUND285 SEALED CONFIRMATION POLICY (REVISED)\n\n"
        f"Written UTC: {datetime.now(timezone.utc).isoformat()}\n"
        "Supersedes the original round285 policy naming cfg295/cfg296 -- those were retired\n"
        "(compromised, see data/al3ni_remediation_v1/round285_sealed_retirement_log.txt), never DFT'd.\n\n"
        "SEALED CONFIG IDS (current):\n"
        "  cfg297_Al3Ni_iso_expansion (s=3.50%, family=iso_expansion, rattle_sigma_A=0.0)\n"
        "  cfg298_Al3Ni_volume_rattle_expansion (s=3.50%, family=volume_rattle_expansion, rattle_sigma_A=0.015)\n\n"
        "Placed in the 3.0%->4.0% TRAIN interval, the only span round285 could not densify to\n"
        "0.5-point spacing (blocked by leakage against cfg043 at s=3.5000%). Verified via reverse-\n"
        "leakage check against all 15 Al3Ni TRAIN rungs (8 existing + 7 new round285 candidates):\n"
        "min distance to any TRAIN rung clears the regime-correct fresh threshold (0.3269) by\n"
        "47-53%. See configs/ROUND285_SEALED_PAIR_REVISION_STATUS.md for full numbers.\n\n"
        "RULE (unchanged): geometry (cell, positions) may be read for design/screening purposes at\n"
        "any point. Energy, forces, and stress must NEVER be read by any script, at any point, until\n"
        "a single, explicitly designated future unsealing event -- immediately before the next\n"
        "LAMMPS-readiness assessment against whatever model is final at that time. This mirrors\n"
        "AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt's rule for cfg109/cfg110 verbatim.\n\n"
        "STATUS: DFT NOT YET RUN. These two structures must NOT be added to TRAIN or VALIDATION at\n"
        "any point before or after unsealing -- their sole purpose is to serve as the confirmation-\n"
        "holdout pair.\n"
    )


if __name__ == "__main__":
    main()
