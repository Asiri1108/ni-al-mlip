#!/usr/bin/env python3
"""Outlier review for Round-214 DFT labels (7 configs).

Self-population screen skipped (n=7 across 4 phases, 1-3 per phase --
too small for a meaningful MAD). Phase-context percentile vs combined-211
is the only informative screen here, same as round4's approach.
"""

from pathlib import Path
from collections import defaultdict

import numpy as np
from ase.io import read

ROOT = Path("/workspace/ni_al")
ROUND214 = ROOT / "data/al3ni_remediation_v1/round214_dft.extxyz"
CONTEXT_TRAIN = ROOT / "data/datasets/ni_al_combined211_train_173.extxyz"
CONTEXT_VALID = ROOT / "data/datasets/ni_al_combined211_validation_18.extxyz"
REPORT = ROOT / "data/al3ni_remediation_v1/round214_dft_outlier_review.txt"


def metrics_row(atoms):
    forces = np.asarray(atoms.get_forces(), dtype=float)
    stress = np.asarray(atoms.get_stress(voigt=True), dtype=float)
    return {"fmax": float(np.linalg.norm(forces, axis=1).max()),
            "frms": float(np.sqrt(np.mean(forces**2))),
            "stress_mag": float(np.linalg.norm(stress))}


def percentile_rank(value, population):
    population = np.asarray(population, dtype=float)
    return float((population < value).sum()) / len(population) * 100.0


def main():
    frames = read(ROUND214, index=":")
    context = read(CONTEXT_TRAIN, index=":") + read(CONTEXT_VALID, index=":")
    context_by_phase = defaultdict(list)
    for a in context:
        context_by_phase[a.info["phase"]].append(metrics_row(a))

    lines = ["ROUND-214 DFT OUTLIER REVIEW (forces/stresses)", "=" * 46,
             f"Dataset: {ROUND214}", f"Frames screened: {len(frames)}", "",
             "SELF-POPULATION SCREEN: SKIPPED (n=7 across 4 phases, too small for MAD)", "",
             "PHASE-CONTEXT PERCENTILE (vs combined-211 TRAIN+VALIDATION)", "-" * 60,
             f"{'config_id':<42s} {'phase':<8s} {'ctx_n':>5s} {'Fmax_pct':>9s} {'Frms_pct':>9s} {'stress_pct':>10s}"]
    context_flags = []
    for a in frames:
        m = metrics_row(a)
        phase = a.info["phase"]
        pop = context_by_phase.get(phase, [])
        fmax_pct = percentile_rank(m["fmax"], [p["fmax"] for p in pop])
        frms_pct = percentile_rank(m["frms"], [p["frms"] for p in pop])
        stress_pct = percentile_rank(m["stress_mag"], [p["stress_mag"] for p in pop])
        lines.append(f"{a.info['config_id']:<42s} {phase:<8s} {len(pop):>5d} {fmax_pct:>8.1f}% {frms_pct:>8.1f}% {stress_pct:>9.1f}%")
        if fmax_pct >= 95.0 or frms_pct >= 95.0 or stress_pct >= 95.0:
            context_flags.append(a.info["config_id"])

    lines.append("")
    lines.append("Context flags (>=95th percentile): " + (", ".join(sorted(set(context_flags))) if context_flags else "none"))
    lines.append("")
    lines.append("These candidates were deliberately pushed beyond existing TRAIN ceilings to clear")
    lines.append("gate (a) redundancy (round212/213's magnitude-widening process) -- high percentile rank")
    lines.append("is the expected outcome for exactly that reason, same as round3's outer candidates.")
    lines.append("")
    lines.append("Advisory only; no configuration removed or altered.")

    REPORT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
