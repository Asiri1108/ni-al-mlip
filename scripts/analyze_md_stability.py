#!/usr/bin/env python3
"""Stage D analysis: parse the NVT/NPT thermo trace out of
logs/lammps_stage_d/<phase>.log (produced by lammps_stage_d_run_phase.py)
and assess dynamical/mechanical stability -- with particular attention to
alpha-angle / yz-shear drift, since that is the mode tied to this project's
softest measured elastic constant (Al3Ni5 C44=33.15 GPa, see
configs/LAMMPS_STAGE_C_ELASTIC_STATUS.txt).

Deliberately reads the LAMMPS log text rather than re-deriving anything from
the summary JSON: the log is the full per-step (well, per-thermo_every-step)
trace, the JSON is only start/end snapshots. thermo_style in both
in.nvt_stability and in.npt_stability is:
  step temp pe ke etotal press pxx pyy pzz pxy pxz pyz lx ly lz xy xz yz vol
Each production stage is bounded in the log by print markers ("=== STAGE D
{NVT,NPT} PRODUCTION {START,END} ==="), and if a run dies mid-stage (lost
atoms, NaN, segfault) the corresponding END marker and/or "Loop time" line
will be missing -- this script detects that (CRASHED) rather than assuming
a clean run.

Cell-angle convention matches ASE's Atoms.cell.cellpar() (also used
throughout Stage B/C via lattice_compare_utils.cellpar_and_vpa): with LAMMPS
triclinic vectors a=(lx,0,0), b=(xy,ly,0), c=(xz,yz,lz),
  alpha = angle(b, c)   <- the yz/ly/lz-driven tilt; this is the one that
                           moved (90 -> ~98 deg) for Al3Ni5 in Stage B and
                           corresponds to Stage C's softest C44 mode.
  beta  = angle(a, c)
  gamma = angle(a, b)

Usage: analyze_md_stability.py PHASE [PHASE ...]
Writes results/lammps_stage_d/<phase>_stability_metrics.json per phase and
appends a combined human-readable report to
configs/LAMMPS_STAGE_D_MD_STABILITY_STATUS.txt (overwritten each run, not
appended across runs, so it always reflects exactly the phases requested
this invocation).
"""
import json
import math
import os
import re
import sys

import numpy as np

ROOT = "/workspace/ni_al"
LOG_DIR = f"{ROOT}/logs/lammps_stage_d"
RESULTS_DIR = f"{ROOT}/results/lammps_stage_d"
OUT = f"{ROOT}/configs/LAMMPS_STAGE_D_MD_STABILITY_STATUS.txt"

THERMO_COLS = ["step", "temp", "pe", "ke", "etotal", "press",
               "pxx", "pyy", "pzz", "pxy", "pxz", "pyz",
               "lx", "ly", "lz", "xy", "xz", "yz", "vol"]

# Flag thresholds -- deliberately explicit constants, not tuned per phase.
TEMP_CONCERN_FRAC = 0.5     # mean(back half) outside target*(1 +/- this) -> CONCERN
TEMP_INSTABILITY_FRAC = 2.0  # ... outside target*(1 +/- this) -> INSTABILITY
ANGLE_CONCERN_DEG = 10.0     # |angle drift from stage-start| -> CONCERN
ANGLE_INSTABILITY_DEG = 30.0  # ... -> INSTABILITY
VOL_CONCERN_FRAC = 0.20      # |volume/atom drift| -> CONCERN
VOL_INSTABILITY_FRAC = 0.50  # ... -> INSTABILITY
EQUIL_DISCARD_FRAC = 0.30    # fraction of each stage's samples treated as equilibration


def cellpar_angles(lx, ly, lz, xy, xz, yz):
    a = np.array([lx, 0.0, 0.0])
    b = np.array([xy, ly, 0.0])
    c = np.array([xz, yz, lz])

    def angle(u, v):
        cosang = np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v))
        cosang = np.clip(cosang, -1.0, 1.0)
        return math.degrees(math.acos(cosang))

    alpha = angle(b, c)
    beta = angle(a, c)
    gamma = angle(a, b)
    return alpha, beta, gamma


def parse_stage(log_lines, start_marker, end_marker):
    """Return (rows: dict[col] -> np.array, status: str) for one stage.
    status is one of 'OK', 'NO_START', 'CRASHED' (start found, end/Loop
    time not found -- run died mid-stage)."""
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


