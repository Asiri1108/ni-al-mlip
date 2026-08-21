#!/usr/bin/env python3
"""Stage D-2 analysis: parse the single-stage NPT thermo trace out of
logs/lammps_stage_d2/<phase>.log (produced by lammps_stage_d2_run_phase.py)
for the 3 supercell small-cell-remediation phases (AlNi, AlNi3, Al3Ni2) and
report:
  - thermal expansion (0 K -> 300 K), vs literature for AlNi/AlNi3 only
  - beta/gamma cell-angle drift (now statistically meaningful at 100-200
    atoms, unlike Stage D's primitive-cell numbers for these 3 phases)
  - per-species (Al vs Ni) MSD trend, to distinguish vibration from
    diffusion/melting

REFERENCE HONESTY: Al3Ni2 has no literature thermal-expansion reference
available (found or recalled) -- reported UNVALIDATED, same convention as
Stage C's Al3Ni/Al3Ni2/Al3Ni5 elastic constants. AlNi/AlNi3 references
below are cited with their actual provenance (live-searched this session,
or recalled/not independently verified this session) -- see LITERATURE
dict; do not treat a "recalled" entry as session-verified fact.

Cell-angle convention matches ASE's Atoms.cell.cellpar() (same as Stage
B/C/D via lattice_compare_utils.cellpar_and_vpa): LAMMPS triclinic vectors
a=(lx,0,0), b=(xy,ly,0), c=(xz,yz,lz); alpha=angle(b,c), beta=angle(a,c),
gamma=angle(a,b).

Usage: analyze_supercell_md.py PHASE [PHASE ...]
Writes results/lammps_stage_d2/<phase>_supercell_metrics.json per phase and
a combined human-readable report to
configs/LAMMPS_STAGE_D2_SUPERCELL_MD_STATUS.txt (overwritten each run to
reflect exactly the phases requested this invocation).
"""
import json
import math
import os
import sys

import numpy as np

ROOT = "/workspace/ni_al"
LOG_DIR = f"{ROOT}/logs/lammps_stage_d2"
RESULTS_DIR = f"{ROOT}/results/lammps_stage_d2"
OUT = f"{ROOT}/configs/LAMMPS_STAGE_D2_SUPERCELL_MD_STATUS.txt"

THERMO_COLS = ["step", "temp", "pe", "ke", "etotal", "press",
               "pxx", "pyy", "pzz", "pxy", "pxz", "pyz",
               "lx", "ly", "lz", "xy", "xz", "yz", "vol",
               "msd_Al", "msd_Ni"]

TARGET_TEMP_K = 300.0
EQUIL_DISCARD_FRAC = 0.30

TEMP_CONCERN_FRAC = 0.5
TEMP_INSTABILITY_FRAC = 2.0
ANGLE_CONCERN_DEG = 10.0
ANGLE_INSTABILITY_DEG = 30.0
VOL_CONCERN_FRAC = 0.20      # this is thermal EXPANSION we expect a small +ve number;
VOL_INSTABILITY_FRAC = 0.50  # these thresholds only catch genuinely large/pathological drift
MSD_CONCERN_A2 = 1.0          # final total MSD above this (typical vibrational amplitude
MSD_INSTABILITY_A2 = 5.0      # at 300 K is well under 1 A^2 for a stable solid) -- heuristic,
MSD_SLOPE_CONCERN_A2_PER_PS = 0.02  # not a literature-calibrated number; stated as such.

