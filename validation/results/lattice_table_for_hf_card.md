# Lattice parameters: combined227 LoRA MACE vs QE/PBE DFT

Relaxation: FIRE + FrechetCellFilter, fmax = 0.01 eV/A, started from the
DFT-relaxed geometry.

**Gates pre-registered before measurement (lengths and volume ONLY):**
`|d(a,b,c)| < 0.05 A` and `|dV/V| < 2%`.

**Cell ANGLES were NOT gated.** No angular tolerance was pre-registered, so the
angle column below is reported, not judged. This matters - see the open defect
immediately after the table.

| Phase | x_Ni | a DFT / MACE (A) | b DFT / MACE (A) | c DFT / MACE (A) | V DFT / MACE (A^3) | dV/V (%) | max abs d(a,b,c) (A) | Gate (lengths+volume) |
|---|---|---|---|---|---|---|---|---|
| Al3Ni | 0.250 | 4.8255 / 4.8160 | 6.6230 / 6.6067 | 7.3825 / 7.4194 | 235.941 / 236.071 | +0.055 | 0.0370 | PASS |
| Al3Ni2 | 0.400 | 4.0449 / 4.0509 | 4.0449 / 4.0509 | 4.9079 / 4.8997 | 69.541 / 69.633 | +0.132 | 0.0081 | PASS |
| AlNi | 0.500 | 2.8940 / 2.8947 | 2.8940 / 2.8947 | 2.8940 / 2.8947 | 24.238 / 24.255 | +0.070 | 0.0007 | PASS |
| Al3Ni5 | 0.625 | 3.7623 / 3.7978 | 5.0118 / 5.0032 | 5.0118 / 5.0032 | 93.898 / 94.085 | +0.199 | 0.0355 | PASS |
| AlNi3 | 0.750 | 3.5673 / 3.5673 | 3.5674 / 3.5674 | 3.5674 / 3.5674 | 45.398 / 45.398 | +0.000 | 0.0000 | PASS |

Lengths and volume: **5/5 within both gates**.

## Open defect: Al3Ni5 alpha angle

| Phase | alpha DFT | alpha MACE | drift |
|---|---|---|---|
| Al3Ni | 90.0000 | 90.0000 | +0.0000 |
| Al3Ni2 | 90.0000 | 90.0000 | +0.0000 |
| AlNi | 90.0000 | 90.0000 | +0.0000 |
| Al3Ni5 | 96.4781 | 98.2481 | +1.7701 **<-- open defect** |
| AlNi3 | 90.0000 | 90.0000 | +0.0000 |

**Al3Ni5 relaxes to alpha = 98.248 deg against a DFT reference of 96.478 deg - a
drift of +1.77 degrees.** This is NOT covered by any pre-registered gate and is NOT
reassurance: it is an unresolved defect. Corroborating evidence that it is a real
feature of the model's energy surface, not a relaxation artefact:

- An independent LAMMPS ML-IAP relaxation of the same model gives 98.279 deg
  (agreement with this ASE run to 0.031 deg).
- Constraining alpha back to the DFT value costs 0.87 meV/atom, about 2x the
  measured 0.43 meV/atom seed-noise floor.
- The elastic tensor shows C44 = 32.1 GPa for Al3Ni5, roughly 3x softer than the
  same phase's own C55/C66 (101.6 / 103.8 GPa), in exactly the yz/alpha direction.

**What is NOT established:** whether the true DFT minimum lies nearer 96.5 or 98.2
degrees. Deciding that requires a new DFT relaxation at the shifted geometry, which
was out of scope. Until then, any Al3Ni5 result sensitive to cell angle or to shear
along yz should be treated as unvalidated.

The other four phases preserve all angles to within 1e-4 degrees.