def analyze_stage(rows, target_temp_K):
    n = len(rows["step"])
    alpha = np.empty(n)
    beta = np.empty(n)
    gamma = np.empty(n)
    for i in range(n):
        alpha[i], beta[i], gamma[i] = cellpar_angles(
            rows["lx"][i], rows["ly"][i], rows["lz"][i],
            rows["xy"][i], rows["xz"][i], rows["yz"][i])

    finite_ok = bool(np.all(np.isfinite(rows["temp"])) and np.all(np.isfinite(rows["pe"]))
                      and np.all(np.isfinite(alpha)) and np.all(np.isfinite(rows["vol"])))

    discard = max(1, int(n * EQUIL_DISCARD_FRAC))
    back = slice(discard, n)

    temp_mean_back = float(np.mean(rows["temp"][back]))
    temp_std_back = float(np.std(rows["temp"][back]))

    vol0 = float(rows["vol"][0])
    vol_final = float(rows["vol"][-1])
    vol_drift_frac = (vol_final - vol0) / vol0

    alpha0, beta0, gamma0 = alpha[0], beta[0], gamma[0]
    alpha_drift = alpha - alpha0
    beta_drift = beta - beta0
    gamma_drift = gamma - gamma0
    max_abs_alpha_drift = float(np.max(np.abs(alpha_drift)))
    max_abs_beta_drift = float(np.max(np.abs(beta_drift)))
    max_abs_gamma_drift = float(np.max(np.abs(gamma_drift)))
    final_alpha_drift = float(alpha_drift[-1])

    # linear-fit slope of alpha vs step, back half only (post-equilibration trend)
    if n - discard >= 2:
        slope_alpha_deg_per_ps = float(np.polyfit(
            rows["step"][back] * 0.001, alpha[back], 1)[0])  # step*timestep(ps)=time; timestep=0.001 ps hardcoded to match protocol
    else:
        slope_alpha_deg_per_ps = None

    flags = []
    if not finite_ok:
        flags.append("INSTABILITY: non-finite value (NaN/Inf) in temp/pe/alpha/vol")

    temp_frac_dev = abs(temp_mean_back - target_temp_K) / target_temp_K
    if temp_frac_dev > TEMP_INSTABILITY_FRAC:
        flags.append(f"INSTABILITY: mean T (back {1-EQUIL_DISCARD_FRAC:.0%}) = {temp_mean_back:.1f} K, "
                      f">{TEMP_INSTABILITY_FRAC:.0%} off target {target_temp_K:.1f} K")
    elif temp_frac_dev > TEMP_CONCERN_FRAC:
        flags.append(f"CONCERN: mean T (back {1-EQUIL_DISCARD_FRAC:.0%}) = {temp_mean_back:.1f} K, "
                      f">{TEMP_CONCERN_FRAC:.0%} off target {target_temp_K:.1f} K")

    if max_abs_alpha_drift > ANGLE_INSTABILITY_DEG:
        flags.append(f"INSTABILITY: max |alpha drift| = {max_abs_alpha_drift:.2f} deg (> {ANGLE_INSTABILITY_DEG})")
    elif max_abs_alpha_drift > ANGLE_CONCERN_DEG:
        flags.append(f"CONCERN: max |alpha drift| = {max_abs_alpha_drift:.2f} deg (> {ANGLE_CONCERN_DEG})")

    if abs(vol_drift_frac) > VOL_INSTABILITY_FRAC:
        flags.append(f"INSTABILITY: volume drift = {vol_drift_frac:+.1%} (> {VOL_INSTABILITY_FRAC:.0%})")
    elif abs(vol_drift_frac) > VOL_CONCERN_FRAC:
        flags.append(f"CONCERN: volume drift = {vol_drift_frac:+.1%} (> {VOL_CONCERN_FRAC:.0%})")

    return {
        "n_samples": n,
        "finite_ok": finite_ok,
        "temp_mean_back_K": temp_mean_back,
        "temp_std_back_K": temp_std_back,
        "alpha0_deg": float(alpha0), "beta0_deg": float(beta0), "gamma0_deg": float(gamma0),
        "alpha_final_deg": float(alpha[-1]), "beta_final_deg": float(beta[-1]), "gamma_final_deg": float(gamma[-1]),
        "max_abs_alpha_drift_deg": max_abs_alpha_drift,
        "max_abs_beta_drift_deg": max_abs_beta_drift,
        "max_abs_gamma_drift_deg": max_abs_gamma_drift,
        "final_alpha_drift_deg": final_alpha_drift,
        "alpha_slope_deg_per_ps_back_half": slope_alpha_deg_per_ps,
        "vol0_A3": vol0,
        "vol_final_A3": vol_final,
        "vol_drift_frac": vol_drift_frac,
        "flags": flags,
    }


def verdict_of(all_flags):
    if any(f.startswith("INSTABILITY") for f in all_flags):
        return "INSTABILITY"
    if any(f.startswith("CONCERN") for f in all_flags):
        return "CONCERN"
    return "STABLE"


