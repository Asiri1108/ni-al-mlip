# Full Coverage / Extrapolation-Ceiling Audit -- Updated for Combined-218

Reconstruction (same caveats as prior updates). Compared vs combined-211 to isolate
round212/213/214's effect. cfg109/cfg110 excluded (sealed, untouched, never loaded).

## Per-phase population and TRAIN counts (combined-218)

| Phase | TOTAL | TRAIN | VALIDATION | TEST | BLIND_HOLDOUT |
|---|---|---|---|---|---|
| Al3Ni | 55 | 44 | 6 | 1 | 4 |
| Al3Ni2 | 37 | 30 | 3 | 1 | 3 |
| Al3Ni5 | 41 | 33 | 3 | 1 | 4 |
| AlNi | 39 | 33 | 3 | 1 | 2 |
| AlNi3 | 40 | 34 | 3 | 1 | 2 |
| **TOTAL** | **212** | **174** | | | |

## Configs that CLOSED an EXTRAPOLATION flag since combined-211

| Phase | Family | Config | Old flag | New flag |
|---|---|---|---|---|
| Al3Ni | shear | cfg042_Al3Ni_shear_xz_negative | EXTRAPOLATION | OK_IN_RANGE |
| Al3Ni2 | shear | cfg074_Al3Ni2_shear_xz_negative | EXTRAPOLATION | OK_IN_RANGE |
| Al3Ni5 | rattle | cfg061_Al3Ni5_rattle_xlarge | EXTRAPOLATION | OK_IN_RANGE |
| Al3Ni5 | shear | cfg059_Al3Ni5_shear_yz_negative | EXTRAPOLATION | OK_IN_RANGE |

## EXTRAPOLATION flags STILL OPEN after round212/213/214

| Phase | Family | Config | Role | Flag | Detail |
|---|---|---|---|---|---|
| Al3Ni | uniaxial | cfg041_Al3Ni_uniaxial_z_compression | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0150, 0.0195] by 0.0070 |
| Al3Ni | volume_rattle | cfg107_Al3Ni_volume_rattle_compression | VALIDATION | EXTRAPOLATION | outside TRAIN [-0.0250, 0.0560] by 0.0150 |

## Zero-TRAIN-support buckets remaining

(none)

## INFO_LOW_TRAIN_COUNT buckets remaining

- Al3Ni2/rattle
- Al3Ni2/shear
- Al3Ni2/volume_rattle
- Al3Ni5/volume_rattle
- AlNi/rattle
- AlNi/volume_rattle
- AlNi3/rattle
- AlNi3/shear

## New flags not present in the combined-211 audit (investigate if non-empty)

(none)
