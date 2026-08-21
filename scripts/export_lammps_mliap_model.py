#!/usr/bin/env python3
"""Export a MACE model to the LAMMPS ML-IAP unified format.

Deliberately bypasses `mace_create_lammps_model --format mliap`'s forced
e3nn -> cuequivariance weight conversion (`run_e3nn_to_cueq`): that path is
unconditional in the installed mace CLI ("Enabling cuequivariance by
default. TODO: switch?" -- mace/cli/create_lammps_model.py) and fails on
this LoRA-trained checkpoint with

    RuntimeError: Error(s) in loading state_dict for ScaleShiftMACE:
    Unexpected key(s) in state_dict: "products.0.symmetric_contractions.weight",
    "products.1.symmetric_contractions.weight".

cuequivariance is not installed in this environment anyway (confirmed at
import time: "cuequivariance or cuequivariance_torch is not available"), so
the conversion buys nothing here and is skipped. `LAMMPS_MLIAP_MACE` /
`MACEEdgeForcesWrapper` (mace/calculators/lammps_mliap_mace.py) call the
wrapped model's plain forward() with `lammps_mliap=True` and have no
dependency on cueq-specific weight layout -- confirmed by reading the class.
"""
import os
import sys

os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

import torch
from mace.calculators.lammps_mliap_mace import LAMMPS_MLIAP_MACE

MODEL_PATH = sys.argv[1] if len(sys.argv) > 1 else \
    "/workspace/ni_al/models/al3ni_combined227_lora_v1/al3ni_combined227_lora_v1.model"
HEAD = "Default"
OUT_PATH = MODEL_PATH + "-mliap_lammps.pt"

model = torch.load(MODEL_PATH, map_location="cpu")
model = model.double().to("cpu")
if not hasattr(model, "heads"):
    model.heads = [HEAD]
assert HEAD in model.heads, f"head {HEAD} not in {model.heads}"
model.lammps_mliap = True

lammps_model = LAMMPS_MLIAP_MACE(model, head=HEAD)
torch.save(lammps_model, OUT_PATH)
print(f"Exported: {OUT_PATH}")
print(f"  size bytes: {os.path.getsize(OUT_PATH)}")
