#!/usr/bin/env python3
"""Strict, read-only scientific validator for Dataset-100 QE production configs 026-100."""

import csv
import hashlib
import math
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path("/workspace/ni_al")
PLAN = ROOT / "configs/DATASET100_GPU_10CHUNK_PLAN.csv"
PROD = ROOT / "data/expansion_026_100/production_gpu"
OUTDIR = ROOT / "results/dataset100_dft_validation_v1"
CSV_OUT = OUTDIR / "config_validation.csv"
REPORT = ROOT / "configs/DATASET100_DFT_VALIDATION_STATUS.txt"
QE = ROOT / "tools/qe_gpu/builds/sm_89_autoconf/PW/src/pw.x"
PSEUDOS = {
    "Al": ROOT / "tools/qe_pseudos/Al.pbe-n-kjpaw_psl.1.0.0.UPF",
    "Ni": ROOT / "tools/qe_pseudos/ni_pbe_v1.4.uspp.F.UPF",
}
EXPECTED_QE = "66b7ea9f173b006854fc9e27dc9982c332dad295384803d612da7dad3edc7f8e"
EXPECTED_PSEUDO = {
    "Al": "fd7b78921e6d0939095b681c328732668eaefd1dee6882fdbc03be463550cc97",
    "Ni": "f76b86ce60cde3d83dfcc8df79ba05478db573d158289f1b226919442d977d25",
}
EXPECTED_PHASES = {"AlNi": 13, "Al3Ni2": 14, "AlNi3": 12, "Al3Ni5": 17, "Al3Ni": 19}
BOHR_ANG = 0.529177210903
FLOAT = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def env_history(path):
    values = {}
    for line in path.read_text(errors="strict").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            values.setdefault(k, []).append(v)
    return values


def input_geometry(text):
    nat_m = re.search(r"(?im)^\s*nat\s*=\s*(\d+)\s*,?", text)
    if not nat_m:
        raise ValueError("canonical input has no nat")
    nat = int(nat_m.group(1))
    cell_m = re.search(r"(?ims)^CELL_PARAMETERS\s+angstrom\s*\n((?:\s*" + FLOAT + r"\s+" + FLOAT + r"\s+" + FLOAT + r"\s*\n){3})", text)
    pos_m = re.search(r"(?ims)^ATOMIC_POSITIONS\s+crystal\s*\n(.*?)(?=^K_POINTS\b)", text)
    if not cell_m or not pos_m:
        raise ValueError("canonical cell/positions missing or unsupported units")
    cell = [[float(x) for x in line.split()] for line in cell_m.group(1).splitlines()]
    atoms = []
    for line in pos_m.group(1).strip().splitlines():
        p = line.split()
        if len(p) < 4:
            raise ValueError("malformed canonical atomic position")
        frac = [float(x) for x in p[1:4]]
        cart_ang = [sum(frac[i] * cell[i][j] for i in range(3)) for j in range(3)]
        atoms.append((p[0], [x / BOHR_ANG for x in cart_ang]))
    if len(atoms) != nat:
        raise ValueError(f"canonical atom count {len(atoms)} != nat {nat}")
    return nat, cell, atoms


def execution_matches(canonical, execution):
    # Production is allowed to change only these run-local CONTROL values.
    key = re.compile(r"(?im)^(\s*)(prefix|pseudo_dir|outdir)(\s*=.*)$")
    return key.sub(lambda m: m.group(1) + m.group(2).lower() + " = <RUN_LOCAL>", canonical) == key.sub(lambda m: m.group(1) + m.group(2).lower() + " = <RUN_LOCAL>", execution)