# LITERATURE reference values for linear thermal expansion coefficient
# (alpha, K^-1) near room temperature. Each entry states its own actual
# provenance -- do not treat "recalled" as session-verified.
LITERATURE = {
    "AlNi": [
        {
            "label": "NiAl-Mo eutectic composite, perpendicular to fiber direction, "
                     "RT-800C average (NOT pure single-crystal stoichiometric B2 NiAl, "
                     "and spans a much wider T range than this run's 0->300 K)",
            "alpha_per_K": 16.0e-6,
            "provenance": "VERIFIED via live web search this session (2026-08-19): "
                          "'Thermal-expansion behavior of a directionally solidified "
                          "NiAl-Mo composite investigated by neutron diffraction and "
                          "dilatometry' (ResearchGate/ScienceDirect).",
        },
        {
            "label": "near-stoichiometric B2 NiAl, commonly cited near room temperature "
                     "in the intermetallics literature (e.g. the Miracle 1993 NiAl review "
                     "lineage)",
            "alpha_per_K": 13.0e-6,
            "provenance": "RECALLED, NOT independently verified this session -- the "
                          "primary source (Miracle, Int. Mater. Rev. 1993) was paywalled/"
                          "bot-blocked when fetched this session; treat as background "
                          "domain knowledge, not a session-verified citation.",
        },
    ],
    "AlNi3": [
        {
            "label": "Ni3Al (gamma-prime, L1_2), commonly reported near room temperature, "
                     "consistent with its close CTE match to the Ni-rich gamma matrix in "
                     "superalloys (the physical basis of gamma/gamma-prime coherency)",
            "alpha_per_K": 12.5e-6,
            "provenance": "RECALLED, NOT independently verified this session -- a live "
                          "web search this session found only an unsourced aggregator "
                          "paraphrase (~12e-6/K, no retrievable primary citation), and the "
                          "one directly on-topic paper found (Ni3Al thermal expansion by "
                          "XRD/dilatometry, IOPscience 1989) was blocked by an anti-bot "
                          "redirect before its content could be retrieved. Treat as "
                          "background domain knowledge, not a session-verified citation.",
        },
    ],
    "Al3Ni2": None,  # UNVALIDATED -- no reference found or recalled, same convention as Stage C
}


def cellpar_angles(lx, ly, lz, xy, xz, yz):
    a = np.array([lx, 0.0, 0.0])
    b = np.array([xy, ly, 0.0])
    c = np.array([xz, yz, lz])

    def angle(u, v):
        cosang = np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v))
        cosang = np.clip(cosang, -1.0, 1.0)
        return math.degrees(math.acos(cosang))

    return angle(b, c), angle(a, c), angle(a, b)


def parse_stage(log_lines, start_marker, end_marker):
    try:
        start_idx = next(i for i, l in enumerate(log_lines) if start_marker in l)
    except StopIteration:
        return None, "NO_START"

    end_idx = None
    for i in range(start_idx, len(log_lines)):
        if end_marker in log_lines[i]:
            end_idx = i
            break
    region = log_lines[start_idx:end_idx] if end_idx is not None else log_lines[start_idx:]

    header_idx = None
    for i, l in enumerate(region):
        if l.strip().split() and l.strip().split()[0] == "Step":
            header_idx = i
            break
    if header_idx is None:
        return None, "CRASHED"

    data_rows = []
    for l in region[header_idx + 1:]:
        s = l.strip()
        if not s:
            continue
        if s.startswith("Loop time"):
            break
        parts = s.split()
        if len(parts) != len(THERMO_COLS):
            break
        try:
            data_rows.append([float(x) for x in parts])
        except ValueError:
            break

    status = "OK" if end_idx is not None else "CRASHED"
    if not data_rows:
        return None, "CRASHED"

    arr = np.array(data_rows)
    rows = {col: arr[:, j] for j, col in enumerate(THERMO_COLS)}
    return rows, status


