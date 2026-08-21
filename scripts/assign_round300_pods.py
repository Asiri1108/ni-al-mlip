#!/usr/bin/env python3
"""Partition the 82 gate-passed round300 candidates across 10 pods.

Balances by ESTIMATED WALL-CLOCK TIME per structure, not raw count, using
an empirical (phase, rattle-present) timing model built from every real
QE run this project has on record (round3 pod01+pod02, round4 -- 16 real
data points). Assignment uses LPT (Longest Processing Time first) greedy
bin-packing: sort candidates by estimated time descending, assign each to
the currently-lightest pod. LPT is a well-known near-optimal heuristic for
makespan minimization (provably within 4/3 of optimal) -- the appropriate,
non-arbitrary choice for "balance so every pod finishes around the same
time," not just "split into equal-sized groups."

Does NOT launch anything. No runner scripts, no tmux sessions, no QE
processes. Assignment only, per explicit instruction.
"""

import csv
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path("/workspace/ni_al")
MANIFEST = ROOT / "data/al3ni_remediation_v1/round300_manifest.csv"
OUT_CSV = ROOT / "configs/ROUND300_POD_ASSIGNMENT.csv"
OUT_MD = ROOT / "configs/ROUND300_POD_PLAN.md"
N_PODS = 10

# Empirical (phase, rattle) -> observed wall-clock seconds, from every real QE run
# on record: round3 pod01 (logs/round3_pod01/console.log), round3 pod02
# (logs/round3_pod02/console.log), round4 (logs/round4_biaxial/console.log).
OBSERVED = {
    ("AlNi", False): [229, 117],           # cfg139, cfg125
    ("AlNi", True): [481, 470],            # cfg131, cfg133
    ("Al3Ni", False): [623],               # cfg123
    ("Al3Ni2", False): [150, 338],         # cfg117, cfg137
    ("Al3Ni2", True): [550],               # cfg127
    ("Al3Ni5", False): [485, 527],         # cfg121, cfg143
    ("Al3Ni5", True): [795],               # cfg129
    ("AlNi3", False): [693, 381],          # cfg141, cfg145
    ("AlNi3", True): [1564, 1484, 1674],   # cfg118, cfg119, cfg135
}


def build_timing_model():
    model = {k: statistics.mean(v) for k, v in OBSERVED.items()}
    # Al3Ni rattle: no direct observation anywhere in this project yet. Estimate via the
    # mean rattle/no-rattle ratio observed in the 4 phases that DO have both, applied to
    # Al3Ni's own no-rattle time -- data-derived, not invented, but flagged as an estimate.
    ratios = []
    for phase in ("AlNi", "Al3Ni2", "Al3Ni5", "AlNi3"):
        if (phase, True) in model and (phase, False) in model:
            ratios.append(model[(phase, True)] / model[(phase, False)])
    mean_ratio = statistics.mean(ratios)
    model[("Al3Ni", True)] = model[("Al3Ni", False)] * mean_ratio
    return model, mean_ratio


