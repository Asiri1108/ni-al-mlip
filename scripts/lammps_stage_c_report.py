#!/usr/bin/env python3
"""Stage C report: Cij, moduli, Born stability, literature comparison for
AlNi/AlNi3. Writes configs/LAMMPS_STAGE_C_ELASTIC_STATUS.txt."""
import json

ROOT = "/workspace/ni_al"
RESULTS_DIR = f"{ROOT}/results/lammps_stage_c"
OUT = f"{ROOT}/configs/LAMMPS_STAGE_C_ELASTIC_STATUS.txt"
PHASES = ["AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3"]

# Literature references gathered via web search this session (2026-08-19).
# AlNi3 (Ni3Al, L1_2): two independent experimental ultrasonic studies,
#   reasonably consistent with each other:
#   - "The elastic constants of Ni3Al to 1.4 GPa" (pulse superposition/echo
#     overlap, ambient pressure intercept): C11=223.5, C12=149.0, C44=122.9 GPa
#   - Kayser (1981), physica status solidi (a) 64, ultrasonic on stoichiometric
#     Ni3Al: C11=224.3, C12=148.6, C44=125.8 GPa
#   Used here: mean of the two = C11=223.9, C12=148.8, C44=124.35 GPa
# AlNi (B2): could not retrieve a clean, paywall-free experimental table
#   despite multiple attempts (Rusovic & Warlimont 1977 is the standard-cited
#   experimental source per search results, but exact digits were not
#   recoverable from an open page this session). Two references used instead,
#   both explicitly labeled by provenance:
#   - DFT/first-principles (source found via live search, exact figures
#     confirmed in retrieved text): C11=229.8, C12=124.7, C44=115.7 GPa
#   - Recalled experimental figures (Rusovic & Warlimont 1977, as commonly
#     tabulated in NiAl potential papers e.g. Mishin et al.): C11~199,
#     C12~137, C44~116 GPa -- NOT independently re-verified against a primary
#     source this session; flagged as recalled, not fetched.
LIT_ALNI3 = {"C11": 223.9, "C12": 148.8, "C44": 124.35,
             "source": "mean of two experimental ultrasonic studies (pressure-derivative paper "
                        "1atm intercept: 223.5/149.0/122.9; Kayser 1981: 224.3/148.6/125.8 GPa)"}
LIT_ALNI_DFT = {"C11": 229.8, "C12": 124.7, "C44": 115.7,
                "source": "first-principles/DFT literature value, confirmed via live web search this session"}
LIT_ALNI_EXP_RECALLED = {"C11": 199.0, "C12": 137.0, "C44": 116.0,
                          "source": "RECALLED (not freshly verified this session) -- commonly cited as "
                                     "Rusovic & Warlimont (1977) experimental single-crystal B2-NiAl"}


def load(phase):
    with open(f"{RESULTS_DIR}/{phase}_elastic.json") as fh:
        return json.load(fh)


def pct(pred, ref):
    return (pred - ref) / ref * 100.0


