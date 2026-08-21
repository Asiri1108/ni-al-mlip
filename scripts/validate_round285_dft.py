#!/usr/bin/env python3
"""Read-only integrity + QE-parameter-compatibility validator for all 9
round285 DFT outputs (7 TRAIN + 2 SEALED). Does NOT merge. Does NOT
retrain. Does NOT write ni_al_combined227_*.extxyz or round285_dft.extxyz.

SEALED (cfg297/cfg299): only presence/completion flags are computed for
these two -- job_done, scf_converged, and whether the energy/forces/stress
XML tags exist and are non-empty. Their numeric content is never parsed
into a float, never printed, never compared, never summarized.
"""

import csv
import hashlib
import re
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from ase.io import read

ROOT = Path("/workspace/ni_al")
BASE = ROOT / "data/al3ni_remediation_v1"
TRAIN_MANIFEST = BASE / "round285_manifest.csv"
SEALED_MANIFEST = BASE / "round285_sealed_manifest.csv"
PROD_BASE = BASE / "round285_production_dft"
COMBINED220_ALL = ROOT / "data/datasets/ni_al_combined220_dft.extxyz"

REFERENCE_QE_OUT = BASE / "round220_production_dft/cfg283_Al3Ni_uniaxial_z_compression/attempt_001/qe.out"
# nkpoints depends on how much the structure's rattle perturbation breaks the cell's
# point-group symmetry (QE's own automatic symmetry reduction), NOT on the requested
# k-mesh (10x8x8, byte-identical everywhere). A single non-rattled reference is the
# wrong comparison for rattled configs. Verified against 3 EXISTING frozen combined-220
# TRAIN members: cfg112/cfg114 (volume_rattle_expansion) and cfg284 (volume_rattle_
# compression) all show 324 k-points; cfg111/cfg283 (no rattle) show 150 -- this split
# predates round285 and is not a round285-specific issue.
REFERENCE_QE_OUT_RATTLED = BASE / "round2_production_dft/cfg112_Al3Ni_volume_rattle_expansion/attempt_001/qe.out"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def find_attempt_dir(cid):
    matches = list(PROD_BASE.glob(f"pod*/{cid}/attempt_001"))
    return matches[0] if len(matches) == 1 else None


def geometry_fingerprint_from_ase(atoms):
    payload = bytearray(" ".join(atoms.get_chemical_symbols()), "ascii")
    payload.extend(np.round(np.asarray(atoms.cell), 10).tobytes())
    payload.extend(np.round(atoms.get_scaled_positions(wrap=True), 10).tobytes())
    return hashlib.sha256(payload).hexdigest()


def requested_kmesh(execution_in_path):
    text = execution_in_path.read_text()
    m = re.search(r"K_POINTS automatic\s*\n\s*(\d+)\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+", text)
    return tuple(int(x) for x in m.groups()) if m else None


def qe_params(qe_out_path):
    """Parse echoed QE settings from a qe.out header. Metadata only --
    ecutwfc/ecutrho/k-points/smearing/spin/PP checksums/version -- never
    the physical labels (energy/forces/stress)."""
    text = qe_out_path.read_text(errors="replace")
    p = {}
    m = re.search(r"Program PWSCF v\.(\S+)", text)
    p["qe_version"] = m.group(1) if m else None
    m = re.search(r"kinetic-energy cutoff\s*=\s*([\d.]+)\s*Ry", text)
    p["ecutwfc"] = float(m.group(1)) if m else None
    m = re.search(r"charge density cutoff\s*=\s*([\d.]+)\s*Ry", text)
    p["ecutrho"] = float(m.group(1)) if m else None
    m = re.search(r"number of k points=\s*(\d+)\s+(\S[\S ]*?smearing), width \(Ry\)=\s*([\d.]+)", text)
    p["nkpoints"] = int(m.group(1)) if m else None
    p["smearing_type"] = m.group(2).strip() if m else None
    p["degauss"] = float(m.group(3)) if m else None
    p["nspin_lsda_present"] = bool(re.search(r"\bLSDA\b|spin polarized calculation", text))
    al = re.search(r"for Al read from file:\s*\n\s*(\S+)\s*\n\s*MD5 check sum:\s*([0-9a-f]+)", text)
    ni = re.search(r"for Ni read from file:\s*\n\s*(\S+)\s*\n\s*MD5 check sum:\s*([0-9a-f]+)", text)
    p["al_pseudo_path"] = al.group(1) if al else None
    p["al_pseudo_md5"] = al.group(2) if al else None
    p["ni_pseudo_path"] = ni.group(1) if ni else None
    p["ni_pseudo_md5"] = ni.group(2) if ni else None
    return p


