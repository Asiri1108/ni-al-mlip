# Round-4 Biaxial Design Status (Al3Ni5, AlNi3)

Design-only. No DFT run. cfg109/cfg110 untouched (different phase; gate (b) N/A).
Generated UTC: 2026-08-16T10:21:29.598928+00:00

## Per-phase gate thresholds (freshly derived, this round, from current combined-127 population)

| Phase | n population | n TRAIN | n pairwise combos | redundancy (5th pct) |
|---|---|---|---|---|
| Al3Ni5 | 24 | 16 | 276 | 0.904588 |
| AlNi3 | 21 | 15 | 210 | 0.751966 |

## Candidate gate results

| config_id | tag | value | probe (id=value) | min dist to TRAIN | nearest TRAIN | threshold | gate(a) | gate(c) | status |
|---|---|---|---|---|---|---|---|---|---|
| cfg142_Al3Ni5_biaxial_xz_compression | inner | -0.0080 | cfg058_Al3Ni5_biaxial_xz_compression=-0.0160 | 0.7467 | cfg045_Al3Ni5_iso_compression | 0.9046 | FAIL_REDUNDANT | PASS | **REJECTED** |
| cfg143_Al3Ni5_biaxial_xz_compression | outer | -0.0240 | cfg058_Al3Ni5_biaxial_xz_compression=-0.0160 | 1.1680 | Al3Ni5_iso_m02 | 0.9046 | PASS | PASS | **KEPT** |
| cfg144_AlNi3_biaxial_yz_expansion | inner | 0.0090 | cfg099_AlNi3_biaxial_yz_expansion=0.0180 | 0.6405 | cfg090_AlNi3_iso_expansion | 0.7520 | FAIL_REDUNDANT | PASS | **REJECTED** |
| cfg145_AlNi3_biaxial_yz_expansion | outer | 0.0270 | cfg099_AlNi3_biaxial_yz_expansion=0.0180 | 1.1739 | AlNi3_iso_p02 | 0.7520 | PASS | PASS | **KEPT** |

## Kept (frozen for future DFT submission -- not run here)

- cfg143_Al3Ni5_biaxial_xz_compression (Al3Ni5, biaxial_xz=-0.0240, outer candidate for gap probe cfg058_Al3Ni5_biaxial_xz_compression)
- cfg145_AlNi3_biaxial_yz_expansion (AlNi3, biaxial_yz=0.0270, outer candidate for gap probe cfg099_AlNi3_biaxial_yz_expansion)

## Rejected

- cfg142_Al3Ni5_biaxial_xz_compression: FAIL_REDUNDANT, PASS
- cfg144_AlNi3_biaxial_yz_expansion: FAIL_REDUNDANT, PASS

## Coverage impact

Before this design: Al3Ni5/biaxial and AlNi3/biaxial were the only two remaining
EXTRAPOLATION_NO_TRAIN_SUPPORT (Tier-1) buckets after round3
(results/full_coverage_audit_v1/priority_ranking_combined127.md).
Kept candidates: 2/4 proposed (2 inner + 2 outer).

## Not done in this pass
DFT has not been run. No production directory execution. No merge into any TRAIN/VALIDATION
split. cfg109/cfg110 remain sealed and untouched.