def analyze_phase(phase, natoms, n_al, n_ni, vol0_per_atom):
    log_file = f"{LOG_DIR}/{phase}.log"
    if not os.path.exists(log_file):
        return {"phase": phase, "status": "NO_LOG", "log_file": log_file}

    with open(log_file) as fh:
        log_lines = fh.readlines()

    rows, status = parse_stage(log_lines, "STAGE D-2 NPT PRODUCTION START", "STAGE D-2 NPT PRODUCTION END")
    if rows is None:
        return {"phase": phase, "status": status, "log_file": log_file}

    n = len(rows["step"])
    time_ps = rows["step"] * 0.001  # timestep hardcoded to match protocol (1 fs)

    alpha = np.empty(n); beta = np.empty(n); gamma = np.empty(n)
    for i in range(n):
        alpha[i], beta[i], gamma[i] = cellpar_angles(
            rows["lx"][i], rows["ly"][i], rows["lz"][i],
            rows["xy"][i], rows["xz"][i], rows["yz"][i])

    finite_ok = bool(np.all(np.isfinite(rows["temp"])) and np.all(np.isfinite(rows["pe"]))
                      and np.all(np.isfinite(alpha)) and np.all(np.isfinite(rows["vol"]))
                      and np.all(np.isfinite(rows["msd_Al"])) and np.all(np.isfinite(rows["msd_Ni"])))

    discard = max(1, int(n * EQUIL_DISCARD_FRAC))
    back = slice(discard, n)

    temp_mean_back = float(np.mean(rows["temp"][back]))
    temp_std_back = float(np.std(rows["temp"][back]))

    vol_per_atom = rows["vol"] / natoms
    vol_per_atom_mean_back = float(np.mean(vol_per_atom[back]))
    vol_per_atom_std_back = float(np.std(vol_per_atom[back]))
    thermal_expansion_frac = (vol_per_atom_mean_back - vol0_per_atom) / vol0_per_atom
    # linear CTE from volumetric, valid strictly for isotropic (cubic) expansion;
    # 0 K -> back-half-mean-300K, so divide by the nominal 300 K delta-T.
    volumetric_cte_per_K = thermal_expansion_frac / TARGET_TEMP_K
    linear_cte_per_K = volumetric_cte_per_K / 3.0

    alpha0, beta0, gamma0 = alpha[0], beta[0], gamma[0]
    max_abs_alpha_drift = float(np.max(np.abs(alpha - alpha0)))
    max_abs_beta_drift = float(np.max(np.abs(beta - beta0)))
    max_abs_gamma_drift = float(np.max(np.abs(gamma - gamma0)))
    final_alpha_drift = float(alpha[-1] - alpha0)
    final_beta_drift = float(beta[-1] - beta0)
    final_gamma_drift = float(gamma[-1] - gamma0)

    msd_al_final = float(rows["msd_Al"][-1])
    msd_ni_final = float(rows["msd_Ni"][-1])
    msd_al_mean_back = float(np.mean(rows["msd_Al"][back]))
    msd_ni_mean_back = float(np.mean(rows["msd_Ni"][back]))
    if n - discard >= 2:
        msd_al_slope = float(np.polyfit(time_ps[back], rows["msd_Al"][back], 1)[0])
        msd_ni_slope = float(np.polyfit(time_ps[back], rows["msd_Ni"][back], 1)[0])
    else:
        msd_al_slope = msd_ni_slope = None

    flags = []
    if not finite_ok:
        flags.append("INSTABILITY: non-finite value (NaN/Inf) in temp/pe/alpha/vol/MSD")

    temp_frac_dev = abs(temp_mean_back - TARGET_TEMP_K) / TARGET_TEMP_K
    if temp_frac_dev > TEMP_INSTABILITY_FRAC:
        flags.append(f"INSTABILITY: mean T (back {1-EQUIL_DISCARD_FRAC:.0%}) = {temp_mean_back:.1f} K, "
                      f">{TEMP_INSTABILITY_FRAC:.0%} off target")
    elif temp_frac_dev > TEMP_CONCERN_FRAC:
        flags.append(f"CONCERN: mean T (back {1-EQUIL_DISCARD_FRAC:.0%}) = {temp_mean_back:.1f} K, "
                      f">{TEMP_CONCERN_FRAC:.0%} off target")

    if max_abs_alpha_drift > ANGLE_INSTABILITY_DEG:
        flags.append(f"INSTABILITY: max |alpha drift| = {max_abs_alpha_drift:.2f} deg")
    elif max_abs_alpha_drift > ANGLE_CONCERN_DEG:
        flags.append(f"CONCERN: max |alpha drift| = {max_abs_alpha_drift:.2f} deg")
    if max_abs_beta_drift > ANGLE_INSTABILITY_DEG:
        flags.append(f"INSTABILITY: max |beta drift| = {max_abs_beta_drift:.2f} deg")
    elif max_abs_beta_drift > ANGLE_CONCERN_DEG:
        flags.append(f"CONCERN: max |beta drift| = {max_abs_beta_drift:.2f} deg")
    if max_abs_gamma_drift > ANGLE_INSTABILITY_DEG:
        flags.append(f"INSTABILITY: max |gamma drift| = {max_abs_gamma_drift:.2f} deg")
    elif max_abs_gamma_drift > ANGLE_CONCERN_DEG:
        flags.append(f"CONCERN: max |gamma drift| = {max_abs_gamma_drift:.2f} deg")

    if abs(thermal_expansion_frac) > VOL_INSTABILITY_FRAC:
        flags.append(f"INSTABILITY: volume/atom drift vs 0K = {thermal_expansion_frac:+.1%}")
    elif abs(thermal_expansion_frac) > VOL_CONCERN_FRAC:
        flags.append(f"CONCERN: volume/atom drift vs 0K = {thermal_expansion_frac:+.1%}")

    for label, msd_final, msd_slope in (("Al", msd_al_final, msd_al_slope), ("Ni", msd_ni_final, msd_ni_slope)):
        if msd_final > MSD_INSTABILITY_A2:
            flags.append(f"INSTABILITY: {label} final MSD = {msd_final:.3f} A^2 (> {MSD_INSTABILITY_A2}, "
                          f"consistent with diffusion/melting, not vibration)")
        elif msd_final > MSD_CONCERN_A2 or (msd_slope is not None and msd_slope > MSD_SLOPE_CONCERN_A2_PER_PS):
            flags.append(f"CONCERN: {label} MSD final={msd_final:.3f} A^2, "
                          f"back-half slope={msd_slope} A^2/ps (check for early diffusion)")

    verdict = "STABLE"
    if any(f.startswith("INSTABILITY") for f in flags):
        verdict = "INSTABILITY"
    elif any(f.startswith("CONCERN") for f in flags):
        verdict = "CONCERN"

    return {
        "phase": phase, "status": status, "log_file": log_file,
        "n_samples": n, "finite_ok": finite_ok, "natoms": natoms, "n_Al": n_al, "n_Ni": n_ni,
        "temp_mean_back_K": temp_mean_back, "temp_std_back_K": temp_std_back,
        "vol0_per_atom_A3": vol0_per_atom,
        "vol_per_atom_mean_back_A3": vol_per_atom_mean_back,
        "vol_per_atom_std_back_A3": vol_per_atom_std_back,
        "thermal_expansion_frac_0K_to_300K": thermal_expansion_frac,
        "volumetric_cte_per_K": volumetric_cte_per_K,
        "linear_cte_per_K_from_volumetric": linear_cte_per_K,
        "alpha0_deg": float(alpha0), "beta0_deg": float(beta0), "gamma0_deg": float(gamma0),
        "alpha_final_deg": float(alpha[-1]), "beta_final_deg": float(beta[-1]), "gamma_final_deg": float(gamma[-1]),
        "max_abs_alpha_drift_deg": max_abs_alpha_drift,
        "max_abs_beta_drift_deg": max_abs_beta_drift,
        "max_abs_gamma_drift_deg": max_abs_gamma_drift,
        "final_alpha_drift_deg": final_alpha_drift,
        "final_beta_drift_deg": final_beta_drift,
        "final_gamma_drift_deg": final_gamma_drift,
        "msd_Al_final_A2": msd_al_final, "msd_Ni_final_A2": msd_ni_final,
        "msd_Al_mean_back_A2": msd_al_mean_back, "msd_Ni_mean_back_A2": msd_ni_mean_back,
        "msd_Al_slope_A2_per_ps_back_half": msd_al_slope,
        "msd_Ni_slope_A2_per_ps_back_half": msd_ni_slope,
        "flags": flags,
        "verdict": verdict,
    }


