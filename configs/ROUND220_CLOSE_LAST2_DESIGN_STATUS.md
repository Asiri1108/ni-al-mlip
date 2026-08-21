# Round-220: Close the Last 2 EXTRAPOLATION Flags (design-only, NO DFT run)

Generated UTC: 2026-08-17T14:29:32.114721+00:00
Targets: cfg041 (Al3Ni uniaxial_z compression, BLIND_HOLDOUT), cfg107 (Al3Ni volume_rattle compression, VALIDATION).
Each candidate = Nx the flagged point's own magnitude, same sign/axis/family (N swept from 1.1x; smallest passing found: cfg283=1.4x, cfg284=1.2x).
cfg109/cfg110 NOT read or referenced. Gate (b) uses the Al3Ni BLIND_HOLDOUT/TEST population already in combined-218 as the leak reference.

## Gate results

| config_id | gap closed | flagged value | candidate value | closes by construction | min dist TRAIN | nearest TRAIN | thr(a) | min dist RESERVED | nearest RESERVED | thr(b) | gate(a) | gate(b) | gate(c) | gate(d) | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cfg283_Al3Ni_uniaxial_z_compression | cfg041_Al3Ni_uniaxial_z_compression | -0.0220 | -0.0308 | Y | 0.7634 | cfg175_Al3Ni_uniaxial_z_compression | 0.7551 | 0.4227 | cfg041_Al3Ni_uniaxial_z_compression | 0.3417 | PASS | PASS | PASS | PASS | **KEPT** |
| cfg284_Al3Ni_volume_rattle_compression | cfg107_Al3Ni_volume_rattle_compression | -0.0400 | -0.0480 | Y | 0.8672 | cfg101_Al3Ni_iso_compression | 0.7551 | 3.9062 | cfg041_Al3Ni_uniaxial_z_compression | 0.3417 | PASS | PASS | PASS | PASS | **KEPT** |

KEPT: 2/2

## Not done in this pass
DFT has not been run. No merge into any TRAIN/VALIDATION split. cfg109/cfg110 were never read or referenced.