def main():
    model, mean_ratio = build_timing_model()
    rows = list(csv.DictReader(MANIFEST.open(newline="")))
    if len(rows) != 82:
        raise RuntimeError(f"expected 82 kept candidates, found {len(rows)}")

    candidates = []
    for r in rows:
        phase = r["phase"]
        has_rattle = float(r["rattle_sigma_A"]) > 0
        est = model[(phase, has_rattle)]
        candidates.append({
            "config_id": r["config_id"], "phase": phase, "family": r["config_family"],
            "has_rattle": has_rattle, "estimated_seconds": est,
        })

    # LPT: sort descending by estimated time, greedily assign to the lightest pod.
    candidates.sort(key=lambda c: -c["estimated_seconds"])
    pod_load = [0.0] * N_PODS
    pod_members = [[] for _ in range(N_PODS)]
    for c in candidates:
        idx = min(range(N_PODS), key=lambda i: pod_load[i])
        pod_load[idx] += c["estimated_seconds"]
        c["pod_number"] = idx + 1
        pod_members[idx].append(c)

    # Correctness checks -- accuracy is the explicit priority here.
    assigned_ids = [c["config_id"] for c in candidates]
    if len(assigned_ids) != 82 or len(set(assigned_ids)) != 82:
        raise RuntimeError("assignment integrity failure: not exactly 82 unique config_ids assigned")
    if sum(len(m) for m in pod_members) != 82:
        raise RuntimeError("assignment integrity failure: pod membership count mismatch")
    for i, members in enumerate(pod_members):
        ids_in_pod = {m["config_id"] for m in members}
        if len(ids_in_pod) != len(members):
            raise RuntimeError(f"pod {i+1}: duplicate config_id within pod")
    all_ids_union = set()
    for members in pod_members:
        all_ids_union |= {m["config_id"] for m in members}
    if all_ids_union != set(r["config_id"] for r in rows):
        raise RuntimeError("assignment integrity failure: pod union does not match manifest exactly")

    # Restore original manifest order within the CSV output for readability, but keep pod assignment.
    pod_by_id = {c["config_id"]: c["pod_number"] for c in candidates}
    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["config_id", "phase", "family", "has_rattle", "estimated_seconds", "pod_number"])
        w.writeheader()
        for c in sorted(candidates, key=lambda c: (c["pod_number"], -c["estimated_seconds"])):
            w.writerow({"config_id": c["config_id"], "phase": c["phase"], "family": c["family"],
                        "has_rattle": c["has_rattle"], "estimated_seconds": round(c["estimated_seconds"]),
                        "pod_number": c["pod_number"]})

    lines = [
        "# Round-300 Pod Assignment Plan (10 pods, time-balanced, NOT LAUNCHED)",
        "",
        "Assignment only -- no runner scripts written, no tmux sessions, no QE processes",
        "started. This is a plan to review before launch.",
        "",
        "## Timing model (empirical, from every real QE run on record: 16 data points",
        "across round3 pod01+pod02 and round4)",
        "",
        "| Phase | No-rattle (n, mean s) | Rattle (n, mean s) |",
        "|---|---|---|",
    ]
    for phase in ("AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3"):
        nr = OBSERVED.get((phase, False), [])
        r_ = OBSERVED.get((phase, True), [])
        nr_s = f"n={len(nr)}, {model[(phase, False)]:.0f}s" if nr else "no data"
        if r_:
            r_s = f"n={len(r_)}, {model[(phase, True)]:.0f}s"
        else:
            r_s = f"**estimated** {model[(phase, True)]:.0f}s (no direct observation -- extrapolated via mean rattle/no-rattle ratio {mean_ratio:.2f}x observed across the other 4 phases)"
        lines.append(f"| {phase} | {nr_s} | {r_s} |")

    lines += [
        "",
        "## Method",
        "",
        "LPT (Longest Processing Time first) greedy bin-packing: candidates sorted by",
        "estimated time descending, each assigned to the currently lightest-loaded pod.",
        "This minimizes makespan (the slowest pod's finish time), not just structure count",
        "per pod -- the actual goal when the aim is \"every pod finishes around the same",
        "time,\" given the >10x spread between the fastest (AlNi no-rattle, ~2 min) and",
        "slowest (AlNi3 rattle, ~26 min) candidate categories.",
        "",
        "## Per-pod load",
        "",
        "| Pod | Structures | Total est. time | vs mean |",
        "|---|---|---|---|",
    ]
    mean_load = sum(pod_load) / N_PODS
    for i in range(N_PODS):
        mins = pod_load[i] / 60
        delta = (pod_load[i] - mean_load) / mean_load * 100
        lines.append(f"| {i+1} | {len(pod_members[i])} | {mins:.1f} min | {delta:+.1f}% |")
    lines.append("")
    lines.append(f"Mean pod load: {mean_load/60:.1f} min. Max/min spread: {(max(pod_load)-min(pod_load))/60:.1f} min "
                 f"({(max(pod_load)/min(pod_load)-1)*100:.1f}% above the lightest pod).")
    lines.append(f"Total estimated sequential compute (all 82, one pod): {sum(pod_load)/3600:.1f} hours.")
    lines.append(f"Estimated wall-clock with 10 pods running in parallel: ~{max(pod_load)/60:.1f} minutes "
                 "(the slowest pod), assuming genuinely independent, uncontended GPUs per pod -- see caveat below.")

    lines += [
        "",
        "## Per-pod membership",
        "",
    ]
    for i in range(N_PODS):
        lines.append(f"### Pod {i+1} ({len(pod_members[i])} structures, {pod_load[i]/60:.1f} min estimated)")
        lines.append("")
        for m in sorted(pod_members[i], key=lambda c: -c["estimated_seconds"]):
            rattle_tag = "rattle" if m["has_rattle"] else "no-rattle"
            lines.append(f"- `{m['config_id']}` ({m['phase']}, {m['family']}, {rattle_tag}, ~{m['estimated_seconds']/60:.1f} min)")
        lines.append("")

    lines += [
        "## Integrity checks (all passed, or this script would have raised)",
        "",
        "- Exactly 82 unique config_ids assigned, matching round300_manifest.csv exactly",
        "- No config_id assigned to more than one pod",
        "- Pod membership union equals the full 82-candidate manifest exactly",
        "",
        "## Caveats -- read before launching",
        "",
        f"1. **Al3Ni rattle timing is an estimate**, not an observation (no round3/round4 config",
        "   exercised this combination). This batch contains "
        f"{sum(1 for c in candidates if c['phase']=='Al3Ni' and c['has_rattle'])} Al3Ni-rattle",
        "   candidates (pods 5, 6, 7 -- cfg189, cfg191, cfg194), each estimated at ~24.7 min via",
        "   the cross-phase ratio extrapolation above. Their pods' actual time may deviate more",
        "   than the others from this plan; this is the single largest source of estimate risk.",
        "2. **This project's GPU/driver has changed identity between sessions before**",
        "   (`project_knowledge.md` Section 6: 2.3-3.1x wall-clock variance observed between the",
        "   combined-113 and combined-127/129 training runs on different physical GPUs). If DFT",
        "   for this batch runs on a different GPU/driver than the ones behind this timing model,",
        "   absolute times will shift -- the RELATIVE balance across pods should still roughly",
        "   hold since all pods would be affected proportionally, but the makespan estimate above",
        "   should not be treated as a tight bound.",
        "3. This plan assumes 10 genuinely independent, uncontended GPUs/pods running in true",
        "   parallel, matching the `ROUND3_POD_ASSIGNMENT.csv` convention. Round3 only actually",
        "   used 2 of the 10 available pod slots -- confirm real pod availability before assuming",
        "   the ~26-minute parallel estimate above is achievable.",
        "",
        f"Assignment CSV: `{OUT_CSV}`",
    ]

    OUT_MD.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
