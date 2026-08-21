#!/usr/bin/env python3
"""Combined-211 interim progress check. Same method/references as every
prior interim check (combined-127, combined-129), now comparing
combined-211 against combined-129 as the immediately-prior checkpoint.
NOT a pass/fail gate -- no threshold.
"""

from pathlib import Path

import numpy as np
import torch
from ase.io import read
from mace.calculators import MACECalculator

ROOT = Path("/workspace/ni_al")
DATA = ROOT / "data/datasets/ni_al_combined211_dft.extxyz"
OLD_MODEL = ROOT / "models/al3ni_combined129_lora_v1/al3ni_combined129_lora_v1.model"
NEW_MODEL = ROOT / "models/al3ni_combined211_lora_v1/al3ni_combined211_lora_v1.model"
STATUS = ROOT / "configs/AL3NI_INTERIM_GATE_211_STATUS.txt"
REF_IDS = ["cfg043_Al3Ni_volume_rattle_expansion", "cfg115_Al3Ni_iso_expansion"]


def predict(model_path, structures):
    calc = MACECalculator(model_paths=str(model_path), device="cuda", default_dtype="float64")
    out = {}
    for key, atoms in structures.items():
        w = atoms.copy()
        w.calc = calc
        out[key] = float(w.get_potential_energy())
    del calc
    torch.cuda.empty_cache()
    return out


def main():
    frames = read(DATA, index=":")
    by = {a.info["config_id"]: a for a in frames}
    if "Al3Ni_relaxed" not in by:
        raise RuntimeError("Al3Ni_relaxed reference missing from combined-211")
    for cid in REF_IDS:
        if cid not in by:
            raise RuntimeError(f"{cid} missing from combined-211")

    ref = by["Al3Ni_relaxed"]
    dft_ref_energy = float(ref.get_potential_energy())
    structures = {"relaxed": ref}
    structures.update({cid: by[cid] for cid in REF_IDS})

    dft_relative = {}
    for cid in REF_IDS:
        a = by[cid]
        de = float(a.get_potential_energy())
        dft_relative[cid] = (de - dft_ref_energy) / len(a) * 1000

    print("Evaluating combined-129 (prior checkpoint) model...", flush=True)
    old_e = predict(OLD_MODEL, structures)
    print("Evaluating combined-211 (this checkpoint) model...", flush=True)
    new_e = predict(NEW_MODEL, structures)

    def relative(pred, cid):
        return (pred[cid] - pred["relaxed"]) / len(by[cid]) * 1000

    lines = [
        "AL3NI INTERIM GATE STATUS -- COMBINED-211 CHECKPOINT (round300 merged in, 82 configs, 10 pods)",
        "",
        "NOT a pass/fail gate. No threshold. Progress signal only, per",
        "configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt.",
        "",
        "METHOD (identical to every prior interim check)",
        "relative_energy_mev_atom = (E_pred(config) - E_pred(Al3Ni_relaxed)) / natoms * 1000",
        "",
        f"OLD model (prior checkpoint): {OLD_MODEL}",
        f"NEW model (this checkpoint):  {NEW_MODEL}",
        "",
    ]
    for cid in REF_IDS:
        lines.append(f"DFT relative energy, {cid}: {dft_relative[cid]:.6f} meV/atom")
    lines.append("")
    for label, pred in [("combined129 (OLD)", old_e), ("combined211 (NEW)", new_e)]:
        lines.append(f"=== {label} ===")
        for cid in REF_IDS:
            pr = relative(pred, cid)
            err = pr - dft_relative[cid]
            raw_err = (pred[cid] - by[cid].get_potential_energy()) / len(by[cid]) * 1000
            lines.append(
                f"{cid}: pred_relative={pr:.6f} meV/atom  "
                f"relative_energy_error={err:.6f} meV/atom  (raw energy error={raw_err:.6f} meV/atom)"
            )
        lines.append("")

    lines.append("=== CHANGE (combined211 - combined129), negative = improvement ===")
    for cid in REF_IDS:
        old_err = relative(old_e, cid) - dft_relative[cid]
        new_err = relative(new_e, cid) - dft_relative[cid]
        lines.append(f"{cid} relative_energy_error change: {new_err - old_err:.6f} meV/atom")
    lines.append("")
    lines.append("Note: round300 added 44 Al3Ni TRAIN structures (17->44 TRAIN vs combined-129's 27 total")
    lines.append("population), the largest phase gain in this round -- unlike round4's Al3Ni5/AlNi3-only")
    lines.append("addition, this probe (both cfg043/cfg115 are Al3Ni) IS directly relevant this time.")
    lines.append("")
    lines.append("cfg109/cfg110 NOT evaluated -- sealed, no labels read.")
    lines.append("")
    lines.append("STATUS")
    lines.append("AL3NI INTERIM GATE EVALUATION COMPLETE (combined-211 checkpoint)")

    STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
