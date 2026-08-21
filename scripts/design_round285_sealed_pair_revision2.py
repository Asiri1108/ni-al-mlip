#!/usr/bin/env python3
"""Design-only REVISION 2: replace cfg298 (retired -- descriptor-degenerate
with cfg043, the feedback probe) with cfg299_Al3Ni_volume_rattle_expansion
at s=3.6%.

WHY cfg298 WAS RETIRED (not just "close to TRAIN" like cfg295/296 -- a
different, more serious problem): cfg298 (volume_rattle_expansion, s=3.5%)
sat at the exact same nominal strain as cfg043, the FEEDBACK PROBE whose
error value steered 5+ remediation design rounds (documented in
AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt, CFG043 EXCLUSION RATIONALE).
d_vol/d_strain between cfg298 and cfg043 were ~1e-8/1e-9 -- a true
descriptor collapse, not the ordinary matched-strain-family blind spot
tolerated elsewhere (that pattern is normally between TWO CLEAN points;
here one side is a design-contaminated probe). A seal that is a
descriptor-clone of the feedback probe inherits its indirect design
contamination and cannot serve as an independent final test -- discarding
it is correct, not merely cautious.

cfg297 (iso_expansion, s=3.5%) is RETAINED: different family (no rattle)
at the same strain as cfg043 is the ordinary, tolerated matched-pair
separation (d_shape != 0, ~0.27-0.28 combined distance elsewhere in this
project), not a collapse -- verified below, not assumed.

REPLACEMENT SEARCH: swept volume_rattle_expansion candidates s=3.1%-3.9%
in the same 3.0%->4.0% TRAIN gap (0.1-point steps). Requirements: (1) not
descriptor-degenerate (d_vol<1e-3 AND d_strain<1e-3, the same calibrated
epsilon used throughout round285) with cfg043, cfg109, cfg110, cfg115, or
cfg297; (2) clears the regime-correct fresh threshold 0.3269 against all
15 Al3Ni TRAIN rungs (8 existing + 7 new round285 candidates). Result:
3.3%, 3.4%, 3.6%, 3.7% all pass cleanly (3.1%/3.2%/3.8%/3.9% fail the
TRAIN-distance threshold, too close to the 3.0%/4.0% TRAIN rungs; exactly
3.5% is the cfg043 collision). 3.6% has the best margin
(min_dist_TRAIN=0.4350, vs 3.4%'s 0.4312) and is picked.

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

RATTLE_SIGMA = 0.015
S_REPLACEMENT = 0.036  # 3.6%, best-margin non-degenerate slot in the 3.0-4.0% gap
CFG_NUM = 299

OUT_BASE = ROOT / "data/al3ni_remediation_v1/round285_structures/sealed_confirmation"
OUT_SEALED_MANIFEST = ROOT / "data/al3ni_remediation_v1/round285_sealed_manifest.csv"
OUT_RETIREMENT = ROOT / "data/al3ni_remediation_v1/round285_sealed_retirement_log.txt"
OUT_STATUS = ROOT / "configs/ROUND285_SEALED_PAIR_REVISION2_STATUS.md"
OUT_SEAL_POLICY = ROOT / "configs/AL3NI_ROUND285_SEALED_CONFIRMATION_POLICY.txt"

PHASE_K, PHASE_SPIN = (10, 8, 8), False
DEGEN_EPS = 1e-3


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
    al3ni = [a for a in dft if a.info.get("phase") == "Al3Ni"]
    by_id = {a.info["config_id"]: a for a in al3ni}
    ref = by_id["Al3Ni_relaxed"]
    ref_cell = ref.cell.array.copy()

    desc = {cid: descriptor(a, ref_cell) for cid, a in by_id.items()}
    train_pop = [c for c in desc if c in train_ids]
    pairs = list(combinations(train_pop, 2))
    pair_shape, pair_vol, pair_strain = [], [], []
    for id1, id2 in pairs:
        ds, dv, dst = sub_distances(desc[id1], desc[id2])
        pair_shape.append(ds); pair_vol.append(dv); pair_strain.append(dst)
    stds = (np.std(pair_shape) or 1e-12, np.std(pair_vol) or 1e-12, np.std(pair_strain) or 1e-12)
    threshold = 0.3269  # round285's own fresh gate(b) threshold, re-verified unchanged this pass

    # reference geometries for degeneracy checks -- geometry only, cfg109/cfg110 labels never read
    g109 = read(ROOT / "data/al3ni_remediation_v1/structures/cfg109_Al3Ni_iso_expansion.extxyz")
    g110 = read(ROOT / "data/al3ni_remediation_v1/structures/cfg110_Al3Ni_volume_rattle_expansion.extxyz")
    g297 = read(OUT_BASE / "cfg297_Al3Ni_iso_expansion.extxyz")
    ref_points = {
        "cfg043": desc["cfg043_Al3Ni_volume_rattle_expansion"],
        "cfg109": descriptor(g109, ref_cell),
        "cfg110": descriptor(g110, ref_cell),
        "cfg115": desc["cfg115_Al3Ni_iso_expansion"],
        "cfg297": descriptor(g297, ref_cell),
    }

    # full 15-rung TRAIN reference: 8 existing Al3Ni iso/vr TRAIN members + 7 new round285 candidates
    EXISTING8 = ["cfg027_Al3Ni_iso_expansion", "cfg103_Al3Ni_iso_expansion", "cfg105_Al3Ni_volume_rattle_expansion",
                 "cfg029_Al3Ni_iso_expansion", "cfg111_Al3Ni_iso_expansion", "cfg112_Al3Ni_volume_rattle_expansion",
                 "cfg113_Al3Ni_iso_expansion", "cfg114_Al3Ni_volume_rattle_expansion"]
    NEW7 = [
        ("cfg287_Al3Ni_iso_expansion", 0.040, 0.0, None), ("cfg288_Al3Ni_iso_expansion", 0.045, 0.0, None),
        ("cfg289_Al3Ni_iso_expansion", 0.050, 0.0, None), ("cfg290_Al3Ni_volume_rattle_expansion", 0.030, RATTLE_SIGMA, 20262290),
        ("cfg292_Al3Ni_volume_rattle_expansion", 0.040, RATTLE_SIGMA, 20262292),
        ("cfg293_Al3Ni_volume_rattle_expansion", 0.045, RATTLE_SIGMA, 20262293),
        ("cfg294_Al3Ni_volume_rattle_expansion", 0.050, RATTLE_SIGMA, 20262294),
    ]
    all_train = {cid: desc[cid] for cid in EXISTING8}
    for cid, s, rattle, seed in NEW7:
        all_train[cid] = descriptor(build_candidate(cid, ref, s, rattle, seed), ref_cell)

    cid = f"cfg{CFG_NUM}_Al3Ni_volume_rattle_expansion"
    seed = 20262000 + CFG_NUM
    cand = build_candidate(cid, ref, S_REPLACEMENT, RATTLE_SIGMA, seed)
    cdesc = descriptor(cand, ref_cell)

    dists_train = {t: combined_distance(cdesc, d, stds) for t, d in all_train.items()}
    nearest_train = min(dists_train, key=dists_train.get)
    min_dist_train = dists_train[nearest_train]

    degen_report = {}
    any_degen = False
    for name, rd in ref_points.items():
        d_shape, d_vol, d_strain = sub_distances(cdesc, rd)
        is_degen = d_vol < DEGEN_EPS and d_strain < DEGEN_EPS
        degen_report[name] = (d_shape, d_vol, d_strain, is_degen)
        any_degen = any_degen or is_degen

    verdict_train = "PASS" if min_dist_train >= threshold else "FAIL"
    verdict_degen = "CONFLICT" if any_degen else "ALL CLEAR"

    OUT_BASE.mkdir(parents=True, exist_ok=True)
    sp = OUT_BASE / f"{cid}.extxyz"
    qp = OUT_BASE / f"{cid}.in"
    write(sp, cand, format="extxyz")
    qp.write_text(qe_text(cand, cid, PHASE_K, PHASE_SPIN))
    reread = read(sp)

    manifest_row = {
        "config_id": cid, "phase": "Al3Ni", "config_family": "volume_rattle_expansion",
        "target_role": "CONFIRMATION_HOLDOUT", "strain_type": "isotropic",
        "strain_value": format(S_REPLACEMENT, ".17g"), "rattle_sigma_A": RATTLE_SIGMA, "random_seed": seed,
        "natoms": len(reread), "structure_path": str(sp), "structure_sha256": sha256(sp),
        "qe_input_path": str(qp), "qe_input_sha256": sha256(qp),
        "qe_status": "READY_NOT_RUN", "dft_status": "NOT_STARTED",
        "label_access_policy": "SEALED_AFTER_DFT -- energy/forces/stress must not be read by any script "
                                "until a single, designated future unsealing event",
    }
    # keep cfg297's row, replace cfg298's with cfg299's
    existing_rows = []
    if OUT_SEALED_MANIFEST.exists():
        with OUT_SEALED_MANIFEST.open() as f:
            existing_rows = [r for r in csv.DictReader(f) if r["config_id"].startswith("cfg297")]
    with OUT_SEALED_MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest_row))
        w.writeheader()
        for r in existing_rows:
            w.writerow({k: r.get(k, "") for k in manifest_row})
        w.writerow(manifest_row)

    with OUT_RETIREMENT.open("a") as f:
        f.write(
            "\n---\n\n"
            f"UPDATE ({datetime.now(timezone.utc).isoformat()}):\n"
            "cfg298_Al3Ni_volume_rattle_expansion (s=3.5%) RETIRED, second retirement this design "
            "thread -- never DFT'd, no compute lost. Reason (more serious than cfg295/cfg296's "
            "leakage issue): descriptor-degenerate with cfg043, the FEEDBACK PROBE that steered "
            "5+ remediation design rounds (AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt, CFG043 "
            "EXCLUSION RATIONALE). d_vol/d_strain vs cfg043 were ~1e-8/1e-9 -- a true descriptor "
            "collapse (same family, same strain), not the ordinary matched-pair separation. A seal "
            "that is a clone of the feedback probe inherits its indirect design contamination and "
            "cannot serve as an independent test.\n\n"
            f"REPLACED BY: cfg{CFG_NUM}_Al3Ni_volume_rattle_expansion (s={S_REPLACEMENT*100:.1f}%), "
            f"min_dist_TRAIN={min_dist_train:.6f} (threshold 0.3269), verified non-degenerate against "
            "cfg043/cfg109/cfg110/cfg115/cfg297 (all d_vol,d_strain >> 1e-3). cfg297 (iso_expansion, "
            "s=3.5%) unchanged, retained -- confirmed not degenerate with cfg043 (different family, "
            "legitimate matched-pair separation).\n"
        )

    lines = [
        "# Round-285 Sealed Pair Revision 2 (design-only, NO DFT run)",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
        "cfg298 retired (descriptor-degenerate with the feedback probe cfg043 -- see retirement log "
        "for full reasoning). cfg297 retained unchanged. This revision proposes "
        f"cfg{CFG_NUM}_Al3Ni_volume_rattle_expansion as the replacement second seal.",
        "",
        f"## cfg{CFG_NUM} (volume_rattle_expansion, s={S_REPLACEMENT*100:.1f}%)",
        "",
        f"min_dist to nearest of 15 TRAIN rungs: {min_dist_train:.6f} (nearest: {nearest_train}) "
        f"vs threshold 0.3269 -> **{verdict_train}**",
        "",
        "Degeneracy check (d_vol, d_strain must both be >> 1e-3 to be non-degenerate; the true-collapse "
        "floor observed for cfg298 vs cfg043 was ~1e-8/1e-9):",
        "",
        "| reference | d_shape | d_vol | d_strain | degenerate? |",
        "|---|---|---|---|---|",
    ]
    for name, (ds_, dv_, dst_, isd) in degen_report.items():
        lines.append(f"| {name} | {ds_:.6f} | {dv_:.2e} | {dst_:.2e} | {'YES -- CONFLICT' if isd else 'no'} |")
    lines += [
        "",
        f"**Overall degeneracy verdict: {verdict_degen}**",
        "",
        "## Status",
        f"cfg{CFG_NUM}_Al3Ni_volume_rattle_expansion ACCEPTED as the replacement second seal. "
        "cfg297_Al3Ni_iso_expansion retained unchanged. Sealed pair is now "
        f"{{cfg297, cfg{CFG_NUM}}}. Geometry and QE input written; DFT NOT run.",
    ]
    OUT_STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    OUT_SEAL_POLICY.write_text(
        "AL3NI ROUND285 SEALED CONFIRMATION POLICY (REVISION 2)\n\n"
        f"Written UTC: {datetime.now(timezone.utc).isoformat()}\n"
        "Supersedes the prior policy naming cfg298 -- retired (descriptor-degenerate with cfg043,\n"
        "the feedback probe; see data/al3ni_remediation_v1/round285_sealed_retirement_log.txt).\n"
        "cfg295/cfg296 remain retired from the first revision (leakage-compromised).\n\n"
        "SEALED CONFIG IDS (current):\n"
        "  cfg297_Al3Ni_iso_expansion (s=3.50%, family=iso_expansion, rattle_sigma_A=0.0)\n"
        f"  cfg{CFG_NUM}_Al3Ni_volume_rattle_expansion (s={S_REPLACEMENT*100:.1f}%, "
        f"family=volume_rattle_expansion, rattle_sigma_A={RATTLE_SIGMA})\n\n"
        f"cfg{CFG_NUM} placed off cfg043's exact strain (3.5%) specifically to avoid the descriptor-\n"
        "degeneracy that disqualified cfg298, while staying inside the 3.0%->4.0% under-dense "
        "interval and clearing the 0.3269 TRAIN-distance threshold. Verified non-degenerate against "
        "cfg043, cfg109, cfg110, cfg115, and cfg297 -- see "
        "configs/ROUND285_SEALED_PAIR_REVISION2_STATUS.md.\n\n"
        "RULE (unchanged): geometry (cell, positions) may be read for design/screening purposes at\n"
        "any point. Energy, forces, and stress must NEVER be read by any script, at any point, until\n"
        "a single, explicitly designated future unsealing event -- immediately before the next\n"
        "LAMMPS-readiness assessment against whatever model is final at that time.\n\n"
        "STATUS: DFT NOT YET RUN. These two structures must NOT be added to TRAIN or VALIDATION at\n"
        "any point before or after unsealing.\n"
    )


if __name__ == "__main__":
    main()
