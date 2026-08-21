#!/usr/bin/env python3
"""Read-only scientific-integrity validator for the frozen Al3Ni remediation DFT runs."""

import csv
import hashlib
import math
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/workspace/ni_al")
BASE = ROOT / "data/al3ni_remediation_v1"
MANIFEST = BASE / "remediation_manifest.csv"
SPLIT = BASE / "split_membership_manifest.csv"
ARTIFACTS = BASE / "artifact_sha256.csv"
PROD = BASE / "production_dft"
OUTDIR = ROOT / "results/al3ni_remediation_dft_validation_v1"
CSV_OUT = OUTDIR / "config_validation.csv"
REPORT = ROOT / "configs/AL3NI_REMEDIATION_DFT_VALIDATION_STATUS.txt"
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
EXPECTED_ROLES = {"TRAIN": 6, "VALIDATION": 2, "CONFIRMATION_HOLDOUT": 2}
BOHR_ANG = 0.529177210903
FLOAT = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def env_values(path):
    values = {}
    for line in path.read_text(errors="strict").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.rstrip("\r")
    return values


def input_geometry(text):
    nat_match = re.search(r"(?im)^\s*nat\s*=\s*(\d+)\s*,?", text)
    cell_match = re.search(
        r"(?ims)^CELL_PARAMETERS\s+angstrom\s*\n"
        r"((?:\s*" + FLOAT + r"\s+" + FLOAT + r"\s+" + FLOAT + r"\s*\n){3})",
        text,
    )
    pos_match = re.search(r"(?ims)^ATOMIC_POSITIONS\s+crystal\s*\n(.*?)(?=^K_POINTS\b)", text)
    if not nat_match or not cell_match or not pos_match:
        raise ValueError("canonical nat/cell/positions missing or unsupported")
    nat = int(nat_match.group(1))
    cell = [[float(x) for x in line.split()] for line in cell_match.group(1).splitlines()]
    atoms = []
    for line in pos_match.group(1).strip().splitlines():
        fields = line.split()
        if len(fields) < 4:
            raise ValueError("malformed canonical atomic position")
        frac = [float(x) for x in fields[1:4]]
        cart_ang = [sum(frac[i] * cell[i][j] for i in range(3)) for j in range(3)]
        atoms.append((fields[0], [x / BOHR_ANG for x in cart_ang]))
    if len(atoms) != nat:
        raise ValueError(f"canonical atom count {len(atoms)} != nat {nat}")
    return nat, atoms


def execution_matches(canonical, execution):
    allowed = re.compile(r"(?im)^(\s*)(prefix|pseudo_dir|outdir)(\s*=.*)$")
    normalize = lambda text: allowed.sub(
        lambda match: match.group(1) + match.group(2).lower() + " = <RUN_LOCAL>", text
    )
    return normalize(canonical) == normalize(execution)


