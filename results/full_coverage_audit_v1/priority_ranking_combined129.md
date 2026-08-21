# Full Coverage / Extrapolation-Ceiling Audit -- Updated for Combined-129

**Reconstruction, not a verified rerun** -- same caveats as the combined-127 update (`scripts/update_full_coverage_audit_combined127.py`): TRAIN-range/zero-support method reproduced from documented conventions; the geometry-descriptor "local density" analysis is NOT reproduced (original script not found on disk). Compared against the combined-127 audit (immediately-prior checkpoint), not the original combined-113 one, to isolate what round4 specifically changed.

cfg109/cfg110 excluded (sealed, untouched, never loaded).

## Per-phase population and TRAIN counts (combined-129)

| Phase | TOTAL | TRAIN | VALIDATION | TEST | BLIND_HOLDOUT |
|---|---|---|---|---|---|
| Al3Ni | 38 | 27 | 6 | 1 | 4 |
| Al3Ni2 | 22 | 15 | 3 | 1 | 3 |
| Al3Ni5 | 25 | 17 | 3 | 1 | 4 |
| AlNi | 22 | 16 | 3 | 1 | 2 |
| AlNi3 | 22 | 16 | 3 | 1 | 2 |
| **TOTAL** | **129** | **91** | **18** | **5** | **15** |

(TOTAL should read 129 = 91 TRAIN + 18 VALIDATION + 5 TEST + 15 BLIND_HOLDOUT; cfg109/cfg110 sealed, excluded from this count entirely.)

## Configs that CLOSED an EXTRAPOLATION flag since combined-127

(none)

## EXTRAPOLATION flags STILL OPEN after round4

| Phase | Family | Config | Role | Flag | Detail |
|---|---|---|---|---|---|
| Al3Ni | biaxial | cfg039_Al3Ni_biaxial_xy_expansion | VALIDATION | EXTRAPOLATION | outside TRAIN [0.0180, 0.0180] by 0.0060 |
| Al3Ni | shear | cfg042_Al3Ni_shear_xz_negative | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0100, 0.0100] by 0.0080 |
| Al3Ni | shear_rattle | cfg044_Al3Ni_shear_rattle_xy_negative | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [0.0200, 0.0200] by 0.0450 |
| Al3Ni | uniaxial | cfg041_Al3Ni_uniaxial_z_compression | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0150, 0.0150] by 0.0070 |
| Al3Ni | volume_rattle | cfg107_Al3Ni_volume_rattle_compression | VALIDATION | EXTRAPOLATION | outside TRAIN [-0.0250, 0.0560] by 0.0150 |
| Al3Ni2 | biaxial | cfg073_Al3Ni2_biaxial_xy_compression | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0270, -0.0270] by 0.0090 |
| Al3Ni2 | orthorhombic | cfg071_Al3Ni2_orthorhombic_xy | VALIDATION | EXTRAPOLATION | outside TRAIN [0.0240, 0.0240] by 0.0080 |
| Al3Ni2 | shear | cfg074_Al3Ni2_shear_xz_negative | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0100, -0.0100] by 0.0120 |
| Al3Ni2 | shear_rattle | cfg072_Al3Ni2_shear_rattle_yz_positive | VALIDATION | EXTRAPOLATION | outside TRAIN [0.0270, 0.0270] by 0.0090 |
| Al3Ni2 | volume_rattle | cfg075_Al3Ni2_volume_rattle_expansion | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0250, -0.0250] by 0.0600 |
| Al3Ni5 | biaxial | cfg058_Al3Ni5_biaxial_xz_compression | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0240, -0.0240] by 0.0080 |
| Al3Ni5 | rattle | cfg061_Al3Ni5_rattle_xlarge | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [0.0100, 0.0400] by 0.0100 |
| Al3Ni5 | shear | cfg059_Al3Ni5_shear_yz_negative | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0100, 0.0100] by 0.0120 |
| Al3Ni5 | shear_rattle | cfg057_Al3Ni5_shear_rattle_xz_positive | VALIDATION | EXTRAPOLATION | outside TRAIN [0.0270, 0.0270] by 0.0090 |
| Al3Ni5 | volume_rattle | cfg060_Al3Ni5_volume_rattle_expansion | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0250, -0.0250] by 0.0600 |
| AlNi | biaxial | cfg087_AlNi_biaxial_xz_compression | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0270, -0.0270] by 0.0090 |
| AlNi | orthorhombic | cfg085_AlNi_orthorhombic_yz | VALIDATION | EXTRAPOLATION | outside TRAIN [0.0240, 0.0240] by 0.0080 |
| AlNi3 | biaxial | cfg099_AlNi3_biaxial_yz_expansion | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [0.0270, 0.0270] by 0.0090 |
| AlNi3 | orthorhombic | cfg097_AlNi3_orthorhombic_xz | VALIDATION | EXTRAPOLATION | outside TRAIN [0.0240, 0.0240] by 0.0080 |
| AlNi3 | shear_rattle | cfg100_AlNi3_shear_rattle_xz_negative | BLIND_HOLDOUT | EXTRAPOLATION | outside TRAIN [-0.0290, -0.0290] by 0.0070 |

## Zero-TRAIN-support buckets remaining (Tier 1 equivalent)

(none -- every phase/family bucket now has at least one TRAIN member)

## New flags not present in the combined-127 audit (should not normally happen; investigate if non-empty)

(none)

## Round4 gap-bucket status (Al3Ni5/biaxial, AlNi3/biaxial)

- Al3Ni5/biaxial: only 1 TRAIN member(s) -- gap analysis not meaningful
- AlNi3/biaxial: only 1 TRAIN member(s) -- gap analysis not meaningful