def analyze_phase(phase, target_temp_K=300.0):
    log_file = f"{LOG_DIR}/{phase}.log"
    if not os.path.exists(log_file):
        return {"phase": phase, "status": "NO_LOG", "log_file": log_file}

    with open(log_file) as fh:
        log_lines = fh.readlines()

    nvt_rows, nvt_status = parse_stage(log_lines, "STAGE D NVT PRODUCTION START", "STAGE D NVT PRODUCTION END")
    npt_rows, npt_status = parse_stage(log_lines, "STAGE D NPT PRODUCTION START", "STAGE D NPT PRODUCTION END")

    nvt_metrics = analyze_stage(nvt_rows, target_temp_K) if nvt_rows is not None else None
    npt_metrics = analyze_stage(npt_rows, target_temp_K) if npt_rows is not None else None

    all_flags = []
    if nvt_status != "OK":
        all_flags.append(f"INSTABILITY: NVT stage did not complete cleanly (status={nvt_status})")
    elif nvt_metrics:
        all_flags += [f"NVT: {f}" for f in nvt_metrics["flags"]]
    if npt_status != "OK":
        all_flags.append(f"INSTABILITY: NPT stage did not complete cleanly (status={npt_status})")
    elif npt_metrics:
        all_flags += [f"NPT: {f}" for f in npt_metrics["flags"]]

    # end-to-end angle drift: NPT's final alpha vs NVT's very first alpha
    # (i.e. drift across the whole production run, not just within-NPT)
    overall_alpha_drift_deg = None
    if nvt_metrics and npt_metrics:
        overall_alpha_drift_deg = npt_metrics["alpha_final_deg"] - nvt_metrics["alpha0_deg"]
        if abs(overall_alpha_drift_deg) > ANGLE_INSTABILITY_DEG:
            all_flags.append(f"INSTABILITY: overall (NVT start -> NPT end) alpha drift = "
                              f"{overall_alpha_drift_deg:+.2f} deg (> {ANGLE_INSTABILITY_DEG})")
        elif abs(overall_alpha_drift_deg) > ANGLE_CONCERN_DEG:
            all_flags.append(f"CONCERN: overall (NVT start -> NPT end) alpha drift = "
                              f"{overall_alpha_drift_deg:+.2f} deg (> {ANGLE_CONCERN_DEG})")

    verdict = verdict_of(all_flags)

    result = {
        "phase": phase,
        "log_file": log_file,
        "nvt_status": nvt_status,
        "npt_status": npt_status,
        "nvt_metrics": nvt_metrics,
        "npt_metrics": npt_metrics,
        "overall_alpha_drift_deg": overall_alpha_drift_deg,
        "flags": all_flags,
        "verdict": verdict,
    }
    return result


def fmt_stage_block(label, status, m):
    lines = [f"  --- {label}: status={status} ---"]
    if m is None:
        lines.append("    (no data parsed)")
        return lines
    lines.append(f"    samples={m['n_samples']}  finite_ok={m['finite_ok']}")
    lines.append(f"    T back-{1-EQUIL_DISCARD_FRAC:.0%} mean/std: {m['temp_mean_back_K']:.1f} / {m['temp_std_back_K']:.1f} K")
    lines.append(f"    alpha: start={m['alpha0_deg']:.4f} deg  final={m['alpha_final_deg']:.4f} deg  "
                 f"max|drift|={m['max_abs_alpha_drift_deg']:.4f} deg  final_drift={m['final_alpha_drift_deg']:+.4f} deg  "
                 f"back-half slope={m['alpha_slope_deg_per_ps_back_half']}")
    lines.append(f"    beta:  start={m['beta0_deg']:.4f} deg  final={m['beta_final_deg']:.4f} deg  max|drift|={m['max_abs_beta_drift_deg']:.4f} deg")
    lines.append(f"    gamma: start={m['gamma0_deg']:.4f} deg  final={m['gamma_final_deg']:.4f} deg  max|drift|={m['max_abs_gamma_drift_deg']:.4f} deg")
    lines.append(f"    volume/cell: start={m['vol0_A3']:.4f} A^3  final={m['vol_final_A3']:.4f} A^3  drift={m['vol_drift_frac']:+.2%}")
    if m["flags"]:
        for f in m["flags"]:
            lines.append(f"    {f}")
    else:
        lines.append("    no flags")
    return lines


def main():
    phases = sys.argv[1:]
    if not phases:
        print(f"usage: {sys.argv[0]} PHASE [PHASE ...]", file=sys.stderr)
        sys.exit(2)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    report_lines = ["LAMMPS STAGE D -- NVT/NPT MD STABILITY", ""]
    overall_verdicts = {}

    for phase in phases:
        result = analyze_phase(phase)
        overall_verdicts[phase] = result.get("verdict", result.get("status", "UNKNOWN"))

        metrics_path = f"{RESULTS_DIR}/{phase}_stability_metrics.json"
        with open(metrics_path, "w") as fh:
            json.dump(result, fh, indent=2)
        print(f"Wrote {metrics_path}")

        report_lines.append(f"=== {phase} ===")
        if "nvt_metrics" not in result:
            report_lines.append(f"  {result.get('status', 'UNKNOWN')}: {result.get('log_file')}")
            report_lines.append("")
            continue
        report_lines += fmt_stage_block("NVT", result["nvt_status"], result["nvt_metrics"])
        report_lines += fmt_stage_block("NPT", result["npt_status"], result["npt_metrics"])
        if result["overall_alpha_drift_deg"] is not None:
            report_lines.append(f"  overall alpha drift (NVT start -> NPT end): "
                                 f"{result['overall_alpha_drift_deg']:+.4f} deg")
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
