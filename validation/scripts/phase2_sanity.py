"""Phase 2 + 2b: loader sanity (NOT accuracy) and internal consistency."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, common as C
from ase.build import bulk

np.random.seed(0)
res = {"LABEL": "LOADER SANITY ONLY - NOT EVIDENCE OF ACCURACY"}
c = C.calc(C.model_path("al3ni_combined227_lora_v1"))

# --- Phase 2: bulk Ni fcc ------------------------------------------------
ni = bulk("Ni", "fcc", a=3.52, cubic=True); ni.calc = c
E = ni.get_potential_energy(); F = ni.get_forces()
res["phase2"] = {"structure": "bulk Ni fcc a=3.52 (4 atoms)",
                 "E_eV": float(E), "E_per_atom_eV": float(E/len(ni)),
                 "E_negative": bool(E < 0),
                 "max_abs_force_eV_A": float(np.abs(F).max()),
                 "forces_near_zero": bool(np.abs(F).max() < 1e-6),
                 "exception": None}

# --- Phase 2b: internal consistency -------------------------------------
al3ni = C.load_dataset("combined227")[0]
ref = [a for a in al3ni if a.info["config_id"] == "AlNi_rattle_003"][0].copy()
ref.calc = c
E1 = ref.get_potential_energy()

r2 = ref.copy(); r2.calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))
E2 = r2.get_potential_energy()
det = abs(E1 - E2)

# rotational invariance: rotate cell AND positions 45 deg about x
from ase.build import cut
r3 = ref.copy()
th = np.deg2rad(45.0)
R = np.array([[1,0,0],[0,np.cos(th),-np.sin(th)],[0,np.sin(th),np.cos(th)]])
r3.set_cell(ref.get_cell() @ R.T, scale_atoms=False)
r3.set_positions(ref.get_positions() @ R.T)
r3.calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))
E3 = r3.get_potential_energy()

# translational invariance
r4 = ref.copy()
shift = np.random.uniform(-5, 5, 3)
r4.set_positions(ref.get_positions() + shift)
r4.wrap()
r4.calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))
E4 = r4.get_potential_energy()

res["phase2b"] = {
 "structure": "AlNi_rattle_003 (from combined-227)",
 "E_reference_eV": float(E1),
 "determinism_dE_eV": float(det), "determinism_tol": 1e-8,
 "determinism_PASS": bool(det < 1e-8),
 "rotation_45deg_x_dE_eV": float(abs(E1 - E3)), "rotation_tol": 1e-6,
 "rotation_PASS": bool(abs(E1 - E3) < 1e-6),
 "translation_shift_A": shift.tolist(),
 "translation_dE_eV": float(abs(E1 - E4)), "translation_tol": 1e-6,
 "translation_PASS": bool(abs(E1 - E4) < 1e-6)}
res["phase2b"]["ALL_PASS"] = all(res["phase2b"][k] for k in
    ["determinism_PASS", "rotation_PASS", "translation_PASS"])

json.dump(res, open(os.path.join(C.RESULTS, "phase2_sanity.json"), "w"), indent=2)
print(json.dumps(res, indent=2))
