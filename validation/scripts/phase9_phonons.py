"""Phase 9: phonon dispersion per phase via phonopy + MACE force constants.

Imaginary (negative) frequencies at a phase known to be experimentally stable
indicate the model believes it is dynamically unstable - a serious defect.
"""
import sys, os, json, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, common as C
from phonopy import Phonopy
from phonopy.structure.atoms import PhonopyAtoms
from ase.optimize import FIRE
from ase.filters import FrechetCellFilter
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

atoms, split = C.load_dataset("combined227")
relaxed = {a.info["phase"]: a for a in atoms if a.info["config_type"] == "relaxed"}
calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))
# supercell chosen so every lattice vector reaches >= ~9 A
SUPER = {"Al3Ni": [2,2,2], "Al3Ni2": [3,3,2], "AlNi": [4,4,4],
         "Al3Ni5": [3,2,2], "AlNi3": [3,3,3]}

summary, panels = [], []
for ph in C.PHASES:
    ref = relaxed[ph].copy(); ref.calc = calc
    FIRE(FrechetCellFilter(ref), logfile=os.devnull).run(fmax=0.001, steps=2000)
    cell = PhonopyAtoms(symbols=ref.get_chemical_symbols(),
                        cell=ref.cell.array, scaled_positions=ref.get_scaled_positions())
    phonon = Phonopy(cell, supercell_matrix=np.diag(SUPER[ph]))
    phonon.generate_displacements(distance=0.01)
    sets = []
    for sc in phonon.supercells_with_displacements:
        w = C.__import__("ase").Atoms(symbols=sc.symbols, cell=sc.cell,
                                      scaled_positions=sc.scaled_positions, pbc=True) \
            if False else None
        from ase import Atoms
        w = Atoms(symbols=sc.symbols, cell=sc.cell,
                  scaled_positions=sc.scaled_positions, pbc=True)
        w.calc = calc
        sets.append(w.get_forces())
    phonon.forces = np.array(sets)
    phonon.produce_force_constants()

    # dense mesh for DOS / global minimum frequency
    phonon.run_mesh([16, 16, 16])
    mesh = phonon.get_mesh_dict()
    freqs = mesh["frequencies"]                      # THz
    fmin = float(freqs.min())
    # ignore the three acoustic modes at Gamma, which are ~0 by construction
    nonzero = freqs[np.abs(freqs) > 1e-3]
    n_imag = int((freqs < -1e-2).sum())
    frac_imag = n_imag / freqs.size

    phonon.run_total_dos()
    dos = phonon.get_total_dos_dict()
    panels.append((ph, dos["frequency_points"], dos["total_dos"], fmin))
    summary.append({"phase": ph, "supercell": "x".join(map(str, SUPER[ph])),
                    "n_atoms_supercell": len(ref)*int(np.prod(SUPER[ph])),
                    "n_displacements": len(sets),
                    "min_freq_THz": fmin, "max_freq_THz": float(freqs.max()),
                    "n_imaginary_modes": n_imag,
                    "frac_imaginary": frac_imag,
                    "DYNAMICALLY_STABLE": bool(n_imag == 0)})
    print(f"  {ph:7s} supercell={SUPER[ph]} ndisp={len(sets):3d} "
          f"min={fmin:7.3f} THz max={freqs.max():6.2f} THz  imaginary={n_imag}/{freqs.size} "
          f"-> {'STABLE' if n_imag==0 else 'IMAGINARY MODES PRESENT'}", flush=True)

df = pd.DataFrame(summary)
df.to_csv(os.path.join(C.RESULTS, "phonons", "phonon_summary.csv"), index=False)

fig, axes = plt.subplots(1, 5, figsize=(19, 3.6))
for ax, (ph, x, y, fmin) in zip(axes, panels):
    ax.fill_between(x, 0, y, color="#1baf7a", alpha=0.85, lw=0)
    ax.axvline(0, color="#9a9a94", lw=1.0, ls=":")
    ax.set_title(f"{ph}   min = {fmin:.3f} THz", fontsize=10, loc="left")
    ax.set_xlabel("frequency (THz)")
    if ax is axes[0]: ax.set_ylabel("phonon DOS (states/THz)")
    for s in ("top","right"): ax.spines[s].set_visible(False)
    ax.grid(True, lw=0.4, color="#e4e4de"); ax.set_axisbelow(True)
fig.suptitle("Phase 9: phonon density of states, MACE combined227 (16x16x16 mesh). "
             "Negative frequency = imaginary mode = dynamical instability.",
             x=0.005, ha="left", fontsize=12)
fig.tight_layout(rect=[0,0,1,0.93])
fig.savefig(os.path.join(C.RESULTS, "phonons", "phonon_dos_all.png"), dpi=150)
pd.set_option("display.width", 220)
print("\n" + df.to_string(index=False, float_format=lambda v: f"{v:10.4f}"))
