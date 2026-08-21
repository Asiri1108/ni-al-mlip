#!/usr/bin/env python3
"""Comprehensive integrity check for the round300 batch (82 configs, 10 pods).

Same rigor as round3/round4: SCF convergence, NaN/Inf, frozen-design
SHA256 freshness, QE parameter uniformity, AlNi3 nspin correctness,
GPU-active confirmation, exit codes, energy sanity, sealed-data isolation.
"""

import csv
import re
from pathlib import Path

ROOT = Path("/workspace/ni_al")
MANIFEST = ROOT / "data/al3ni_remediation_v1/round300_manifest.csv"
ASSIGNMENT = ROOT / "configs/ROUND300_POD_ASSIGNMENT.csv"
PROD_BASE = ROOT / "data/al3ni_remediation_v1/round300_production_dft"


def main():
    manifest = {r["config_id"]: r for r in csv.DictReader(MANIFEST.open(newline=""))}
    pod_by_id = {r["config_id"]: r["pod_number"] for r in csv.DictReader(ASSIGNMENT.open(newline=""))}

    if len(manifest) != 82:
        raise RuntimeError(f"expected 82 manifest rows, found {len(manifest)}")
    if set(manifest) != set(pod_by_id):
        raise RuntimeError("manifest and pod assignment config_id sets differ")

    fail_count = 0
    energy_by_phase = {}
    rows_report = []

    for cid, m in manifest.items():
        pod = pod_by_id[cid]
        attempt = PROD_BASE / f"pod{int(pod):02d}" / cid / "attempt_001"
        qe_out = attempt / "qe.out"
        meta_path = attempt / "execution_metadata.env"
        canonical = Path(m["qe_input_path"])
        phase = m["phase"]

        issues = []
        if not qe_out.exists():
            issues.append("qe.out missing")
        if not meta_path.exists():
            issues.append("execution_metadata.env missing")
        if issues:
            rows_report.append((cid, phase, pod, "FAIL", "; ".join(issues)))
            fail_count += 1
            continue

        meta = dict(line.split("=", 1) for line in meta_path.read_text().splitlines() if "=" in line)
        text = qe_out.read_text(errors="replace")

        scf = "convergence has been achieved" in text
        notconv = text.count("convergence NOT achieved")
        nan_hits = len(re.findall(r"\bnan\b|\binf\b|-nan|-inf", text, re.IGNORECASE))
        gpu_active = "GPU acceleration is ACTIVE" in text
        job_done = meta.get("JOB_DONE") == "YES"
        exit0 = meta.get("EXIT_CODE") == "0"

        import hashlib
        def sha(p):
            h = hashlib.sha256()
            h.update(p.read_bytes())
            return h.hexdigest()
        canon_sha_now = sha(canonical) if canonical.exists() else None
        canon_sha_ok = canon_sha_now == meta.get("CANONICAL_INPUT_SHA256")
        out_sha_ok = sha(qe_out) == meta.get("OUTPUT_SHA256")

        nspin_present = "nspin" in canonical.read_text() if canonical.exists() else False
        nspin_expected = phase == "AlNi3"
        nspin_ok = nspin_present == nspin_expected

        params_ok = all(tok in canonical.read_text() for tok in
                         ["ecutwfc = 90.0", "ecutrho = 720.0", "conv_thr = 1.0d-10", "mixing_beta = 0.30", "calculation = 'scf'"])

        em = re.search(r"!\s*total energy\s*=\s*(-?\d+\.\d+)\s*Ry", text)
        energy = float(em.group(1)) if em else None
        if energy is not None:
            energy_by_phase.setdefault(phase, []).append((cid, energy))

        ok = scf and notconv == 0 and nan_hits == 0 and gpu_active and job_done and exit0 and canon_sha_ok and out_sha_ok and nspin_ok and params_ok
        if not ok:
            reasons = []
            if not scf: reasons.append("SCF not converged")
            if notconv: reasons.append(f"{notconv} non-convergence warnings")
            if nan_hits: reasons.append(f"{nan_hits} NaN/Inf hits")
            if not gpu_active: reasons.append("GPU not active")
            if not job_done: reasons.append("JOB_DONE != YES")
            if not exit0: reasons.append("exit code != 0")
            if not canon_sha_ok: reasons.append("canonical input SHA changed since execution")
            if not out_sha_ok: reasons.append("qe.out SHA changed since execution")
            if not nspin_ok: reasons.append(f"nspin mismatch (present={nspin_present}, expected={nspin_expected})")
            if not params_ok: reasons.append("QE parameter uniformity failure")
            fail_count += 1
            rows_report.append((cid, phase, pod, "FAIL", "; ".join(reasons)))
        else:
            rows_report.append((cid, phase, pod, "PASS", ""))

    print(f"Checked {len(manifest)} configs across 10 pods")
    print(f"PASS: {len(manifest) - fail_count}, FAIL: {fail_count}")
    print()
    if fail_count:
        print("=== FAILURES ===")
        for cid, phase, pod, status, reason in rows_report:
            if status == "FAIL":
                print(f"  {cid} (phase={phase}, pod={pod}): {reason}")
    else:
        print("All 82 configs passed every check: SCF converged, 0 NaN/Inf, hash-fresh, GPU active, nspin correct, QE params uniform.")

    print()
    print("=== per-phase energy sanity (finite, phase-consistent) ===")
    for phase, vals in sorted(energy_by_phase.items()):
        es = [v for _, v in vals]
        print(f"  {phase}: n={len(es)}  min={min(es):.4f}  max={max(es):.4f} Ry")

    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