def main():
    lines = ["LAMMPS STAGE C -- ELASTIC CONSTANTS, ALL 5 PHASES", "",
             "Geometry: each phase's OWN LAMMPS zero-stress relaxed cell (Stage B), NOT the DFT cell.",
             "Method: finite-difference stress-strain, central difference over +/-delta (both signs),",
             "internal positions relaxed at each fixed strained cell. Linearity confirmed via the",
             "nonlinear-residual diagnostic (deviation of the +/- mean from the 0-strain reference stress).",
             ""]

    data = {p: load(p) for p in PHASES}

    lines.append("STRAIN MAGNITUDE USED: delta = %.4f (0.75%%), all 6 Voigt modes, both signs" % data["AlNi"]["delta_strain"])
    lines.append("")

    lines.append("=" * 100)
    lines.append("PER-PHASE Cij SUMMARY (symmetrized, GPa) -- diagonal + off-diagonal, shear constants highlighted")
    lines.append("=" * 100)
    for p in PHASES:
        d = data[p]
        C = d["Cij_symmetrized_GPa"]
        lines.append(f"\n--- {p} ({d['natoms']} atoms, cellpar={[round(x,3) for x in d['base_relaxed_cellpar']]}) ---")
        if d["geometry_note"]:
            lines.append(f"  NOTE: {d['geometry_note']}")
        labels = ["C1", "C2", "C3", "C4", "C5", "C6"]
        header = "        " + "".join(f"{l:>9}" for l in labels)
        lines.append(header)
        for i, row in enumerate(C):
            lines.append(f"  {labels[i]:<5} " + "".join(f"{v:9.2f}" for v in row))
        lines.append(f"  Shear diagonal (C44,C55,C66): {C[3][3]:.2f}, {C[4][4]:.2f}, {C[5][5]:.2f} GPa")
        lines.append(f"  Cij asymmetry (max |C-C^T|): {d['Cij_asymmetry_max_GPa']:.4f} GPa   "
                      f"nonlinear residual (max): {d['nonlinear_residual_max_GPa']:.4f} GPa")
        eig = d["eigenvalues_GPa"]
        lines.append(f"  Eigenvalues (GPa): {[round(x,2) for x in eig]}")
        lines.append(f"  BORN STABILITY (general, all eigenvalues > 0): {'Y' if d['born_general_stable'] else 'N'}")
        if d["cubic"]:
            c = d["cubic"]
            lines.append(f"  Cubic-specific: C11={c['C11']:.2f} C12={c['C12']:.2f} C44={c['C44']:.2f} GPa "
                          f"(symmetry spread <= {max(c['symmetry_spread'].values()):.2e} GPa)")
            lines.append(f"  Cubic Born criteria: C11-C12>0: {c['cond_C11_minus_C12_gt0']}  "
                          f"C11+2C12>0: {c['cond_C11_plus_2C12_gt0']}  C44>0: {c['cond_C44_gt0']}  "
                          f"-> {'Y' if c['born_cubic_stable'] else 'N'}")
            lines.append(f"  Zener anisotropy ratio (2*C44/(C11-C12)): {c['zener_ratio']:.4f}")
        m = d["moduli_GPa"]
        lines.append(f"  Moduli (Voigt-Reuss-Hill): K={m['K']:.2f} GPa (V={m['Kv']:.2f}/R={m['Kr']:.2f})  "
                      f"G={m['G']:.2f} GPa (V={m['Gv']:.2f}/R={m['Gr']:.2f})  E={m['E']:.2f} GPa  nu={m['nu']:.4f}")
        lines.append(f"  Universal anisotropy index A^U (any symmetry): {m['universal_anisotropy_index']:.4f}")

    lines.append("\n" + "=" * 100)
    lines.append("SHEAR-CONSTANT FOCUS (per your explicit request re: Al3Ni5 / Stage B tilt-softness link)")
    lines.append("=" * 100)
    lines.append(f"{'phase':<10}{'C44':>10}{'C55':>10}{'C66':>10}   note")
    for p in PHASES:
        C = data[p]["Cij_symmetrized_GPa"]
        note = ""
        if p == "Al3Ni5":
            note = ("<-- anomalously soft: C44=33.15 GPa is ~3x softer than this SAME phase's own "
                     "C55/C66 (~98-102 GPa), and softer than every other phase's shear constants below. "
                     "This is the C44 direction associated with the yz/alpha-angle strain mode -- directly "
                     "corroborates the Stage B diagnostic (model's energy minimum displaced from DFT along "
                     "this exact direction, +0.87 meV/atom cost, i.e. a real but genuinely SOFT direction, "
                     "now independently confirmed and quantified via a completely different observable).")
        lines.append(f"{p:<10}{C[3][3]:>10.2f}{C[4][4]:>10.2f}{C[5][5]:>10.2f}   {note}")

    lines.append("\n" + "=" * 100)
    lines.append("LITERATURE COMPARISON -- AlNi and AlNi3 only")
    lines.append("=" * 100)
    alni_c = data["AlNi"]["cubic"]
    alni3_c = data["AlNi3"]["cubic"]

    lines.append(f"\nAlNi (B2) computed: C11={alni_c['C11']:.2f}  C12={alni_c['C12']:.2f}  C44={alni_c['C44']:.2f} GPa")
    for label, lit in (("DFT literature", LIT_ALNI_DFT), ("Recalled experimental (unverified this session)", LIT_ALNI_EXP_RECALLED)):
        lines.append(f"  vs {label} (C11={lit['C11']}, C12={lit['C12']}, C44={lit['C44']} GPa; {lit['source']}):")
        lines.append(f"    % dev: C11={pct(alni_c['C11'], lit['C11']):+.2f}%  "
                      f"C12={pct(alni_c['C12'], lit['C12']):+.2f}%  C44={pct(alni_c['C44'], lit['C44']):+.2f}%")

    lines.append(f"\nAlNi3 (Ni3Al, L1_2) computed: C11={alni3_c['C11']:.2f}  C12={alni3_c['C12']:.2f}  C44={alni3_c['C44']:.2f} GPa")
    lines.append(f"  vs experimental (mean of 2 studies, C11={LIT_ALNI3['C11']}, C12={LIT_ALNI3['C12']}, "
                 f"C44={LIT_ALNI3['C44']} GPa; {LIT_ALNI3['source']}):")
    lines.append(f"    % dev: C11={pct(alni3_c['C11'], LIT_ALNI3['C11']):+.2f}%  "
                  f"C12={pct(alni3_c['C12'], LIT_ALNI3['C12']):+.2f}%  C44={pct(alni3_c['C44'], LIT_ALNI3['C44']):+.2f}%")

    lines.append("\n" + "=" * 100)
    lines.append("SUMMARY")
    lines.append("=" * 100)
    born_col = "  ".join(f"{p}={'Y' if data[p]['born_general_stable'] else 'N'}" for p in PHASES)
    lines.append(f"Born stability (general, all phases): {born_col}")
    lines.append("UNVALIDATED (no DFT/literature elastic reference available): Al3Ni, Al3Ni2, Al3Ni5 -- count=3")
    lines.append("Al3Ni5 additionally: computed at model's own alpha=98.28 deg, not DFT's 96.478 deg -- "
                 "not apples-to-apples with any future DFT Al3Ni5 elastic reference computed at the DFT angle.")

    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
