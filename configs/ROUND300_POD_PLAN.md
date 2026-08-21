# Round-300 Pod Assignment Plan (10 pods, time-balanced, NOT LAUNCHED)

Assignment only -- no runner scripts written, no tmux sessions, no QE processes
started. This is a plan to review before launch.

## Timing model (empirical, from every real QE run on record: 16 data points
across round3 pod01+pod02 and round4)

| Phase | No-rattle (n, mean s) | Rattle (n, mean s) |
|---|---|---|
| AlNi | n=2, 173s | n=2, 476s |
| Al3Ni | n=1, 623s | **estimated** 1480s (no direct observation -- extrapolated via mean rattle/no-rattle ratio 2.38x observed across the other 4 phases) |
| Al3Ni2 | n=2, 244s | n=1, 550s |
| Al3Ni5 | n=2, 506s | n=1, 795s |
| AlNi3 | n=2, 537s | n=3, 1574s |

## Method

LPT (Longest Processing Time first) greedy bin-packing: candidates sorted by
estimated time descending, each assigned to the currently lightest-loaded pod.
This minimizes makespan (the slowest pod's finish time), not just structure count
per pod -- the actual goal when the aim is "every pod finishes around the same
time," given the >10x spread between the fastest (AlNi no-rattle, ~2 min) and
slowest (AlNi3 rattle, ~26 min) candidate categories.

## Per-pod load

| Pod | Structures | Total est. time | vs mean |
|---|---|---|---|
| 1 | 8 | 74.0 min | +0.3% |
| 2 | 8 | 74.0 min | +0.3% |
| 3 | 8 | 74.0 min | +0.3% |
| 4 | 8 | 72.8 min | -1.3% |
| 5 | 7 | 72.4 min | -1.8% |
| 6 | 8 | 72.6 min | -1.5% |
| 7 | 8 | 75.1 min | +1.9% |
| 8 | 9 | 72.8 min | -1.2% |
| 9 | 9 | 74.8 min | +1.4% |
| 10 | 9 | 74.8 min | +1.4% |

Mean pod load: 73.7 min. Max/min spread: 2.7 min (3.7% above the lightest pod).
Total estimated sequential compute (all 82, one pod): 12.3 hours.
Estimated wall-clock with 10 pods running in parallel: ~75.1 minutes (the slowest pod), assuming genuinely independent, uncontended GPUs per pod -- see caveat below.

## Per-pod membership

### Pod 1 (8 structures, 74.0 min estimated)

- `cfg266_AlNi3_shear_rattle_xz_positive` (AlNi3, shear_rattle, rattle, ~26.2 min)
- `cfg181_Al3Ni_orthorhombic_xy_compression` (Al3Ni, orthorhombic, no-rattle, ~10.4 min)
- `cfg248_AlNi3_uniaxial_x_compression` (AlNi3, uniaxial, no-rattle, ~8.9 min)
- `cfg258_AlNi3_orthorhombic_xy_compression` (AlNi3, orthorhombic, no-rattle, ~8.9 min)
- `cfg230_Al3Ni5_biaxial_yz_compression` (Al3Ni5, biaxial, no-rattle, ~8.4 min)
- `cfg201_Al3Ni2_biaxial_xz_expansion` (Al3Ni2, biaxial, no-rattle, ~4.1 min)
- `cfg207_Al3Ni2_orthorhombic_xz_compression` (Al3Ni2, orthorhombic, no-rattle, ~4.1 min)
- `cfg155_AlNi_biaxial_yz_compression` (AlNi, biaxial, no-rattle, ~2.9 min)

### Pod 2 (8 structures, 74.0 min estimated)

- `cfg269_AlNi3_shear_rattle_yz_positive` (AlNi3, shear_rattle, rattle, ~26.2 min)
- `cfg182_Al3Ni_orthorhombic_xz_expansion` (Al3Ni, orthorhombic, no-rattle, ~10.4 min)
- `cfg249_AlNi3_uniaxial_y_expansion` (AlNi3, uniaxial, no-rattle, ~8.9 min)
- `cfg259_AlNi3_orthorhombic_xz_compression` (AlNi3, orthorhombic, no-rattle, ~8.9 min)
- `cfg231_Al3Ni5_orthorhombic_xy_expansion` (Al3Ni5, orthorhombic, no-rattle, ~8.4 min)
- `cfg202_Al3Ni2_biaxial_xz_compression` (Al3Ni2, biaxial, no-rattle, ~4.1 min)
- `cfg208_Al3Ni2_orthorhombic_yz_expansion` (Al3Ni2, orthorhombic, no-rattle, ~4.1 min)
- `cfg156_AlNi_orthorhombic_xy_expansion` (AlNi, orthorhombic, no-rattle, ~2.9 min)

### Pod 3 (8 structures, 74.0 min estimated)

- `cfg271_AlNi3_shear_rattle_yz_negative` (AlNi3, shear_rattle, rattle, ~26.2 min)
- `cfg183_Al3Ni_orthorhombic_xz_compression` (Al3Ni, orthorhombic, no-rattle, ~10.4 min)
- `cfg250_AlNi3_uniaxial_z_expansion` (AlNi3, uniaxial, no-rattle, ~8.9 min)
- `cfg260_AlNi3_orthorhombic_yz_expansion` (AlNi3, orthorhombic, no-rattle, ~8.9 min)
- `cfg232_Al3Ni5_orthorhombic_xy_compression` (Al3Ni5, orthorhombic, no-rattle, ~8.4 min)
- `cfg203_Al3Ni2_biaxial_yz_expansion` (Al3Ni2, biaxial, no-rattle, ~4.1 min)
- `cfg209_Al3Ni2_orthorhombic_yz_compression` (Al3Ni2, orthorhombic, no-rattle, ~4.1 min)
- `cfg157_AlNi_orthorhombic_xy_compression` (AlNi, orthorhombic, no-rattle, ~2.9 min)

### Pod 4 (8 structures, 72.8 min estimated)

- `cfg272_AlNi3_volume_rattle_expansion` (AlNi3, volume_rattle, rattle, ~26.2 min)
- `cfg184_Al3Ni_orthorhombic_yz_expansion` (Al3Ni, orthorhombic, no-rattle, ~10.4 min)
- `cfg251_AlNi3_uniaxial_z_compression` (AlNi3, uniaxial, no-rattle, ~8.9 min)
- `cfg261_AlNi3_orthorhombic_yz_compression` (AlNi3, orthorhombic, no-rattle, ~8.9 min)
- `cfg233_Al3Ni5_orthorhombic_xz_expansion` (Al3Ni5, orthorhombic, no-rattle, ~8.4 min)
- `cfg204_Al3Ni2_biaxial_yz_compression` (Al3Ni2, biaxial, no-rattle, ~4.1 min)
- `cfg146_AlNi_uniaxial_x_compression` (AlNi, uniaxial, no-rattle, ~2.9 min)
- `cfg153_AlNi_biaxial_xz_expansion` (AlNi, biaxial, no-rattle, ~2.9 min)

### Pod 5 (7 structures, 72.4 min estimated)

- `cfg189_Al3Ni_shear_rattle_xz_positive` (Al3Ni, shear_rattle, rattle, ~24.7 min)
- `cfg178_Al3Ni_biaxial_xz_compression` (Al3Ni, biaxial, no-rattle, ~10.4 min)
- `cfg219_Al3Ni2_shear_rattle_yz_negative` (Al3Ni2, shear_rattle, rattle, ~9.2 min)
- `cfg255_AlNi3_biaxial_xz_compression` (AlNi3, biaxial, no-rattle, ~8.9 min)
- `cfg227_Al3Ni5_biaxial_xy_compression` (Al3Ni5, biaxial, no-rattle, ~8.4 min)
- `cfg170_AlNi_volume_rattle_expansion` (AlNi, volume_rattle, rattle, ~7.9 min)
- `cfg150_AlNi_uniaxial_z_compression` (AlNi, uniaxial, no-rattle, ~2.9 min)

### Pod 6 (8 structures, 72.6 min estimated)

- `cfg191_Al3Ni_shear_rattle_xz_negative` (Al3Ni, shear_rattle, rattle, ~24.7 min)
- `cfg179_Al3Ni_biaxial_yz_expansion` (Al3Ni, biaxial, no-rattle, ~10.4 min)
- `cfg220_Al3Ni2_volume_rattle_expansion` (Al3Ni2, volume_rattle, rattle, ~9.2 min)
- `cfg256_AlNi3_biaxial_yz_compression` (AlNi3, biaxial, no-rattle, ~8.9 min)
- `cfg228_Al3Ni5_biaxial_xz_expansion` (Al3Ni5, biaxial, no-rattle, ~8.4 min)
- `cfg195_Al3Ni2_uniaxial_x_expansion` (Al3Ni2, uniaxial, no-rattle, ~4.1 min)
- `cfg205_Al3Ni2_orthorhombic_xy_compression` (Al3Ni2, orthorhombic, no-rattle, ~4.1 min)
- `cfg152_AlNi_biaxial_xy_compression` (AlNi, biaxial, no-rattle, ~2.9 min)

### Pod 7 (8 structures, 75.1 min estimated)

- `cfg194_Al3Ni_shear_rattle_yz_negative` (Al3Ni, shear_rattle, rattle, ~24.7 min)
- `cfg180_Al3Ni_biaxial_yz_compression` (Al3Ni, biaxial, no-rattle, ~10.4 min)
- `cfg247_AlNi3_uniaxial_x_expansion` (AlNi3, uniaxial, no-rattle, ~8.9 min)
- `cfg254_AlNi3_biaxial_xz_expansion` (AlNi3, biaxial, no-rattle, ~8.9 min)
- `cfg224_Al3Ni5_uniaxial_z_expansion` (Al3Ni5, uniaxial, no-rattle, ~8.4 min)
- `cfg166_AlNi_shear_rattle_xz_negative` (AlNi, shear_rattle, rattle, ~7.9 min)
- `cfg149_AlNi_uniaxial_z_expansion` (AlNi, uniaxial, no-rattle, ~2.9 min)
- `cfg160_AlNi_orthorhombic_yz_compression` (AlNi, orthorhombic, no-rattle, ~2.9 min)

### Pod 8 (9 structures, 72.8 min estimated)

- `cfg241_Al3Ni5_shear_rattle_xz_negative` (Al3Ni5, shear_rattle, rattle, ~13.2 min)
- `cfg172_Al3Ni_uniaxial_x_expansion` (Al3Ni, uniaxial, no-rattle, ~10.4 min)
- `cfg175_Al3Ni_uniaxial_z_compression` (Al3Ni, uniaxial, no-rattle, ~10.4 min)
- `cfg185_Al3Ni_orthorhombic_yz_compression` (Al3Ni, orthorhombic, no-rattle, ~10.4 min)
- `cfg257_AlNi3_orthorhombic_xy_expansion` (AlNi3, orthorhombic, no-rattle, ~8.9 min)
- `cfg229_Al3Ni5_biaxial_yz_expansion` (Al3Ni5, biaxial, no-rattle, ~8.4 min)
- `cfg198_Al3Ni2_uniaxial_y_compression` (Al3Ni2, uniaxial, no-rattle, ~4.1 min)
- `cfg206_Al3Ni2_orthorhombic_xz_expansion` (Al3Ni2, orthorhombic, no-rattle, ~4.1 min)
- `cfg154_AlNi_biaxial_yz_expansion` (AlNi, biaxial, no-rattle, ~2.9 min)

### Pod 9 (9 structures, 74.8 min estimated)

- `cfg244_Al3Ni5_shear_rattle_yz_negative` (Al3Ni5, shear_rattle, rattle, ~13.2 min)
- `cfg173_Al3Ni_uniaxial_y_compression` (Al3Ni, uniaxial, no-rattle, ~10.4 min)
- `cfg176_Al3Ni_biaxial_xy_compression` (Al3Ni, biaxial, no-rattle, ~10.4 min)
- `cfg214_Al3Ni2_shear_rattle_xz_positive` (Al3Ni2, shear_rattle, rattle, ~9.2 min)
- `cfg252_AlNi3_biaxial_xy_expansion` (AlNi3, biaxial, no-rattle, ~8.9 min)
- `cfg222_Al3Ni5_uniaxial_x_compression` (Al3Ni5, uniaxial, no-rattle, ~8.4 min)
- `cfg234_Al3Ni5_orthorhombic_xz_compression` (Al3Ni5, orthorhombic, no-rattle, ~8.4 min)
- `cfg147_AlNi_uniaxial_y_expansion` (AlNi, uniaxial, no-rattle, ~2.9 min)
- `cfg158_AlNi_orthorhombic_xz_expansion` (AlNi, orthorhombic, no-rattle, ~2.9 min)

### Pod 10 (9 structures, 74.8 min estimated)

- `cfg245_Al3Ni5_volume_rattle_expansion` (Al3Ni5, volume_rattle, rattle, ~13.2 min)
- `cfg174_Al3Ni_uniaxial_z_expansion` (Al3Ni, uniaxial, no-rattle, ~10.4 min)
- `cfg177_Al3Ni_biaxial_xz_expansion` (Al3Ni, biaxial, no-rattle, ~10.4 min)
- `cfg216_Al3Ni2_shear_rattle_xz_negative` (Al3Ni2, shear_rattle, rattle, ~9.2 min)
- `cfg253_AlNi3_biaxial_xy_compression` (AlNi3, biaxial, no-rattle, ~8.9 min)
- `cfg223_Al3Ni5_uniaxial_y_expansion` (Al3Ni5, uniaxial, no-rattle, ~8.4 min)
- `cfg235_Al3Ni5_orthorhombic_yz_compression` (Al3Ni5, orthorhombic, no-rattle, ~8.4 min)
- `cfg148_AlNi_uniaxial_y_compression` (AlNi, uniaxial, no-rattle, ~2.9 min)
- `cfg159_AlNi_orthorhombic_xz_compression` (AlNi, orthorhombic, no-rattle, ~2.9 min)

## Integrity checks (all passed, or this script would have raised)

- Exactly 82 unique config_ids assigned, matching round300_manifest.csv exactly
- No config_id assigned to more than one pod
- Pod membership union equals the full 82-candidate manifest exactly

## Caveats -- read before launching

1. **Al3Ni rattle timing is an estimate**, not an observation (no round3/round4 config
   exercised this combination). This batch contains 3 Al3Ni-rattle
   candidates (pods 5, 6, 7 -- cfg189, cfg191, cfg194), each estimated at ~24.7 min via
   the cross-phase ratio extrapolation above. Their pods' actual time may deviate more
   than the others from this plan; this is the single largest source of estimate risk.
2. **This project's GPU/driver has changed identity between sessions before**
   (`project_knowledge.md` Section 6: 2.3-3.1x wall-clock variance observed between the
   combined-113 and combined-127/129 training runs on different physical GPUs). If DFT
   for this batch runs on a different GPU/driver than the ones behind this timing model,
   absolute times will shift -- the RELATIVE balance across pods should still roughly
   hold since all pods would be affected proportionally, but the makespan estimate above
   should not be treated as a tight bound.
3. This plan assumes 10 genuinely independent, uncontended GPUs/pods running in true
   parallel, matching the `ROUND3_POD_ASSIGNMENT.csv` convention. Round3 only actually
   used 2 of the 10 available pod slots -- confirm real pod availability before assuming
   the ~26-minute parallel estimate above is achievable.

Assignment CSV: `/workspace/ni_al/configs/ROUND300_POD_ASSIGNMENT.csv`
