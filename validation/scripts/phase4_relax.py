"""Phase 4: relaxation from the DFT-relaxed geometry + lattice comparison table."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, common as C
from ase.optimize import FIRE
from ase.filters import FrechetCellFilter

atoms, split = C.load_dataset("combined227")
relaxed = {a.info["phase"]: a for a in atoms if a.info["config_type"] == "relaxed"}
calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))

rows = []
for ph in C.PHASES:
    ref = relaxed[ph]
    d = ref.cell.cellpar()          # DFT reference lattice
    Vd = ref.get_volume(); Nd = len(ref)
    Ed = ref.get_potential_energy() / Nd

    w = ref.copy(); w.calc = calc
    E0 = w.get_potential_energy() / Nd            # MACE energy at the DFT geometry
    opt = FIRE(FrechetCellFilter(w), logfile=os.devnull)
    opt.run(fmax=0.01, steps=500)
    m = w.cell.cellpar(); Vm = w.get_volume()
    Em = w.get_potential_energy() / len(w)
    fmax = float(np.abs(w.get_forces()).max())

    rows.append({
        "phase": ph, "x_Ni": C.X_NI[ph], "natoms": Nd, "converged": bool(opt.converged()),
        "steps": opt.get_number_of_steps(), "final_fmax_eV_A": fmax,
        "a_dft": d[0], "b_dft": d[1], "c_dft": d[2],
        "alpha_dft": d[3], "beta_dft": d[4], "gamma_dft": d[5], "V_dft": Vd,
        "a_mace": m[0], "b_mace": m[1], "c_mace": m[2],
        "alpha_mace": m[3], "beta_mace": m[4], "gamma_mace": m[5], "V_mace": Vm,
        "da": m[0]-d[0], "db": m[1]-d[1], "dc": m[2]-d[2],
        "dalpha": m[3]-d[3], "dbeta": m[4]-d[4], "dgamma": m[5]-d[5],
        "max_abs_dabc_A": max(abs(m[i]-d[i]) for i in range(3)),
        "dV_over_V_pct": (Vm-Vd)/Vd*100.0,
        "E_per_atom_dft": Ed, "E_per_atom_mace_at_dft_geom": E0,
        "E_per_atom_mace_relaxed": Em,
        "dE_relax_meV_atom": (Em-E0)*1000.0,
    })
    print(f"  {ph:7s} steps={opt.get_number_of_steps():4d} conv={opt.converged()} "
          f"max|d(a,b,c)|={rows[-1]['max_abs_dabc_A']:.4f} A  dV/V={rows[-1]['dV_over_V_pct']:+.3f}%", flush=True)

df = pd.DataFrame(rows)
# Pre-registered gates: |d(a,b,c)| < 0.05 A and |dV/V| < 2%
df["PASS_dabc"] = df.max_abs_dabc_A < C.THRESHOLDS["relax_dabc_A"]
df["PASS_dV"] = df.dV_over_V_pct.abs() < C.THRESHOLDS["relax_dV_frac"]*100
df["PASS"] = df.PASS_dabc & df.PASS_dV
df.to_csv(os.path.join(C.RESULTS, "relaxation_lattice_table.csv"), index=False)

pd.set_option("display.width", 250)
print("\n=== LATTICE COMPARISON (MACE relaxed vs DFT relaxed) ===")
print(df[["phase","a_dft","a_mace","da","b_dft","b_mace","db","c_dft","c_mace","dc",
          "V_dft","V_mace","dV_over_V_pct","max_abs_dabc_A","PASS_dabc","PASS_dV","PASS"]]
      .to_string(index=False, float_format=lambda v: f"{v:9.4f}"))
print("\n=== ANGLES ===")
print(df[["phase","alpha_dft","alpha_mace","beta_dft","beta_mace","gamma_dft","gamma_mace"]]
      .to_string(index=False, float_format=lambda v: f"{v:9.4f}"))

# markdown block for the Hugging Face model card
L = ["# Lattice parameters: combined227 LoRA MACE vs QE/PBE DFT",
     "",
     "Relaxation: FIRE + FrechetCellFilter, fmax = 0.01 eV/A, started from the",
     "DFT-relaxed geometry. Gates pre-registered before measurement:",
     "|d(a,b,c)| < 0.05 A and |dV/V| < 2%.",
     "",
     "| Phase | x_Ni | a DFT / MACE (A) | b DFT / MACE (A) | c DFT / MACE (A) | V DFT / MACE (A^3) | dV/V (%) | max abs d(a,b,c) (A) | Gate |",
     "|---|---|---|---|---|---|---|---|---|"]
for _, r in df.iterrows():
    L.append(f"| {r.phase} | {r.x_Ni:.3f} | {r.a_dft:.4f} / {r.a_mace:.4f} | "
             f"{r.b_dft:.4f} / {r.b_mace:.4f} | {r.c_dft:.4f} / {r.c_mace:.4f} | "
             f"{r.V_dft:.3f} / {r.V_mace:.3f} | {r.dV_over_V_pct:+.3f} | "
             f"{r.max_abs_dabc_A:.4f} | {'PASS' if r.PASS else 'FAIL'} |")
L += ["", f"All five phases: {'PASS' if df.PASS.all() else 'NOT ALL PASS'} "
          f"({int(df.PASS.sum())}/5 within both gates).",
      "", "Angles are preserved to within "
      f"{max(df[['dalpha','dbeta','dgamma']].abs().max()):.4f} degrees in all phases."]
open(os.path.join(C.RESULTS, "lattice_table_for_hf_card.md"), "w").write("\n".join(L))
print("\nWrote results/lattice_table_for_hf_card.md")