def main():
    train_rows = {r["config_id"]: r for r in csv.DictReader(TRAIN_MANIFEST.open(newline=""))}
    sealed_rows = {r["config_id"]: r for r in csv.DictReader(SEALED_MANIFEST.open(newline=""))}
    all_rows = {**{k: (v, "TRAIN") for k, v in train_rows.items()},
                **{k: (v, "SEALED") for k, v in sealed_rows.items()}}
    if len(all_rows) != 9:
        raise RuntimeError(f"expected 9 configs (7 TRAIN + 2 SEALED), found {len(all_rows)}")

    ref_params = qe_params(REFERENCE_QE_OUT)
    ref_params_rattled = qe_params(REFERENCE_QE_OUT_RATTLED)
    print(f"Reference QE parameters, non-rattled family (combined-220, from {REFERENCE_QE_OUT}):")
    for k, v in ref_params.items():
        print(f"  {k}: {v}")
    print(f"\nReference QE parameters, rattled family (combined-220, from {REFERENCE_QE_OUT_RATTLED}):")
    for k, v in ref_params_rattled.items():
        print(f"  {k}: {v}")
    print()

    combined220 = read(COMBINED220_ALL, index=":")
    ids220 = {a.info["config_id"] for a in combined220}
    geoms220 = {geometry_fingerprint_from_ase(a) for a in combined220}

    param_mismatches = []
    geoms_seen = {}
    results = []

    for cid, (r, role) in all_rows.items():
        flags = {"config_id": cid, "role": role}
        attempt = find_attempt_dir(cid)
        if attempt is None:
            flags["FATAL"] = "attempt_001 not found or ambiguous"
            results.append(flags)
            continue

        meta_path = attempt / "execution_metadata.env"
        meta = dict(line.split("=", 1) for line in meta_path.read_text().splitlines() if "=" in line) if meta_path.exists() else {}

        flags["job_done"] = meta.get("JOB_DONE") == "YES"
        flags["scf_converged"] = meta.get("SCF_CONVERGED") == "YES"
        flags["exit_code_0"] = meta.get("EXIT_CODE") == "0"
        flags["gpu_active"] = meta.get("GPU_ACCELERATION_ACTIVE") == "YES"

        canonical_input = Path(r["qe_input_path"])
        input_sha_now = sha256(canonical_input) if canonical_input.exists() else None
        flags["input_sha_matches_manifest"] = input_sha_now == r.get("qe_input_sha256")
        flags["input_sha_matches_execution_meta"] = input_sha_now == meta.get("CANONICAL_INPUT_SHA256")

        qe_out = attempt / "qe.out"
        output_sha_now = sha256(qe_out) if qe_out.exists() else None
        flags["output_belongs_to_recorded_input"] = output_sha_now == meta.get("OUTPUT_SHA256")

        xmls = list((attempt / "tmp").glob("*.save/data-file-schema.xml"))
        flags["exactly_one_xml"] = len(xmls) == 1

        if flags["exactly_one_xml"]:
            xml_root = ET.parse(xmls[0]).getroot()
            output = xml_root.find("output")
            structure = output.find("atomic_structure")
            nat_xml = int(structure.attrib["nat"])

            pre_dft = read(Path(r["structure_path"])) if Path(r["structure_path"]).exists() else None
            if pre_dft is not None:
                pos_node = structure.find("atomic_positions")
                symbols_xml = [atom.attrib["name"] for atom in pos_node.findall("atom")]
                flags["atom_count_matches"] = nat_xml == len(pre_dft)
                flags["composition_matches"] = Counter(symbols_xml) == Counter(pre_dft.get_chemical_symbols())
                cell_node = structure.find("cell")
                from ase.units import Bohr
                cell_xml = np.array([[float(x.replace("D", "E")) for x in cell_node.find(k).text.split()]
                                     for k in ("a1", "a2", "a3")], dtype=np.float64) * Bohr
                flags["cell_matches"] = bool(np.allclose(cell_xml, pre_dft.cell.array, rtol=0, atol=1e-6))
            else:
                flags["atom_count_matches"] = flags["composition_matches"] = flags["cell_matches"] = None

            etot_node = output.find("total_energy/etot")
            forces_node = output.find("forces")
            stress_node = output.find("stress")
            flags["energy_present"] = etot_node is not None and (etot_node.text or "").strip() != ""
            flags["forces_present"] = forces_node is not None and (forces_node.text or "").strip() != ""
            flags["stress_present"] = stress_node is not None and (stress_node.text or "").strip() != ""

            if role == "TRAIN":
                # numeric finiteness check -- TRAIN only, never for SEALED
                from ase.units import Hartree, Bohr as Bohr2
                e_val = float(etot_node.text.strip().replace("D", "E")) * Hartree
                f_val = np.fromstring(forces_node.text.replace("D", "E"), sep=" ", dtype=np.float64) * Hartree / Bohr2
                s_val = np.fromstring(stress_node.text.replace("D", "E"), sep=" ", dtype=np.float64) * Hartree / (Bohr2 ** 3)
                flags["no_nan_inf"] = bool(np.isfinite(e_val) and np.isfinite(f_val).all() and np.isfinite(s_val).all())
                # geometry fingerprint for dedup (post-DFT geometry, TRAIN only)
                positions_xml = np.asarray([[float(x.replace("D", "E")) for x in atom.text.split()]
                                            for atom in structure.find("atomic_positions").findall("atom")]) * Bohr
                import ase
                fake = ase.Atoms(symbols=symbols_xml, positions=positions_xml, cell=cell_xml, pbc=True)
                gh = geometry_fingerprint_from_ase(fake)
                geoms_seen.setdefault(gh, []).append(cid)
                flags["dup_vs_combined220"] = gh in geoms220
            else:
                flags["no_nan_inf"] = None  # not evaluated for SEALED, by design
                flags["dup_vs_combined220"] = None
        else:
            for k in ("atom_count_matches", "composition_matches", "cell_matches",
                       "energy_present", "forces_present", "stress_present", "no_nan_inf", "dup_vs_combined220"):
                flags[k] = False

        flags["config_id_collision"] = cid in ids220

        exec_in = attempt / "execution.in"
        if exec_in.exists():
            kmesh = requested_kmesh(exec_in)
            if kmesh != (10, 8, 8):
                param_mismatches.append((cid, "requested_kmesh", (10, 8, 8), kmesh))

        # QE parameter compatibility (metadata only, safe for SEALED too)
        if qe_out.exists():
            p = qe_params(qe_out)
            is_rattled = r.get("rattle_sigma_A") not in (None, "", "0.0", "0")
            active_ref = ref_params_rattled if is_rattled else ref_params
            for key in ("qe_version", "ecutwfc", "ecutrho", "smearing_type", "degauss",
                        "al_pseudo_md5", "ni_pseudo_md5"):
                if p.get(key) != active_ref.get(key):
                    param_mismatches.append((cid, key, active_ref.get(key), p.get(key)))
            # nkpoints compared against the FAMILY-MATCHED reference (rattle vs non-rattle
            # changes QE's own symmetry-reduced k-point count; the requested mesh, 10x8x8,
            # is checked separately and is identical for all 9 -- see execution.in K_POINTS)
            if p.get("nkpoints") != active_ref.get("nkpoints"):
                param_mismatches.append((cid, "nkpoints", active_ref.get("nkpoints"), p.get("nkpoints")))
            if p.get("nspin_lsda_present") != active_ref.get("nspin_lsda_present"):
                param_mismatches.append((cid, "nspin/LSDA presence", active_ref.get("nspin_lsda_present"), p.get("nspin_lsda_present")))

        results.append(flags)

    internal_dups = {gh: cids for gh, cids in geoms_seen.items() if len(cids) > 1}

    print("=" * 110)
    print("PER-CONFIG INTEGRITY REPORT")
    print("=" * 110)
    valid_count = 0
    for flags in results:
        cid, role = flags["config_id"], flags["role"]
        print(f"\n{cid} (role={role})")
        if "FATAL" in flags:
            print(f"  FATAL: {flags['FATAL']}")
            continue
        core_checks = ["job_done", "scf_converged", "exit_code_0", "gpu_active",
                        "input_sha_matches_manifest", "input_sha_matches_execution_meta",
                        "output_belongs_to_recorded_input", "exactly_one_xml",
                        "atom_count_matches", "composition_matches", "cell_matches",
                        "energy_present", "forces_present", "stress_present",
                        "config_id_collision"]
        for k in core_checks:
            v = flags.get(k)
            label = "config_id_collision (expect False)" if k == "config_id_collision" else k
            print(f"  {label}: {v}")
        if role == "TRAIN":
            print(f"  no_nan_inf: {flags['no_nan_inf']}")
            print(f"  dup_vs_combined220 (expect False): {flags['dup_vs_combined220']}")
            is_valid = (flags.get("job_done") and flags.get("scf_converged") and flags.get("exit_code_0")
                        and flags.get("gpu_active") and flags.get("input_sha_matches_manifest")
                        and flags.get("input_sha_matches_execution_meta") and flags.get("output_belongs_to_recorded_input")
                        and flags.get("exactly_one_xml") and flags.get("atom_count_matches")
                        and flags.get("composition_matches") and flags.get("cell_matches")
                        and flags.get("energy_present") and flags.get("forces_present") and flags.get("stress_present")
                        and flags.get("no_nan_inf") and not flags.get("config_id_collision")
                        and not flags.get("dup_vs_combined220"))
        else:
            print("  [SEALED -- numeric labels not read, not checked for NaN/Inf, not compared]")
            is_valid = (flags.get("job_done") and flags.get("scf_converged") and flags.get("exit_code_0")
                        and flags.get("gpu_active") and flags.get("input_sha_matches_manifest")
                        and flags.get("input_sha_matches_execution_meta") and flags.get("output_belongs_to_recorded_input")
                        and flags.get("exactly_one_xml") and flags.get("atom_count_matches")
                        and flags.get("composition_matches") and flags.get("cell_matches")
                        and flags.get("energy_present") and flags.get("forces_present") and flags.get("stress_present")
                        and not flags.get("config_id_collision"))
        flags["_valid"] = is_valid
        print(f"  ==> {'VALID' if is_valid else 'INVALID'}")
        valid_count += int(is_valid)

    print()
    print("=" * 110)
    print("INTERNAL DUPLICATE CHECK (within round285's 7 TRAIN structures)")
    print("=" * 110)
    if internal_dups:
        for gh, cids in internal_dups.items():
            print(f"  DUPLICATE GEOMETRY: {cids}")
    else:
        print("  none found")

    print()
    print("=" * 110)
    print("QE PARAMETER COMPATIBILITY vs combined-220 reference")
    print("=" * 110)
    if param_mismatches:
        for cid, key, refv, gotv in param_mismatches:
            print(f"  MISMATCH: {cid} field={key} reference={refv} got={gotv}")
    else:
        print("  All 9 configs: byte-identical QE parameters vs combined-220 reference "
              "(qe_version, ecutwfc, ecutrho, k-point count, smearing type/width, "
              "nspin/LSDA presence, Al/Ni pseudopotential MD5)")

    # Structurally guaranteed, not just asserted: the code path above only ever calls
    # float()/np.fromstring() on etot_node/forces_node/stress_node text inside the
    # `if role == "TRAIN":` branch. For role == "SEALED", only tag-presence (bool) is
    # checked -- the numeric text is never parsed, computed on, or printed.
    sealed_labels_unread = True

    print()
    print("=" * 110)
    print("SUMMARY")
    print("=" * 110)
    print(f"VALID: {valid_count}/9")
    qe_match_str = "MATCH" if not param_mismatches else f"MISMATCH, {param_mismatches[0][1]}"
    print(f"QE PARAMETER MATCH: {qe_match_str}")
    print(f"SEALED LABELS UNREAD: {'Y' if sealed_labels_unread else 'N'}")
    ready = valid_count == 9 and not param_mismatches and not internal_dups
    print(f"READY FOR MERGE: {'Y' if ready else 'N'}")


if __name__ == "__main__":
    main()
