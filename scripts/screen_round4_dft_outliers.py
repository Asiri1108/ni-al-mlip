#!/usr/bin/env python3
"""Outlier review for Round-4 biaxial DFT labels (forces/stresses).

Self-population MAD screen (Pilot-25/round3 method) is not meaningful at
n=2 (1 config per phase) -- skipped with an explicit note rather than run
on a population too small to produce a real MAD. Phase-context percentile
screen (same method as screen_round3_dft_outliers.py's Screen 2) is the
only screen that says anything useful here, run against each phase's
existing combined-127 TRAIN+VALIDATION population.
"""

from pathlib import Path

import numpy as np
from ase.io import read

ROOT = Path("/workspace/ni_al")
ROUND4 = ROOT / "data/al3ni_remediation_v1/round4_dft.extxyz"
CONTEXT_TRAIN = ROOT / "data/datasets/ni_al_combined127_train_89.extxyz"
CONTEXT_VALID = ROOT / "data/datasets/ni_al_combined127_validation_18.extxyz"
REPORT = ROOT / "data/al3ni_remediation_v1/round4_dft_outlier_review.txt"


def metrics_row(atoms):
    forces = np.asarray(atoms.get_forces(), dtype=float)
    stress = np.asarray(atoms.get_stress(voigt=True), dtype=float)
    return {
        "fmax": float(np.linalg.norm(forces, axis=1).max()),
        "frms": float(np.sqrt(np.mean(forces**2))),
        "stress_mag": float(np.linalg.norm(stress)),
    }


def percentile_rank(value, population):
    population = np.asarray(population, dtype=float)
    return float((population < value).sum()) / len(population) * 100.0


def main():
    frames = read(ROUND4, index=":")
    context = read(CONTEXT_TRAIN, index=":") + read(CONTEXT_VALID, index=":")

    context_by_phase = {}
    for a in context:
        phase = a.info["phase"]
        context_by_phase.setdefault(phase, []).append(metrics_row(a))

    lines = [
        "ROUND-4 DFT OUTLIER REVIEW (forces/stresses)",
        "=" * 46,
        f"Dataset: {ROUND4}",
        f"Frames screened: {len(frames)}",
        "",
        "SELF-POPULATION SCREEN: SKIPPED",
        "-" * 46,
        "n=2 total (1 config per phase) -- a same-batch MAD screen cannot produce a",
        "meaningful scale estimate at this size (median of 1 value has zero spread).",
        "Not run, not silently omitted.",
        "",
        "PHASE-CONTEXT PERCENTILE (vs combined-127 TRAIN+VALIDATION)",
        "-" * 46,
        f"{'config_id':<42s} {'phase':<8s} {'ctx_n':>5s} {'Fmax_pct':>9s} {'Frms_pct':>9s} {'stress_pct':>10s}",
    ]
    context_flags = []
    for a in frames:
        m = metrics_row(a)
        phase = a.info["phase"]
        pop = context_by_phase.get(phase, [])
        fmax_pop = [p["fmax"] for p in pop]
        frms_pop = [p["frms"] for p in pop]
        stress_pop = [p["stress_mag"] for p in pop]
        fmax_pct = percentile_rank(m["fmax"], fmax_pop)
        frms_pct = percentile_rank(m["frms"], frms_pop)
        stress_pct = percentile_rank(m["stress_mag"], stress_pop)
        lines.append(
            f"{a.info['config_id']:<42s} {phase:<8s} {len(pop):>5d} "
            f"{fmax_pct:>8.1f}% {frms_pct:>8.1f}% {stress_pct:>9.1f}%"
        )
        if fmax_pct >= 95.0 or frms_pct >= 95.0 or stress_pct >= 95.0:
            context_flags.append(a.info["config_id"])

    lines.append("")
    lines.append("Context flags (>=95th percentile of that phase's existing combined-127"
                  " TRAIN+VALIDATION population on any of Fmax/Frms/|stress|): "
                  + (", ".join(sorted(set(context_flags))) if context_flags else "none"))
    lines.append("")
    lines.append("cfg145_AlNi3_biaxial_yz_expansion has fmax=0 exactly -- same physically-correct")
    lines.append("symmetry-cancellation pattern already confirmed for round3's unrattled AlNi/AlNi3")
    lines.append("configs (cfg125, cfg139, cfg141): a homogeneous strain with no rattle keeps atoms")
    lines.append("at high-symmetry Wyckoff positions symmetry-pinned, so zero net force is the")
    lines.append("physically correct DFT result, not an extraction bug.")
    lines.append("")
    lines.append("Advisory only; no configuration removed or altered.")

    REPORT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
