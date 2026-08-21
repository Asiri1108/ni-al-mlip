#!/usr/bin/env python3
"""Outlier review for Round-3 remediation DFT labels (forces/stresses).

Two screens, both advisory only -- nothing is removed or altered:

1. Self-population screen: identical method to
   validate_and_split_pilot25.py's robust_high_outliers() (median +
   8 * 1.4826 * MAD over the batch itself). Reused verbatim for
   consistency with the project's established convention.
2. Phase-context screen: round3 has only 1-4 members per phase (Al3Ni=1,
   Al3Ni5=2), too thin for #1 to mean much on its own. This compares each
   round3 frame's Fmax/Frms/|stress| against its phase's existing
   combined-113 TRAIN+VALIDATION population (93 frames) and reports the
   percentile rank, so a genuinely large value is visible even when
   round3 alone can't detect it.
"""

from pathlib import Path

import numpy as np
from ase.io import read

ROOT = Path("/workspace/ni_al")
ROUND3 = ROOT / "data/al3ni_remediation_v1/round3_dft.extxyz"
CONTEXT_TRAIN = ROOT / "data/datasets/ni_al_combined113_train_75.extxyz"
CONTEXT_VALID = ROOT / "data/datasets/ni_al_combined113_validation_18.extxyz"
REPORT = ROOT / "data/al3ni_remediation_v1/round3_dft_outlier_review.txt"


def metrics_row(atoms):
    forces = np.asarray(atoms.get_forces(), dtype=float)
    stress = np.asarray(atoms.get_stress(voigt=True), dtype=float)
    return {
        "fmax": float(np.linalg.norm(forces, axis=1).max()),
        "frms": float(np.sqrt(np.mean(forces**2))),
        "stress_mag": float(np.linalg.norm(stress)),
    }


def robust_high_outliers(values):
    """Verbatim from validate_and_split_pilot25.py."""
    array = np.asarray(list(values.values()), dtype=float)
    median = float(np.median(array))
    mad = float(np.median(np.abs(array - median)))
    if mad == 0.0:
        return []
    threshold = median + 8.0 * 1.4826 * mad
    return sorted(key for key, value in values.items() if value > threshold)


def percentile_rank(value, population):
    population = np.asarray(population, dtype=float)
    return float((population < value).sum()) / len(population) * 100.0


def main():
    frames = read(ROUND3, index=":")
    context = read(CONTEXT_TRAIN, index=":") + read(CONTEXT_VALID, index=":")

    rows = []
    for a in frames:
        m = metrics_row(a)
        m["config_id"] = a.info["config_id"]
        m["phase"] = a.info["phase"]
        m["config_type"] = a.info["config_type"]
        m["natoms"] = len(a)
        rows.append(m)

    context_by_phase = {}
    for a in context:
        phase = a.info["phase"]
        m = metrics_row(a)
        context_by_phase.setdefault(phase, []).append(m)

    fmax_values = {r["config_id"]: r["fmax"] for r in rows}
    frms_values = {r["config_id"]: r["frms"] for r in rows}
    stress_values = {r["config_id"]: r["stress_mag"] for r in rows}
    self_flags = {
        "maximum force": robust_high_outliers(fmax_values),
        "RMS force": robust_high_outliers(frms_values),
        "stress magnitude": robust_high_outliers(stress_values),
    }

    lines = [
        "ROUND-3 DFT OUTLIER REVIEW (forces/stresses)",
        "=" * 46,
        f"Dataset: {ROUND3}",
        f"Frames screened: {len(rows)}",
        "",
        "PER-CONFIGURATION METRICS",
        "-------------------------",
        f"{'config_id':<42s} {'phase':<8s} {'N':>2s} {'Fmax_eV/A':>12s} {'Frms_eV/A':>12s} {'|stress|_eV/A^3':>17s}",
    ]
    for r in rows:
        lines.append(
            f"{r['config_id']:<42s} {r['phase']:<8s} {r['natoms']:>2d} "
            f"{r['fmax']:>12.8f} {r['frms']:>12.8f} {r['stress_mag']:>17.8f}"
        )

    lines += ["", "SCREEN 1: SELF-POPULATION (n=14, identical method to Pilot-25's robust_high_outliers)", "-" * 87]
    for metric, flags in self_flags.items():
        lines.append(f"Robust extreme-high {metric} flags: " + (", ".join(flags) if flags else "none"))
    lines.append("Rule: median + 8 * 1.4826 * MAD over these 14 frames. Advisory only.")
    lines.append("CAVEAT: 3 of 5 phases have only 1-2 round3 members (Al3Ni=1, Al3Ni5=2, Al3Ni2=3);")
    lines.append("a same-batch MAD screen has very little power to flag anything at that n. See Screen 2.")

    lines += ["", "SCREEN 2: PHASE-CONTEXT PERCENTILE (vs combined-113 TRAIN+VALIDATION, n=93 total)", "-" * 87]
    lines.append(f"{'config_id':<42s} {'phase':<8s} {'ctx_n':>5s} {'Fmax_pct':>9s} {'Frms_pct':>9s} {'stress_pct':>10s}")
    context_flags = []
    for r in rows:
        phase = r["phase"]
        pop = context_by_phase.get(phase, [])
        if not pop:
            lines.append(f"{r['config_id']:<42s} {phase:<8s}  (no combined-113 frames for this phase)")
            continue
        fmax_pop = [p["fmax"] for p in pop]
        frms_pop = [p["frms"] for p in pop]
        stress_pop = [p["stress_mag"] for p in pop]
        fmax_pct = percentile_rank(r["fmax"], fmax_pop)
        frms_pct = percentile_rank(r["frms"], frms_pop)
        stress_pct = percentile_rank(r["stress_mag"], stress_pop)
        lines.append(
            f"{r['config_id']:<42s} {phase:<8s} {len(pop):>5d} "
            f"{fmax_pct:>8.1f}% {frms_pct:>8.1f}% {stress_pct:>9.1f}%"
        )
        if fmax_pct >= 95.0 or frms_pct >= 95.0 or stress_pct >= 95.0:
            context_flags.append(r["config_id"])
    lines.append("")
    lines.append("Context flags (>=95th percentile of that phase's existing combined-113 TRAIN+VALIDATION"
                  " population on any of Fmax/Frms/|stress|): " + (", ".join(sorted(set(context_flags))) if context_flags else "none"))
    lines.append("This is expected and by design: round3 configs were deliberately generated beyond the")
    lines.append("existing TRAIN ceiling to close coverage gaps (see ROUND3_BATCH_DESIGN_STATUS.md), so")
    lines.append("high percentile rank on strain-driven force/stress magnitude is the intended outcome,")
    lines.append("not evidence of a bad DFT run. Advisory only; no configuration removed or altered.")

    REPORT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
