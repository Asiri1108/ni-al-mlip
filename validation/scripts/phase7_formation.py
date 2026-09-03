"""Phase 7: formation energy, strict. QE chemical potentials only.

E_f = (E_compound - n_Al*mu_Al - n_Ni*mu_Ni) / N.
Elemental-reference models are NEVER used here: the project documents a
linear-in-Ni-content bias when model elemental references are substituted.
Gates: all E_f negative, AND pairwise stability ranking 10/10 vs DFT.
"""
import sys, os, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, common as C

atoms, split = C.load_dataset("combined227")
relaxed = {a.info["phase"]: a for a in atoms if a.info["config_type"] == "relaxed"}
calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))

rows = []
for ph in C.PHASES:
    ref = relaxed[ph]; sym = ref.get_chemical_symbols()
    ef_dft = C.formation_energy(ref.get_potential_energy(), sym)
    w = ref.copy(); w.calc = calc
    ef_mace = C.formation_energy(w.get_potential_energy(), sym)
    rows.append({"phase": ph, "x_Ni": C.X_NI[ph], "natoms": len(ref),
                 "n_Al": sym.count("Al"), "n_Ni": sym.count("Ni"),
                 "Ef_dft_eV_atom": ef_dft, "Ef_mace_eV_atom": ef_mace,
                 "dEf_eV_atom": ef_mace - ef_dft,
                 "dEf_meV_atom": (ef_mace - ef_dft) * 1000,
                 "sign_correct": bool(ef_mace < 0)})
df = pd.DataFrame(rows)

# pairwise ranking, all 10 pairs
pairs = []
for p, q in itertools.combinations(C.PHASES, 2):
    a = df[df.phase == p].iloc[0]; b = df[df.phase == q].iloc[0]
    dft_more_stable = p if a.Ef_dft_eV_atom < b.Ef_dft_eV_atom else q
    mace_more_stable = p if a.Ef_mace_eV_atom < b.Ef_mace_eV_atom else q
    pairs.append({"pair": f"{p} vs {q}",
                  "dft_more_stable": dft_more_stable,
                  "mace_more_stable": mace_more_stable,
                  "agree": dft_more_stable == mace_more_stable,
                  "dft_gap_meV_atom": abs(a.Ef_dft_eV_atom-b.Ef_dft_eV_atom)*1000,
                  "mace_gap_meV_atom": abs(a.Ef_mace_eV_atom-b.Ef_mace_eV_atom)*1000})
pdf = pd.DataFrame(pairs)

df.to_csv(os.path.join(C.RESULTS, "formation_energy.csv"), index=False)
pdf.to_csv(os.path.join(C.RESULTS, "formation_energy_ranking.csv"), index=False)

pd.set_option("display.width", 220)
print("=== FORMATION ENERGY (QE mu_Al / mu_Ni only) ===")
print(df.to_string(index=False, float_format=lambda v: f"{v:10.5f}"))
print(f"\nGATE 1 all negative: {'PASS' if df.sign_correct.all() else 'FAIL'} "
      f"({int(df.sign_correct.sum())}/5)")
print(f"MAE |dEf| = {df.dEf_meV_atom.abs().mean():.3f} meV/atom, "
      f"max = {df.dEf_meV_atom.abs().max():.3f} meV/atom")
print("\n=== PAIRWISE STABILITY RANKING ===")
print(pdf.to_string(index=False, float_format=lambda v: f"{v:9.3f}"))
print(f"\nGATE 2 ranking: {int(pdf.agree.sum())}/10 pairwise agreements -> "
      f"{'PASS' if pdf.agree.all() else 'FAIL'}")
print("\nStability order DFT :", " < ".join(df.sort_values('Ef_dft_eV_atom').phase))
print("Stability order MACE:", " < ".join(df.sort_values('Ef_mace_eV_atom').phase))