def xml_geometry_matches(xml_path, canonical_atoms):
    root = ET.parse(xml_path).getroot()
    structures = root.findall(".//atomic_structure")
    if not structures:
        return False, "QE XML has no atomic_structure"
    structure = structures[0]
    positions = structure.find("atomic_positions")
    if positions is None:
        return False, "QE XML has no atomic_positions"
    xml_atoms = []
    for atom in positions.findall("atom"):
        xml_atoms.append((atom.attrib.get("name"), [float(x.replace("D", "E")) for x in (atom.text or "").split()]))
    if len(xml_atoms) != len(canonical_atoms):
        return False, f"QE XML atom count {len(xml_atoms)} != canonical {len(canonical_atoms)}"
    max_delta = 0.0
    for (cs, cp), (xs, xp) in zip(canonical_atoms, xml_atoms):
        if cs != xs or len(xp) != 3:
            return False, "QE XML species/order mismatch"
        max_delta = max(max_delta, *(abs(a-b) for a, b in zip(cp, xp)))
    # QE's CODATA conversion and decimal input roundoff are much smaller than this.
    if max_delta > 2.0e-8:
        return False, f"QE XML/canonical geometry max |delta|={max_delta:.17g} bohr"
    return True, f"max_geometry_delta_bohr={max_delta:.17g}"


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(PLAN.open(newline="")))
    global_errors = []
    if len(rows) != 75:
        global_errors.append(f"plan row count={len(rows)}, expected 75")
    ids = [r["config_id"] for r in rows]
    expected_ids = [f"cfg{i:03d}_" for i in range(26, 101)]
    for prefix in expected_ids:
        if sum(x.startswith(prefix) for x in ids) != 1:
            global_errors.append(f"plan identity occurrence for {prefix} != 1")
    dup_ids = sorted(k for k, v in Counter(ids).items() if v > 1)
    if dup_ids:
        global_errors.append("duplicate plan config IDs: " + ",".join(dup_ids))
    phase_counts = Counter(r["phase"] for r in rows)
    if dict(phase_counts) != EXPECTED_PHASES:
        global_errors.append(f"phase counts={dict(phase_counts)} expected={EXPECTED_PHASES}")

    markers = sorted(PROD.glob("chunk_*/cfg*/config_complete.env"))
    if len(markers) != 75:
        global_errors.append(f"completion marker count={len(markers)}, expected 75")
    finish_files = sorted(PROD.glob("chunk_*/chunk_finish_utc.txt"))
    if len(finish_files) != 10 or any(not x.read_text().strip() for x in finish_files):
        global_errors.append(f"valid chunk finish marker count={sum(bool(x.read_text().strip()) for x in finish_files)}, expected 10")

    qe_hash = sha256(QE)
    if qe_hash != EXPECTED_QE:
        global_errors.append(f"QE SHA256={qe_hash}, expected={EXPECTED_QE}")
    pseudo_hashes = {k: sha256(v) for k, v in PSEUDOS.items()}
    for species, value in pseudo_hashes.items():
        if value != EXPECTED_PSEUDO[species]:
            global_errors.append(f"{species} pseudo SHA256={value}, expected={EXPECTED_PSEUDO[species]}")

    proc = subprocess.run(["ps", "-eo", "args="], capture_output=True, text=True, check=True).stdout.splitlines()
    running = [x for x in proc if ("pw.x" in x or "run_dataset100_gpu" in x or "run_chunk" in x) and "validate_dataset100_dft.py" not in x]
    if running:
        global_errors.append("production process(es) still running: " + " | ".join(running))

    validation = []
    details = []
    output_hash_to_ids = {}
    marker_ids = []
    for plan in rows:
        cid, phase = plan["config_id"], plan["phase"]
        errors = []
        canonical_path = Path(plan["canonical_input"])
        canonical_hash = sha256(canonical_path) if canonical_path.is_file() else ""
        if canonical_hash != plan["input_sha256"]:
            errors.append("canonical input SHA256 mismatch")
        candidates = sorted(PROD.glob(f"chunk_*/{cid}/config_complete.env"))
        marker = candidates[0] if len(candidates) == 1 else None
        if len(candidates) != 1:
            errors.append(f"completion marker occurrence={len(candidates)}")
        vals = env_history(marker) if marker else {}
        marker_id = vals.get("CONFIG_ID", [""])[-1] if vals else ""
        marker_ids.append(marker_id)
        if marker_id != cid:
            errors.append(f"marker CONFIG_ID={marker_id!r}")
        if (vals.get("PHASE", [""])[-1] if vals else "") != phase:
            errors.append("marker phase mismatch")
        if (vals.get("INPUT_SHA256", [""])[-1] if vals else "") != plan["input_sha256"]:
            errors.append("marker input SHA256 mismatch")
        if (vals.get("EXIT_CODE", [""])[-1] if vals else "") != "0":
            errors.append("exit code is not 0")
        if vals.get("STATE", [""])[-1] != "COMPLETE":
            errors.append("final marker state is not COMPLETE")
        if vals.get("SAFE_TO_REUSE", [""])[-1] != "YES":
            errors.append("marker SAFE_TO_REUSE is not YES")

        output_path = Path(vals.get("OUTPUT_PATH", [""])[-1]) if vals.get("OUTPUT_PATH") else Path("/__missing__")
        execution_path = Path(vals.get("ATTEMPT_DIR", [""])[-1]) / "execution.in" if vals.get("ATTEMPT_DIR") else Path("/__missing__")
        output_hash = sha256(output_path) if output_path.is_file() else ""
        if not output_path.is_file():
            errors.append("raw QE output missing")
            text = ""
        else:
            text = output_path.read_text(errors="strict")
            output_hash_to_ids.setdefault(output_hash, []).append(cid)
        if output_hash != (vals.get("OUTPUT_SHA256", [""])[-1] if vals else ""):
            errors.append("raw QE output SHA256 mismatch")

        try:
            nat, _, canonical_atoms = input_geometry(canonical_path.read_text(errors="strict"))
        except Exception as exc:
            nat, canonical_atoms = 0, []
            errors.append(f"canonical geometry parse: {exc}")
        if not execution_path.is_file():
            errors.append("execution input missing")
        else:
            execution = execution_path.read_text(errors="strict")
            if not execution_matches(canonical_path.read_text(errors="strict"), execution):
                errors.append("execution input differs from canonical beyond run-local CONTROL fields")
            if sha256(execution_path) != vals.get("EXECUTION_INPUT_SHA256", [""])[-1]:
                errors.append("execution input SHA256 mismatch")
            if f"prefix = 'prod_{plan['chunk_id'].replace('chunk_', 'c')}_{cid}'" not in execution:
                errors.append("execution prefix/config identity mismatch")

        job_done = len(re.findall(r"(?m)^\s*JOB DONE\.\s*$", text)) == 1
        scf = "convergence has been achieved" in text and "convergence NOT achieved" not in text
        energy_matches = re.findall(r"(?m)^!\s+total energy\s+=\s+(" + FLOAT + r")\s+Ry\s*$", text)
        energy = len(energy_matches) == 1 and math.isfinite(float(energy_matches[0].replace("D", "E")))
        forces = re.findall(r"(?m)^\s*atom\s+\d+\s+type\s+\d+\s+force\s+=\s+(" + FLOAT + r")\s+(" + FLOAT + r")\s+(" + FLOAT + r")\s*$", text)
        force_found = 3 * len(forces)
        forces_ok = len(forces) == nat and all(math.isfinite(float(x.replace("D", "E"))) for f in forces for x in f)
        stress_matches = re.findall(r"(?ms)^\s*total\s+stress\s+\(Ry/bohr\*\*3\).*?\n\s*(" + FLOAT + r")\s+(" + FLOAT + r")\s+(" + FLOAT + r")\s+" + FLOAT + r"\s+" + FLOAT + r"\s+" + FLOAT + r"\s*\n\s*(" + FLOAT + r")\s+(" + FLOAT + r")\s+(" + FLOAT + r")\s+" + FLOAT + r"\s+" + FLOAT + r"\s+" + FLOAT + r"\s*\n\s*(" + FLOAT + r")\s+(" + FLOAT + r")\s+(" + FLOAT + r")\s+" + FLOAT + r"\s+" + FLOAT + r"\s+" + FLOAT + r"\s*$", text)
        stress = len(stress_matches) == 1 and all(math.isfinite(float(x.replace("D", "E"))) for x in stress_matches[0])
        if not job_done: errors.append("JOB DONE missing or non-unique")
        if not scf: errors.append("SCF convergence evidence missing")
        if not energy: errors.append(f"valid final total energy count={len(energy_matches)}")
        if not forces_ok: errors.append(f"force components={force_found}, expected={nat*3}")
        if not stress: errors.append(f"valid complete stress tensor count={len(stress_matches)}")
        if re.search(r"(?i)(?<![A-Za-z])(?:nan|[+-]?inf(?:inity)?)(?![A-Za-z])", text):
            errors.append("NaN/Inf token in QE output")
        if text and not re.search(r"(?s)JOB DONE\.\s*\n=[-=]+=\s*$", text):
            errors.append("output terminator missing/trailing truncation evidence")
        if f"Reading input from {execution_path}" not in text:
            errors.append("QE output does not identify correct execution input")
        if not re.search(rf"number of atoms/cell\s+=\s+{nat}\s*$", text, re.M):
            errors.append("QE output nat/config identity mismatch")
        if text.count("PseudoPot. # 1 for Al") != 1 or text.count("PseudoPot. # 2 for Ni") != 1:
            errors.append("QE pseudopotential identity evidence missing/non-unique")
        xml_glob = list((execution_path.parent / "tmp").glob("*.save/data-file-schema.xml")) if execution_path.is_file() else []
        if len(xml_glob) != 1:
            errors.append(f"QE XML geometry file count={len(xml_glob)}")
            geometry_detail = "unavailable"
        else:
            ok, geometry_detail = xml_geometry_matches(xml_glob[0], canonical_atoms)
            if not ok: errors.append(geometry_detail)
            save_dir = xml_glob[0].parent
            for species, pseudo in PSEUDOS.items():
                copied = save_dir / pseudo.name
                if not copied.is_file() or sha256(copied) != pseudo_hashes[species]:
                    errors.append(f"{species} saved pseudopotential SHA256 mismatch/missing")

        row = {
            "config_id": cid, "phase": phase, "natoms": nat,
            "input_sha256": canonical_hash, "qe_binary_sha256": qe_hash,
            "job_done": "YES" if job_done else "NO",
            "scf_converged": "YES" if scf else "NO",
            "energy_present": "YES" if energy else "NO",
            "force_components_expected": nat * 3,
            "force_components_found": force_found,
            "stress_present": "YES" if stress else "NO",
            "output_path": str(output_path), "output_sha256": output_hash,
            "scientific_status": "VALID" if not errors else "FAILED: " + "; ".join(errors),
        }
        validation.append(row)
        details.append((cid, geometry_detail, errors))

    for digest, digest_ids in output_hash_to_ids.items():
        if len(digest_ids) > 1:
            global_errors.append(f"duplicate output SHA256 {digest}: {','.join(digest_ids)}")
    marker_dups = sorted(k for k, v in Counter(marker_ids).items() if k and v > 1)
    if marker_dups:
        global_errors.append("duplicate marker identities: " + ",".join(marker_dups))
    planned = set(ids)
    found_marker_dirs = {p.parent.name for p in markers}
    missing = sorted(planned - found_marker_dirs)
    extra = sorted(found_marker_dirs - planned)
    if missing: global_errors.append("missing config directories: " + ",".join(missing))
    if extra: global_errors.append("unexpected config directories: " + ",".join(extra))

    fields = ["config_id", "phase", "natoms", "input_sha256", "qe_binary_sha256", "job_done", "scf_converged", "energy_present", "force_components_expected", "force_components_found", "stress_present", "output_path", "output_sha256", "scientific_status"]
    with CSV_OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(validation)

    failed_rows = [r for r in validation if r["scientific_status"] != "VALID"]
    valid = len(validation) - len(failed_rows)
    report = [
        "DATASET-100 DFT SCIENTIFIC VALIDATION STATUS", "",
        "Validation scope: canonical configurations 026-100", f"Validation manifest: {CSV_OUT}",
        "Raw QE outputs were read only; no canonical QE input was modified.", "",
        "PRECONDITIONS",
        f"Plan configurations: {len(rows)}/75", f"Completion markers: {len(markers)}/75",
        f"Chunk finish markers: {len(finish_files)}/10", f"Production pw.x/chunk runners detected: {len(running)}",
        "Output data sync state: local production paths, markers, execution inputs, QE outputs, XML, and saved pseudopotentials all jointly present" if not missing else "Output data sync state: INCOMPLETE",
        "", "PROVENANCE",
        f"QE executable: {QE}", f"QE executable SHA256: {qe_hash}",
        f"Al pseudopotential: {PSEUDOS['Al']}", f"Al pseudopotential SHA256: {pseudo_hashes['Al']}",
        f"Ni pseudopotential: {PSEUDOS['Ni']}", f"Ni pseudopotential SHA256: {pseudo_hashes['Ni']}",
        "", "CANONICAL PHASE COUNTS",
        *(f"{p} = {phase_counts.get(p, 0)}" for p in ["AlNi", "Al3Ni2", "AlNi3", "Al3Ni5", "Al3Ni"]),
        f"TOTAL = {len(rows)}", "", "SCIENTIFIC CHECKS",
        "Each row was checked for plan/marker/path identity, canonical and execution hashes, controlled execution-input changes only, exit code 0, unique JOB DONE, SCF convergence, one finite final energy, exactly Natoms finite 3-vector forces, one finite 3x3 stress tensor, no NaN/Inf, complete terminator, QE XML geometry/species/order agreement, QE binary provenance, and live plus saved pseudopotential hashes.",
        "", "FAILURES",
    ]
    if global_errors or failed_rows:
        report.extend([f"GLOBAL: {x}" for x in global_errors])
        report.extend(f"{r['config_id']}: {r['scientific_status']}" for r in failed_rows)
        report.extend(["", "DATASET-100 DFT VALIDATION FAILED", f"VALID CONFIGS: {valid}/75", f"FAILED: {len(failed_rows)}", f"MISSING: {len(missing)}", "DO NOT ASSEMBLE DATASET"])
    else:
        report.extend(["NONE", "", "DATASET-100 DFT VALIDATION COMPLETE", "VALID CONFIGS: 75/75", "FAILED: 0", "MISSING: 0", "DUPLICATES: 0", "ENERGY LABELS: 75/75", "FORCE LABELS: 75/75", "STRESS LABELS: 75/75", "SAFE TO ASSEMBLE DATASET"])
    REPORT.write_text("\n".join(report) + "\n")
    print("\n".join(report[-12:]))
    return 1 if global_errors or failed_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
