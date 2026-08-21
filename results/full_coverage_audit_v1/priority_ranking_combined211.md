# Full Coverage / Extrapolation-Ceiling Audit -- Updated for Combined-211

**Reconstruction, not a verified rerun** -- same caveats as prior updates: TRAIN-range/
zero-support method reproduced from documented conventions; the geometry-descriptor
"local density" analysis is NOT reproduced (original script not found on disk).
Compared against the combined-129 audit (immediately-prior checkpoint) to isolate what
round300 (82 configs, 10 pods, full factorial gap-fill) specifically changed.

cfg109/cfg110 excluded (sealed, untouched, never loaded).

## Per-phase population and TRAIN counts (combined-211)

| Phase | TOTAL | TRAIN | VALIDATION | TEST | BLIND_HOLDOUT |
|---|---|---|---|---|---|
| Al3Ni | 55 | 44 | 6 | 1 | 4 |
| Al3Ni2 | 37 | 30 | 3 | 1 | 3 |
| Al3Ni5 | 40 | 32 | 3 | 1 | 4 |
| AlNi | 38 | 32 | 3 | 1 | 2 |
| AlNi3 | 41 | 35 | 3 | 1 | 2 |
| **TOTAL** | **211** | **173** | | | |

## Configs that CLOSED an EXTRAPOLATION flag since combined-129

| Phase | Family | Config | Old flag | New flag |
|---|---|---|---|---|
| Al3Ni | biaxial | cfg039_Al3Ni_biaxial_xy_expansion | EXTRAPOLATION | OK_IN_RANGE |
| Al3Ni | shear_rattle | cfg044_Al3Ni_shear_rattle_xy_negative | EXTRAPOLATION | OK_IN_RANGE |
| Al3Ni2 | biaxial | cfg073_Al3Ni2_biaxial_xy_compression | EXTRAPOLATION | OK_IN_RANGE |
| Al3Ni2 | orthorhombic | cfg071_Al3Ni2_orthorhombic_xy | EXTRAPOLATION | OK_IN_RANGE |
| Al3Ni2 | shear_rattle | cfg072_Al3Ni2_shear_rattle_yz_positive | EXTRAPOLATION | OK_IN_RANGE |
| Al3Ni2 | volume_rattle | cfg075_Al3Ni2_volume_rattle_expansion | EXTRAPOLATION | OK_IN_RANGE |
| Al3Ni5 | biaxial | cfg058_Al3Ni5_biaxial_xz_compression | EXTRAPOLATION | OK_IN_RANGE |
| Al3Ni5 | shear_rattle | cfg057_Al3Ni5_shear_rattle_xz_positive | EXTRAPOLATION | OK_IN_RANGE |
| Al3Ni5 | volume_rattle | cfg060_Al3Ni5_volume_rattle_expansion | EXTRAPOLATION | OK_IN_RANGE |
| AlNi | biaxial | cfg087_AlNi_biaxial_xz_compression | EXTRAPOLATION | OK_IN_RANGE |
| AlNi | orthorhombic | cfg085_AlNi_orthorhombic_yz | EXTRAPOLATION | OK_IN_RANGE |
| AlNi3 | biaxial | cfg099_AlNi3_biaxial_yz_expansion | EXTRAPOLATION | OK_IN_RANGE |
| AlNi3 | orthorhombic | cfg097_AlNi3_orthorhombic_xz | EXTRAPOLATION | OK_IN_RANGE |
| AlNi3 | shear_rattle | cfg100_AlNi3_shear_rattle_xz_negative | EXTRAPOLATION | OK_IN_RANGE |

## EXTRAPOLATION flags STILL OPEN after round300

| Phase | Family | Config | Role | Flag | Detail |
|---|---|---|---|---|---|
| Al3Ni | shear | cfg042_Al3Ni_shear_xz_negative | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0100, 0.0100] by 0.0080 |
| Al3Ni | uniaxial | cfg041_Al3Ni_uniaxial_z_compression | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0150, 0.0195] by 0.0070 |
| Al3Ni | volume_rattle | cfg107_Al3Ni_volume_rattle_compression | VALIDATION | EXTRAPOLATION | outside TRAIN [-0.0250, 0.0560] by 0.0150 |
| Al3Ni2 | shear | cfg074_Al3Ni2_shear_xz_negative | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0100, -0.0100] by 0.0120 |
| Al3Ni5 | rattle | cfg061_Al3Ni5_rattle_xlarge | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [0.0100, 0.0400] by 0.0100 |
| Al3Ni5 | shear | cfg059_Al3Ni5_shear_yz_negative | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0100, 0.0100] by 0.0120 |

## Zero-TRAIN-support buckets remaining (Tier 1 equivalent)

(none -- every phase/family bucket has at least one TRAIN member)

## INFO_LOW_TRAIN_COUNT buckets remaining (1-2 TRAIN members)

- Al3Ni / shear
- Al3Ni2 / rattle
- Al3Ni2 / shear
- Al3Ni2 / volume_rattle
- Al3Ni5 / rattle
- Al3Ni5 / shear
- Al3Ni5 / volume_rattle
- AlNi / rattle
- AlNi / shear
- AlNi / volume_rattle
- AlNi3 / rattle
- AlNi3 / shear

## New flags not present in the combined-129 audit (should not normally happen; investigate if non-empty)

(none)
