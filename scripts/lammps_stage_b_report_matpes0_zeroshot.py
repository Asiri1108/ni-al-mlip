#!/usr/bin/env python3
"""Stage B report (ZERO-SHOT variant): DFT vs LAMMPS lattice parameters,
volume/atom, symmetry, convergence, for all 5 phases, using MACE-MATPES-PBE-0
zero-shot. Writes configs/LAMMPS_STAGE_B_MATPES_PBE0_ZEROSHOT_STATUS.txt.
Same DFT reference (QE/PBE relaxed cells) as the fine-tuned Stage B report,
for a clean single-reference before/after comparison.
"""
import json
import os

import numpy as np

from lattice_compare_utils import load_dft_relaxed, cellpar_and_vpa, spacegroup_of, pct_diff, PHASES

ROOT = "/workspace/ni_al"
RESULTS_DIR = f"{ROOT}/results/lammps_stage_b_matpes_pbe0_zeroshot"
OUT = f"{ROOT}/configs/LAMMPS_STAGE_B_MATPES_PBE0_ZEROSHOT_STATUS.txt"

LABELS = ["a", "b", "c", "alpha", "beta", "gamma"]


def load_json(phase, tag):
    path = f"{RESULTS_DIR}/{phase}_{tag}.json"
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def fmt_cellpar(cp):
    return (f"a={cp[0]:.5f} b={cp[1]:.5f} c={cp[2]:.5f}  "
            f"alpha={cp[3]:.4f} beta={cp[4]:.4f} gamma={cp[5]:.4f}")


def main():
    lines = ["LAMMPS STAGE B (ZERO-SHOT) -- 5-PHASE RELAXATION vs QE/PBE DFT",
             "Model: MACE-MATPES-PBE-0 zero-shot foundation checkpoint (LAMMPS mliap unified, Kokkos build)",
             "Same QE/PBE relaxed reference cells as the fine-tuned Stage B run -- single-reference before/after.",
             ""]
    table_rows = []
    max_vol_err = 0.0
    symmetry_ok_count = 0

    for phase in PHASES:
        dft_atoms = load_dft_relaxed(phase)
        dft_cellpar, dft_vpa = cellpar_and_vpa(dft_atoms)
        dft_sg_symbol, dft_sg_number = spacegroup_of(dft_atoms)

        lmp_r = load_json(phase, "lammps")

        lines.append(f"=== {phase} ({len(dft_atoms)} atoms) ===")
        lines.append(f"  DFT reference:    {fmt_cellpar(dft_cellpar)}  V/atom={dft_vpa:.5f} A^3  "
                      f"spacegroup={dft_sg_symbol} (#{dft_sg_number})")

        if lmp_r is None:
            lines.append("  LAMMPS: DID NOT COMPLETE (subprocess failed -- see logs/lammps_stage_b_matpes_pbe0_zeroshot/)")
            table_rows.append((phase, None, None, None, "FAILED"))
        else:
            lmp_cellpar = np.array(lmp_r["cellpar"])
            lmp_vpa = lmp_r["volume_per_atom_A3"]
            cp_pct = pct_diff(lmp_cellpar, dft_cellpar)
            vol_pct = (lmp_vpa - dft_vpa) / dft_vpa * 100.0
            max_vol_err = max(max_vol_err, abs(vol_pct))
            sym_ok = lmp_r["spacegroup_number"] == dft_sg_number
            symmetry_ok_count += int(sym_ok)

            lines.append(f"  LAMMPS relaxed:   {fmt_cellpar(lmp_cellpar)}  V/atom={lmp_vpa:.5f} A^3  "
                          f"spacegroup={lmp_r['spacegroup_symbol']} (#{lmp_r['spacegroup_number']})")
            lines.append(f"  LAMMPS vs DFT %%: " + "  ".join(
                f"{lbl}={v:+.4f}%" for lbl, v in zip(LABELS, cp_pct)))
            lines.append(f"  LAMMPS vs DFT volume/atom: {vol_pct:+.4f}%")
            lines.append(f"  Symmetry preserved (spacegroup # match): {'Y' if sym_ok else 'N'}")
            lines.append(f"  Convergence: {lmp_r['stopping_criterion']} "
                          f"(fmax={lmp_r['fmax_final_eV_per_A']:.3e} eV/A, press={lmp_r['press_final_bar']:.3f} bar)")
            table_rows.append((phase, vol_pct, max(abs(v) for v in cp_pct), sym_ok, "OK"))
        lines.append("")

    lines.append("=" * 78)
    lines.append("SUMMARY TABLE (LAMMPS zero-shot MACE-MATPES-PBE-0 vs QE/PBE DFT)")
    lines.append(f"{'phase':<10}{'vol/atom % err':>16}{'max |lattice %|':>18}{'symmetry':>10}{'status':>10}")
    for phase, vol_pct, max_cp_pct, sym_ok, status in table_rows:
        if status == "FAILED":
            lines.append(f"{phase:<10}{'--':>16}{'--':>18}{'--':>10}{status:>10}")
        else:
            lines.append(f"{phase:<10}{vol_pct:>+15.4f}%{max_cp_pct:>17.4f}%{('Y' if sym_ok else 'N'):>10}{status:>10}")

    n_completed = sum(1 for r in table_rows if r[4] == "OK")
    lines.append("")
    lines.append(f"Max |volume/atom error| (LAMMPS vs DFT, over completed phases): {max_vol_err:.4f}%")
    lines.append(f"Symmetry preserved: {symmetry_ok_count}/{len(PHASES)}")
    lines.append(f"Phases completed: {n_completed}/{len(PHASES)}")
    lines.append("")
    lines.append("Note: fine-tuned Stage B (configs/LAMMPS_STAGE_B_RELAXATION_STATUS.txt) max "
                  "volume/atom error vs the SAME QE/PBE reference: 0.2159% (Al3Ni5), symmetry 5/5.")

    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
