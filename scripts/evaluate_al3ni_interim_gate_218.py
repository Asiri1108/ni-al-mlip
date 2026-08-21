#!/usr/bin/env python3
"""Combined-218 interim progress check. Same method/references as every
prior interim check, now comparing combined-218 against combined-211 as
the immediately-prior checkpoint. NOT a pass/fail gate -- no threshold.
"""

from pathlib import Path

import numpy as np
import torch
from ase.io import read
from mace.calculators import MACECalculator

ROOT = Path("/workspace/ni_al")
DATA = ROOT / "data/datasets/ni_al_combined218_dft.extxyz"
OLD_MODEL = ROOT / "models/al3ni_combined211_lora_v1/al3ni_combined211_lora_v1.model"
NEW_MODEL = ROOT / "models/al3ni_combined218_lora_v1/al3ni_combined218_lora_v1.model"
STATUS = ROOT / "configs/AL3NI_INTERIM_GATE_218_STATUS.txt"
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
    ref = by["Al3Ni_relaxed"]
    dft_ref_energy = float(ref.get_potential_energy())
    structures = {"relaxed": ref}
    structures.update({cid: by[cid] for cid in REF_IDS})

    dft_relative = {}
    for cid in REF_IDS:
        a = by[cid]
        de = float(a.get_potential_energy())
        dft_relative[cid] = (de - dft_ref_energy) / len(a) * 1000

    print("Evaluating combined-211 (prior checkpoint) model...", flush=True)
    old_e = predict(OLD_MODEL, structures)
    print("Evaluating combined-218 (this checkpoint) model...", flush=True)
    new_e = predict(NEW_MODEL, structures)

    def relative(pred, cid):
        return (pred[cid] - pred["relaxed"]) / len(by[cid]) * 1000

    lines = [
        "AL3NI INTERIM GATE STATUS -- COMBINED-218 CHECKPOINT (round212/213/214 merged in)",
        "", "NOT a pass/fail gate. No threshold. Progress signal only.", "",
        f"OLD model (prior checkpoint): {OLD_MODEL}",
        f"NEW model (this checkpoint):  {NEW_MODEL}", "",
    ]
    for cid in REF_IDS:
        lines.append(f"DFT relative energy, {cid}: {dft_relative[cid]:.6f} meV/atom")
    lines.append("")
    for label, pred in [("combined211 (OLD)", old_e), ("combined218 (NEW)", new_e)]:
        lines.append(f"=== {label} ===")
        for cid in REF_IDS:
            pr = relative(pred, cid)
            err = pr - dft_relative[cid]
            raw_err = (pred[cid] - by[cid].get_potential_energy()) / len(by[cid]) * 1000
            lines.append(f"{cid}: pred_relative={pr:.6f} meV/atom  relative_energy_error={err:.6f} meV/atom  (raw energy error={raw_err:.6f} meV/atom)")
        lines.append("")

    lines.append("=== CHANGE (combined218 - combined211), negative = improvement ===")
    for cid in REF_IDS:
        old_err = relative(old_e, cid) - dft_relative[cid]
        new_err = relative(new_e, cid) - dft_relative[cid]
        lines.append(f"{cid} relative_energy_error change: {new_err - old_err:.6f} meV/atom")
    lines.append("")
    lines.append("cfg109/cfg110 NOT evaluated -- sealed, no labels read.")
    lines.append("")
    lines.append("STATUS")
    lines.append("AL3NI INTERIM GATE EVALUATION COMPLETE (combined-218 checkpoint)")

    STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