def fmt_literature_block(phase, result):
    lines = []
    refs = LITERATURE.get(phase)
    if refs is None:
        lines.append("  REFERENCE: UNVALIDATED -- no literature thermal-expansion reference "
                      "found or recalled for this phase (same convention as Stage C's "
                      "Al3Ni/Al3Ni2/Al3Ni5 elastic constants). Reported as a model "
                      "prediction only.")
        return lines
    lines.append(f"  Model (this run): linear CTE (from volumetric/3, isotropic-expansion "
                 f"assumption) = {result['linear_cte_per_K_from_volumetric']*1e6:.3f} x10^-6 /K "
                 f"(volumetric = {result['volumetric_cte_per_K']*1e6:.3f} x10^-6 /K, "
                 f"thermal expansion 0K->300K = {result['thermal_expansion_frac_0K_to_300K']:+.3%})")
    for ref in refs:
        model_val = result["linear_cte_per_K_from_volumetric"]
        pct_dev = (model_val - ref["alpha_per_K"]) / ref["alpha_per_K"] * 100.0
        lines.append(f"  vs {ref['label']}: literature alpha={ref['alpha_per_K']*1e6:.2f} x10^-6 /K "
                     f"-- model % dev = {pct_dev:+.1f}%")
        lines.append(f"    provenance: {ref['provenance']}")
    return lines


