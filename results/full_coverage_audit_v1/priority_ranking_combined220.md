# Full Coverage / Extrapolation-Ceiling Audit -- Updated for Combined-220

Reconstruction (same caveats as prior updates). Compared vs combined-218 to isolate
round220's effect. cfg109/cfg110 excluded (sealed, untouched, never loaded).

## Per-phase population and TRAIN counts (combined-220)

| Phase | TOTAL | TRAIN | VALIDATION | TEST | BLIND_HOLDOUT |
|---|---|---|---|---|---|
| Al3Ni | 57 | 46 | 6 | 1 | 4 |
| Al3Ni2 | 37 | 30 | 3 | 1 | 3 |
| Al3Ni5 | 41 | 33 | 3 | 1 | 4 |
| AlNi | 39 | 33 | 3 | 1 | 2 |
| AlNi3 | 40 | 34 | 3 | 1 | 2 |
| **TOTAL** | **214** | **176** | | | |

## Configs that CLOSED an EXTRAPOLATION flag since combined-218

| Phase | Family | Config | Old flag | New flag |
|---|---|---|---|---|
| Al3Ni | uniaxial | cfg041_Al3Ni_uniaxial_z_compression | EXTRAPOLATION | OK_IN_RANGE |
| Al3Ni | volume_rattle | cfg107_Al3Ni_volume_rattle_compression | EXTRAPOLATION | OK_IN_RANGE |

## EXTRAPOLATION flags STILL OPEN after round220

(none -- zero EXTRAPOLATION flags project-wide)

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

## New flags not present in the combined-218 audit (investigate if non-empty)

(none)