def xml_geometry_matches(xml_path, canonical_atoms):
    root = ET.parse(xml_path).getroot()
    structures = root.findall(".//atomic_structure")
    if not structures:
        return False, "QE XML has no atomic_structure"
    positions = structures[0].find("atomic_positions")
    if positions is None:
        return False, "QE XML has no atomic_positions"
    xml_atoms = [
        (atom.attrib.get("name"), [float(x.replace("D", "E")) for x in (atom.text or "").split()])
        for atom in positions.findall("atom")
    ]
    if len(xml_atoms) != len(canonical_atoms):
        return False, f"QE XML atom count {len(xml_atoms)} != canonical {len(canonical_atoms)}"
    max_delta = 0.0
    for (canonical_species, canonical_pos), (xml_species, xml_pos) in zip(canonical_atoms, xml_atoms):
        if canonical_species != xml_species or len(xml_pos) != 3:
            return False, "QE XML species/order mismatch"
        max_delta = max(max_delta, *(abs(a - b) for a, b in zip(canonical_pos, xml_pos)))
    if max_delta > 2.0e-8:
        return False, f"QE XML/canonical geometry mismatch ({max_delta:.17g} bohr)"
    return True, "geometry matched"


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    manifest_rows = list(csv.DictReader(MANIFEST.open(newline="")))
    split_rows = list(csv.DictReader(SPLIT.open(newline="")))
    artifact_rows = list(csv.DictReader(ARTIFACTS.open(newline="")))
    global_errors = []

    expected_ids = [f"cfg{i:03d}_" for i in range(101, 111)]
    ids = [row["config_id"] for row in split_rows]
    if len(split_rows) != 10 or len(manifest_rows) != 10:
        global_errors.append(f"manifest counts remediation={len(manifest_rows)}, split={len(split_rows)}, expected=10")
    for prefix in expected_ids:
        if sum(cid.startswith(prefix) for cid in ids) != 1:
            global_errors.append(f"split identity occurrence for {prefix} != 1")
    duplicates = sorted(key for key, value in Counter(ids).items() if value > 1)
    if duplicates:
        global_errors.append("duplicate split config IDs: " + ",".join(duplicates))
    role_counts = Counter(row["split"] for row in split_rows)
    if dict(role_counts) != EXPECTED_ROLES:
        global_errors.append(f"role counts={dict(role_counts)} expected={EXPECTED_ROLES}")

    manifest_by_id = {row["config_id"]: row for row in manifest_rows}
    artifact_hash = {(row["config_id"], row["artifact_type"]): row["sha256"] for row in artifact_rows}
    if set(manifest_by_id) != set(ids):
        global_errors.append("remediation and split manifest config memberships differ")

    qe_hash = sha256(QE) if QE.is_file() else ""
    if qe_hash != EXPECTED_QE:
        global_errors.append(f"QE binary SHA256={qe_hash}, expected={EXPECTED_QE}")
    pseudo_hashes = {species: sha256(path) if path.is_file() else "" for species, path in PSEUDOS.items()}
    for species, digest in pseudo_hashes.items():
        if digest != EXPECTED_PSEUDO[species]:
            global_errors.append(f"{species} pseudopotential SHA256={digest}, expected={EXPECTED_PSEUDO[species]}")

    processes = subprocess.run(["ps", "-eo", "args="], capture_output=True, text=True, check=True).stdout.splitlines()
    running = [
        line for line in processes
        if ("pw.x" in line or "run_al3ni_remediation_dft" in line)
        and "validate_al3ni_remediation_dft.py" not in line
    ]
    if running:
        global_errors.append("Al3Ni production process(es) still running")

    validation = []
    output_hash_to_ids = {}
    marker_ids = []
    for split_row in split_rows:
        cid, role = split_row["config_id"], split_row["split"]
        sealed = role == "CONFIRMATION_HOLDOUT"
        errors = []
        manifest = manifest_by_id.get(cid, {})
        if manifest.get("split") != role:
            errors.append("split membership mismatch between manifests")
        if manifest.get("phase") != "Al3Ni" or split_row.get("phase") != "Al3Ni":
            errors.append("phase is not Al3Ni")
        canonical = Path(manifest.get("qe_input_path", "/__missing__"))
        structure = Path(manifest.get("structure_path", "/__missing__"))
        canonical_hash = sha256(canonical) if canonical.is_file() else ""
        structure_hash = sha256(structure) if structure.is_file() else ""
        expected_input_hash = split_row["qe_input_sha256"]
        if canonical_hash != expected_input_hash or canonical_hash != manifest.get("qe_input_sha256") or canonical_hash != artifact_hash.get((cid, "qe_input")):
            errors.append("canonical input SHA256 mismatch against frozen design")
        if structure_hash != split_row["structure_sha256"] or structure_hash != manifest.get("structure_sha256") or structure_hash != artifact_hash.get((cid, "structure")):
            errors.append("structure SHA256 mismatch against frozen design")

        markers = sorted((PROD / cid).glob("attempt_*/config_complete.env"))
        marker = markers[0] if len(markers) == 1 else None
        if len(markers) != 1:
            errors.append(f"completion marker occurrence={len(markers)}")
        values = env_values(marker) if marker else {}
        marker_ids.append(values.get("CONFIG_ID", ""))
        if values.get("CONFIG_ID") != cid:
            errors.append("completion marker config identity mismatch")
        if values.get("SPLIT") != role:
            errors.append("completion marker split mismatch")
        if values.get("INPUT_SHA256") != expected_input_hash:
            errors.append("completion marker input SHA256 mismatch")
        if values.get("QE_BINARY_SHA256") != EXPECTED_QE:
            errors.append("completion marker QE binary SHA256 mismatch")
        for species in PSEUDOS:
            if values.get(f"{species.upper()}_PSEUDO_SHA256") != EXPECTED_PSEUDO[species]:
                errors.append(f"completion marker {species} pseudopotential SHA256 mismatch")
        if values.get("EXIT_CODE") != "0":
            errors.append("exit code is not 0")
        if values.get("LABEL_POLICY") != split_row["label_access_policy"]:
            errors.append("label-access policy mismatch")

        attempt_dir = marker.parent if marker else Path("/__missing__")
        execution = attempt_dir / "execution.in"
        output = attempt_dir / "qe.out"
        output_hash = sha256(output) if output.is_file() else ""
        output_hash_to_ids.setdefault(output_hash, []).append(cid)
        if output_hash != values.get("OUTPUT_SHA256"):
            errors.append("QE output SHA256 mismatch")
        text = output.read_text(errors="strict") if output.is_file() else ""
        if not output.is_file():
            errors.append("QE output missing")

        try:
            canonical_text = canonical.read_text(errors="strict")
            nat, canonical_atoms = input_geometry(canonical_text)
        except Exception as exc:
            canonical_text, nat, canonical_atoms = "", 0, []
            errors.append(f"canonical geometry parse failed: {exc}")
        composition = Counter(species for species, _ in canonical_atoms)
        if nat != 16 or composition != Counter({"Al": 12, "Ni": 4}):
            errors.append(f"composition/atom count mismatch: nat={nat}, composition={dict(composition)}")
        if manifest.get("natoms") != "16":
            errors.append("manifest atom count is not 16")

        if not execution.is_file():
            errors.append("execution input missing")
        else:
            execution_text = execution.read_text(errors="strict")
            if not execution_matches(canonical_text, execution_text):
                errors.append("execution input differs beyond permitted run-local fields")
            if sha256(execution) != values.get("EXECUTION_INPUT_SHA256"):
                errors.append("execution input SHA256 mismatch")
            if f"prefix = 'rem_{cid}_a001'" not in execution_text:
                errors.append("execution prefix/config identity mismatch")
        if f"Reading input from {execution}" not in text:
            errors.append("QE output does not identify correct frozen execution input")

        job_done = len(re.findall(r"(?m)^\s*JOB DONE\.\s*$", text)) == 1
        scf = "convergence has been achieved" in text and "convergence NOT achieved" not in text
        energies = re.findall(r"(?m)^!\s+total energy\s+=\s+(" + FLOAT + r")\s+Ry\s*$", text)
        energy_ok = len(energies) == 1 and math.isfinite(float(energies[0].replace("D", "E")))
        forces = re.findall(
            r"(?m)^\s*atom\s+\d+\s+type\s+\d+\s+force\s+=\s+(" + FLOAT + r")\s+(" + FLOAT + r")\s+(" + FLOAT + r")\s*$",
            text,
        )
        forces_ok = len(forces) == nat and all(math.isfinite(float(x.replace("D", "E"))) for vector in forces for x in vector)
        stresses = re.findall(
            r"(?ms)^\s*total\s+stress\s+\(Ry/bohr\*\*3\).*?\n"
            r"\s*(" + FLOAT + r")\s+(" + FLOAT + r")\s+(" + FLOAT + r")\s+" + FLOAT + r"\s+" + FLOAT + r"\s+" + FLOAT + r"\s*\n"
            r"\s*(" + FLOAT + r")\s+(" + FLOAT + r")\s+(" + FLOAT + r")\s+" + FLOAT + r"\s+" + FLOAT + r"\s+" + FLOAT + r"\s*\n"
            r"\s*(" + FLOAT + r")\s+(" + FLOAT + r")\s+(" + FLOAT + r")\s+" + FLOAT + r"\s+" + FLOAT + r"\s+" + FLOAT + r"\s*$",
            text,
        )
        stress_ok = len(stresses) == 1 and all(math.isfinite(float(x.replace("D", "E"))) for x in stresses[0])
        nontruncated = bool(re.search(r"(?s)JOB DONE\.\s*\n=[-=]+=\s*$", text))
        if not job_done or values.get("JOB_DONE") != "YES": errors.append("JOB DONE missing/non-unique or marker mismatch")
        if not scf or values.get("SCF_CONVERGED") != "YES": errors.append("SCF convergence evidence missing or marker mismatch")
        if not nontruncated or values.get("OUTPUT_NONTRUNCATED") != "YES": errors.append("output terminator missing/truncation evidence")
        if not energy_ok: errors.append(f"valid final total energy count={len(energies)}")
        if not forces_ok: errors.append(f"force components={3 * len(forces)}, expected={3 * nat}")
        if not stress_ok: errors.append(f"valid complete stress tensor count={len(stresses)}")
        if re.search(r"(?i)(?<![A-Za-z])(?:nan|[+-]?inf(?:inity)?)(?![A-Za-z])", text):
            errors.append("NaN/Inf token in QE output")
        if not re.search(rf"number of atoms/cell\s+=\s+{nat}\s*$", text, re.M):
            errors.append("QE output atom count/config identity mismatch")
        if text.count("PseudoPot. # 1 for Al") != 1 or text.count("PseudoPot. # 2 for Ni") != 1:
            errors.append("QE pseudopotential identity evidence missing/non-unique")

        xml_files = list((attempt_dir / "tmp").glob("*.save/data-file-schema.xml"))
        geometry_ok = False
        if len(xml_files) != 1:
            errors.append(f"QE XML geometry file count={len(xml_files)}")
        else:
            geometry_ok, geometry_detail = xml_geometry_matches(xml_files[0], canonical_atoms)
            if not geometry_ok:
                errors.append(geometry_detail)
            for species, pseudo in PSEUDOS.items():
                saved = xml_files[0].parent / pseudo.name
                if not saved.is_file() or sha256(saved) != EXPECTED_PSEUDO[species]:
                    errors.append(f"saved {species} pseudopotential SHA256 mismatch/missing")

        validation.append({
            "config_id": cid,
            "role": role,
            "natoms": nat,
            "composition": "Al12Ni4" if composition == Counter({"Al": 12, "Ni": 4}) else "INVALID",
            "input_sha256": canonical_hash,
            "structure_sha256": structure_hash,
            "qe_binary_sha256": qe_hash,
            "al_pseudo_sha256": pseudo_hashes["Al"],
            "ni_pseudo_sha256": pseudo_hashes["Ni"],
            "output_sha256": output_hash,
            "exit_code_zero": "YES" if values.get("EXIT_CODE") == "0" else "NO",
            "job_done": "YES" if job_done else "NO",
            "scf_converged": "YES" if scf else "NO",
            "output_nontruncated": "YES" if nontruncated else "NO",
            "energy_present": "YES" if energy_ok else "NO",
            "forces_present": "YES" if forces_ok else "NO",
            "stress_present": "YES" if stress_ok else "NO",
            "geometry_identity": "MATCH" if geometry_ok else "MISMATCH",
            "scientific_status": "VALID" if not errors else "FAILED: " + "; ".join(errors),
            "labels_sealed": "YES" if sealed else "NOT_APPLICABLE",
        })

    for digest, digest_ids in output_hash_to_ids.items():
        if digest and len(digest_ids) > 1:
            global_errors.append(f"duplicate output SHA256 {digest}: {','.join(digest_ids)}")
    marker_duplicates = sorted(key for key, value in Counter(marker_ids).items() if key and value > 1)
    if marker_duplicates:
        global_errors.append("duplicate completion marker identities: " + ",".join(marker_duplicates))
    config_dirs = {path.name for path in PROD.glob("cfg*") if path.is_dir()}
    missing = sorted(set(ids) - config_dirs)
    extra = sorted(config_dirs - set(ids))
    if missing: global_errors.append("missing config directories: " + ",".join(missing))
    if extra: global_errors.append("unexpected config directories: " + ",".join(extra))

    fields = list(validation[0]) if validation else []
    with CSV_OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(validation)

    failed_rows = [row for row in validation if row["scientific_status"] != "VALID"]
    valid_by_role = Counter(row["role"] for row in validation if row["scientific_status"] == "VALID")
    valid = len(validation) - len(failed_rows)
    report = [
        "AL3NI REMEDIATION DFT SCIENTIFIC VALIDATION STATUS", "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"Validation manifest: {CSV_OUT}",
        f"Production root: {PROD}",
        "Audit mode: READ ONLY; no DFT input/output or Dataset-100 content modified", "",
        "PROVENANCE",
        f"QE binary: {QE}", f"QE binary SHA256: {qe_hash}",
        f"Al pseudopotential: {PSEUDOS['Al']}", f"Al pseudopotential SHA256: {pseudo_hashes['Al']}",
        f"Ni pseudopotential: {PSEUDOS['Ni']}", f"Ni pseudopotential SHA256: {pseudo_hashes['Ni']}", "",
        "SCIENTIFIC INTEGRITY CHECKS",
        "Each configuration was independently checked for frozen manifest identity and split, canonical structure/input hashes, permitted execution-input substitutions only, exit code 0, unique JOB DONE, SCF convergence, complete terminator, one finite final energy, exactly Natoms finite 3-vector forces, one finite 3x3 stress tensor, absence of NaN/Inf, Al12Ni4 composition with 16 atoms, QE XML geometry/species/order identity, output-to-input identity, QE binary provenance, live and saved pseudopotential identity/hashes, missing configs, and duplicate output/config identities.", "",
        "CONFIRMATION LABEL PROTECTION",
        "cfg109 and cfg110 were assessed only through boolean integrity/presence tests and hashes.",
        "No confirmation energy, relative energy, force, or stress values are recorded or reported.",
        "CONFIRMATION LABELS SEALED: YES", "",
        "FAILURES",
    ]
    if global_errors or failed_rows:
        report.extend([f"GLOBAL: {error}" for error in global_errors])
        report.extend(f"{row['config_id']}: {row['scientific_status']}" for row in failed_rows)
        report.extend(["", "AL3NI REMEDIATION DFT VALIDATION FAILED", f"VALID CONFIGS: {valid}/10", f"FAILED: {len(failed_rows)}", f"MISSING: {len(missing)}", "DO NOT ASSEMBLE REMEDIATION TRAINING DATA"])
    else:
        report.extend([
            "NONE", "", "FINAL COUNTS", "TOTAL = 10/10", "TRAIN = 6/6", "VALIDATION = 2/2", "CONFIRMATION = 2/2", "FAILED = 0", "MISSING = 0", "CONFIRMATION LABELS SEALED = YES", "",
            "AL3NI REMEDIATION DFT VALIDATION COMPLETE", "VALID CONFIGS: 10/10", "TRAIN VALID: 6/6", "VALIDATION VALID: 2/2", "CONFIRMATION VALID: 2/2", "FAILED: 0", "MISSING: 0", "CONFIRMATION LABELS SEALED: YES", "READY FOR DEVELOPMENT DATASET ASSEMBLY",
        ])
    REPORT.write_text("\n".join(report) + "\n")
    print("\n".join(report[-9:]))
    return 1 if global_errors or failed_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
