# Round-212: Close the Final 4 EXTRAPOLATION Flags (design-only, NO DFT run)

Generated UTC: 2026-08-16T18:06:55.689705+00:00
Targets: cfg042 (Al3Ni shear_xz), cfg074 (Al3Ni2 shear_xz), cfg059 (Al3Ni5 shear_yz), cfg061 (Al3Ni5 rattle).
Each candidate = 1.1x the flagged point's own magnitude, same sign/axis.

## Gate results

| config_id | gap closed | flagged value | candidate value | min dist to TRAIN | nearest TRAIN | threshold | gate(a) | gate(b) | gate(c) | status |
|---|---|---|---|---|---|---|---|---|---|---|
| cfg273_Al3Ni_shear_xy_negative | cfg042_Al3Ni_shear_xz_negative | -0.0180 | -0.0340 | 0.8263 | cfg033_Al3Ni_shear_xy_negative | 0.6614 | PASS | PASS | PASS | **KEPT** |
| ~~cfg274_Al3Ni2_shear_xy_negative~~ | cfg074_Al3Ni2_shear_xz_negative | -0.0220 | -0.0600 | 1.8285 | cfg198_Al3Ni2_uniaxial_y_compression | 1.1438 | PASS | N/A | PASS | **RETIRED (2026-08-16)** |
| cfg275_Al3Ni5_shear_yz_negative | cfg059_Al3Ni5_shear_yz_negative | -0.0220 | -0.0264 | 1.0626 | Al3Ni5_relaxed | 1.0272 | PASS | N/A | PASS | **KEPT** |
| cfg276_Al3Ni5_rattle_xxlarge | cfg061_Al3Ni5_rattle_xlarge | 0.0500 | 0.0550 | 1.4062 | cfg054_Al3Ni5_rattle_large | 1.0272 | PASS | N/A | PASS | **KEPT** |

KEPT: 3/4 (cfg274 retired -- see below)

## Retirement note (2026-08-16)

`cfg274_Al3Ni2_shear_xy_negative` (-0.06) was superseded by round213's magnitude
sweep (`scripts/design_al3ni2_alni_targeted.py`), which found -0.045 as the
minimum magnitude that clears gate (a) for the same gap (`cfg074`), same axis
(shear_xy), same sign. Both candidates were gate-valid (not a correctness bug),
but keeping both would mean two TRAIN points closing the identical gap for no
added coverage value -- redundant, not wrong. Retired in favor of round213's
`cfg279_Al3Ni2_shear_xy_negative_sweep` (-0.045), the smaller, more
conservative, explicitly-searched-for minimum. Structure/QE input files
deleted from `round212_structures/round212_al3ni2/`; row removed from
`round212_manifest.csv`. `cfg273` (Al3Ni) and `cfg275`/`cfg276` (Al3Ni5) are
unaffected and remain the authoritative closures for their respective gaps.

**Authoritative round212+round213 closure set (4 gaps, all confirmed KEPT):**
- cfg042 (Al3Ni shear) -> `cfg273_Al3Ni_shear_xy_negative` (round212)
- cfg074 (Al3Ni2 shear) -> `cfg279_Al3Ni2_shear_xy_negative_sweep` (round213, -0.045)
- cfg059 (Al3Ni5 shear) -> `cfg275_Al3Ni5_shear_yz_negative` (round212)
- cfg061 (Al3Ni5 rattle) -> `cfg276_Al3Ni5_rattle_xxlarge` (round212)

## Not done in this pass
DFT has not been run. No merge into any TRAIN/VALIDATION split. cfg109/cfg110 remain sealed.