def main():
    phases = sys.argv[1:]
    if not phases:
        print(f"usage: {sys.argv[0]} PHASE [PHASE ...]", file=sys.stderr)
        sys.exit(2)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    report_lines = ["LAMMPS STAGE D-2 -- SUPERCELL NPT MD (small-cell remediation: "
                    "AlNi, AlNi3, Al3Ni2)", ""]
    overall_verdicts = {}

    for phase in phases:
        summary_path = f"{RESULTS_DIR}/{phase}_summary.json"
        if not os.path.exists(summary_path):
            print(f"SKIP {phase}: no {summary_path}", file=sys.stderr)
            overall_verdicts[phase] = "NO_SUMMARY"
            report_lines.append(f"=== {phase} ===\n  NO SUMMARY JSON -- phase did not complete\n")
            continue
        with open(summary_path) as fh:
            summary = json.load(fh)

        result = analyze_phase(phase, summary["natoms"], summary["n_Al"], summary["n_Ni"],
                                summary["primitive_relax"]["volume_per_atom_A3"])
        overall_verdicts[phase] = result.get("verdict", result.get("status", "UNKNOWN"))

        metrics_path = f"{RESULTS_DIR}/{phase}_supercell_metrics.json"
        with open(metrics_path, "w") as fh:
            json.dump(result, fh, indent=2)
        print(f"Wrote {metrics_path}")

        report_lines.append(f"=== {phase} ({summary['natoms']} atoms: {summary['n_Al']} Al, "
                            f"{summary['n_Ni']} Ni, replication {summary['replication']}) ===")
        if "n_samples" not in result:
            report_lines.append(f"  {result.get('status', 'UNKNOWN')}: {result.get('log_file')}")
            report_lines.append("")
            continue
        report_lines.append(f"  samples={result['n_samples']}  finite_ok={result['finite_ok']}")
        report_lines.append(f"  T back-{1-EQUIL_DISCARD_FRAC:.0%} mean/std: "
                            f"{result['temp_mean_back_K']:.1f} / {result['temp_std_back_K']:.1f} K")
        report_lines.append(f"  volume/atom: 0K={result['vol0_per_atom_A3']:.4f} A^3  "
                            f"300K mean={result['vol_per_atom_mean_back_A3']:.4f}+/-"
                            f"{result['vol_per_atom_std_back_A3']:.4f} A^3  "
                            f"thermal expansion={result['thermal_expansion_frac_0K_to_300K']:+.3%}")
        report_lines += fmt_literature_block(phase, result)
        report_lines.append(f"  alpha: start={result['alpha0_deg']:.4f}  final={result['alpha_final_deg']:.4f}  "
                            f"max|drift|={result['max_abs_alpha_drift_deg']:.4f} deg")
        report_lines.append(f"  beta:  start={result['beta0_deg']:.4f}  final={result['beta_final_deg']:.4f}  "
                            f"max|drift|={result['max_abs_beta_drift_deg']:.4f} deg")
        report_lines.append(f"  gamma: start={result['gamma0_deg']:.4f}  final={result['gamma_final_deg']:.4f}  "
                            f"max|drift|={result['max_abs_gamma_drift_deg']:.4f} deg")
        report_lines.append(f"  MSD Al: final={result['msd_Al_final_A2']:.4f} A^2  "
                            f"back-half mean={result['msd_Al_mean_back_A2']:.4f} A^2  "
                            f"back-half slope={result['msd_Al_slope_A2_per_ps_back_half']} A^2/ps")
        report_lines.append(f"  MSD Ni: final={result['msd_Ni_final_A2']:.4f} A^2  "
                            f"back-half mean={result['msd_Ni_mean_back_A2']:.4f} A^2  "
                            f"back-half slope={result['msd_Ni_slope_A2_per_ps_back_half']} A^2/ps")
        if result["flags"]:
            for f in result["flags"]:
                report_lines.append(f"  {f}")
        else:
            report_lines.append("  no flags")
        report_lines.append(f"  VERDICT: {result['verdict']}")
        report_lines.append("")

    report_lines.append("SUMMARY")
    for phase, v in overall_verdicts.items():
        report_lines.append(f"  {phase}: {v}")
    report_lines.append("")

    with open(OUT, "w") as fh:
        fh.write("\n".join(report_lines) + "\n")
    print(f"\nWrote {OUT}")
    print("\n".join(report_lines))


if __name__ == "__main__":
    main()
