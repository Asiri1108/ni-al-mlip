#!/usr/bin/env python3
"""Comprehensive integrity check for the round220 batch (2 configs)."""

import csv
import hashlib
import re
from pathlib import Path

ROOT = Path("/workspace/ni_al")
MANIFEST_CSV = ROOT / "data/al3ni_remediation_v1/round220_manifest.csv"
PROD_BASE = ROOT / "data/al3ni_remediation_v1/round220_production_dft"
EXPECTED_TOTAL = 2


def sha(p):
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def main():
    manifest = {r["config_id"]: r for r in csv.DictReader(MANIFEST_CSV.open(newline=""))}
    if len(manifest) != EXPECTED_TOTAL:
        raise RuntimeError(f"expected {EXPECTED_TOTAL} configs, found {len(manifest)}")

    fail_count = 0
    energy_by_phase = {}

    for cid, m in manifest.items():
        attempt = PROD_BASE / cid / "attempt_001"
        qe_out = attempt / "qe.out"
        meta_path = attempt / "execution_metadata.env"
        canonical = Path(m["qe_input_path"])
        phase = m["phase"]

        if not qe_out.exists() or not meta_path.exists():
            print(f"FAIL {cid}: missing qe.out or execution_metadata.env")
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
        canon_sha_ok = sha(canonical) == meta.get("CANONICAL_INPUT_SHA256") if canonical.exists() else False
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

        natoms_line = re.search(r"number of atoms/cell\s*=\s*(\d+)", text)
        natoms_ok = natoms_line is not None and int(natoms_line.group(1)) == int(m["natoms"])

        ok = (scf and notconv == 0 and nan_hits == 0 and gpu_active and job_done and exit0
              and canon_sha_ok and out_sha_ok and nspin_ok and params_ok and natoms_ok)
        if not ok:
            reasons = []
            if not scf: reasons.append("SCF not converged")
            if notconv: reasons.append(f"{notconv} non-convergence")
            if nan_hits: reasons.append(f"{nan_hits} NaN/Inf")
            if not gpu_active: reasons.append("GPU not active")
            if not job_done: reasons.append("JOB_DONE != YES")
            if not exit0: reasons.append("exit code != 0")
            if not canon_sha_ok: reasons.append("canonical input SHA changed")
            if not out_sha_ok: reasons.append("qe.out SHA changed")
            if not nspin_ok: reasons.append(f"nspin mismatch (present={nspin_present})")
            if not params_ok: reasons.append("QE param uniformity failure")
            if not natoms_ok: reasons.append("atom count mismatch")
            print(f"FAIL {cid}: {'; '.join(reasons)}")
            fail_count += 1
        else:
            print(f"PASS {cid} ({phase})")

    print(f"\nChecked {len(manifest)} configs")
    print(f"PASS: {len(manifest) - fail_count}, FAIL: {fail_count}")
    print("\nper-phase energy sanity:")
    for phase, vals in sorted(energy_by_phase.items()):
        es = [v for _, v in vals]
        print(f"  {phase}: n={len(es)} min={min(es):.4f} max={max(es):.4f} Ry")

    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
