# Round-285: Al3Ni High-Expansion Densification + New Sealed Confirmation Pair (design-only, NO DFT run)

Generated UTC: 2026-08-18T12:01:46.891278+00:00

## Background
combined-220 Al3Ni iso_expansion/volume_rattle_expansion TRAIN rungs: s=1.0% (cfg027, iso only), s=2.0% (cfg103+cfg105, matched pair), s=3.0% (cfg029, iso only, no volume_rattle partner), s=4.6% (cfg111+cfg112, matched pair), s=5.6% (cfg113+cfg114, matched pair, at the edge). Only 3 TRAIN rungs sit inside +2%..+5.6%; the 3.0%->4.6% span had zero iso/volume_rattle coverage -- exactly where cfg109/cfg110 (s=4.0%) sat before being consumed by unsealing (2026-08-17, AL3NI_FINAL_UNSEALING_RESULT.txt).

## Policy change applied this round
Gate (b) no longer treats cfg109/cfg110 as a protected holdout -- they are consumed. Candidates may sit directly adjacent to s=4.0%. Gate (b) instead uses the Al3Ni RESERVED population still live in combined-220 (cfg041, cfg042, cfg043, cfg044, Al3Ni_shear015_rattle002), same substitution design_round220_close_last2.py already used. Gates (a) and (c) re-derived fresh against combined-220's own Al3Ni population, per policy (never reused verbatim across rounds).

gate(a) threshold (5th percentile Al3Ni TRAIN-TRAIN combined distance, combined-220, ADVISORY ONLY for same-role TRAIN-vs-TRAIN per EXPANSION_BATCH_DESIGN_POLICY.md gate(c)): 0.7628
gate(b) threshold (min Al3Ni TRAIN<->RESERVED combined distance, cfg109/cfg110 excluded): 0.3269
gate(c) duplicate epsilon (combined distance, calibrated: true duplicate ~1e-7, closest legitimate different-strain neighbor ~0.097, closest legitimate matched-strain-family pair ~0.28): 1.0e-03

## Densification grid: s in {3.0, 3.5, 4.0, 4.5, 5.0}%, iso_expansion + volume_rattle_expansion (rattle_sigma=0.015 A, project-standard for this family)

| config_id | family | s (%) | min dist TRAIN | nearest TRAIN | thr(a) advisory | min dist RESERVED | nearest RESERVED | thr(b) | min dist ANY | nearest ANY | gate(a) | gate(b) | gate(c) | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cfg285_Al3Ni_iso_expansion | iso_expansion | 3.00 | 0.0000 | cfg029_Al3Ni_iso_expansion | 0.7628 | 0.5135 | cfg043_Al3Ni_volume_rattle_expansion | 0.3269 | 0.000000 | cfg029_Al3Ni_iso_expansion | ADVISORY(below_thr) | PASS | FAIL_DUPLICATE(of cfg029_Al3Ni_iso_expansion) | **REJECTED** |
| cfg286_Al3Ni_iso_expansion | iso_expansion | 3.50 | 0.4813 | cfg029_Al3Ni_iso_expansion | 0.7628 | 0.3222 | cfg043_Al3Ni_volume_rattle_expansion | 0.3269 | 0.322191 | cfg043_Al3Ni_volume_rattle_expansion | ADVISORY(below_thr) | FAIL_LEAKAGE | PASS | **REJECTED** |
| cfg287_Al3Ni_iso_expansion | iso_expansion | 4.00 | 0.5817 | cfg112_Al3Ni_volume_rattle_expansion | 0.7628 | 0.6399 | cfg043_Al3Ni_volume_rattle_expansion | 0.3269 | 0.581713 | cfg112_Al3Ni_volume_rattle_expansion | ADVISORY(below_thr) | PASS | PASS | **KEPT** |
| cfg288_Al3Ni_iso_expansion | iso_expansion | 4.50 | 0.0975 | cfg111_Al3Ni_iso_expansion | 0.7628 | 1.0896 | cfg043_Al3Ni_volume_rattle_expansion | 0.3269 | 0.097456 | cfg111_Al3Ni_iso_expansion | ADVISORY(below_thr) | PASS | PASS | **KEPT** |
| cfg289_Al3Ni_iso_expansion | iso_expansion | 5.00 | 0.3907 | cfg111_Al3Ni_iso_expansion | 0.7628 | 1.5633 | cfg043_Al3Ni_volume_rattle_expansion | 0.3269 | 0.294032 | cfg115_Al3Ni_iso_expansion | ADVISORY(below_thr) | PASS | PASS | **KEPT** |
| cfg290_Al3Ni_volume_rattle_expansion | volume_rattle_expansion | 3.00 | 0.3082 | cfg029_Al3Ni_iso_expansion | 0.7628 | 0.5031 | cfg043_Al3Ni_volume_rattle_expansion | 0.3269 | 0.308179 | cfg029_Al3Ni_iso_expansion | ADVISORY(below_thr) | PASS | PASS | **KEPT** |
| cfg291_Al3Ni_volume_rattle_expansion | volume_rattle_expansion | 3.50 | 0.4990 | cfg029_Al3Ni_iso_expansion | 0.7628 | 0.1880 | cfg043_Al3Ni_volume_rattle_expansion | 0.3269 | 0.188012 | cfg043_Al3Ni_volume_rattle_expansion | ADVISORY(below_thr) | FAIL_LEAKAGE | PASS | **REJECTED** |
| cfg292_Al3Ni_volume_rattle_expansion | volume_rattle_expansion | 4.00 | 0.6296 | cfg112_Al3Ni_volume_rattle_expansion | 0.7628 | 0.5365 | cfg043_Al3Ni_volume_rattle_expansion | 0.3269 | 0.276331 | cfg287_Al3Ni_iso_expansion | ADVISORY(below_thr) | PASS | PASS | **KEPT** |
| cfg293_Al3Ni_volume_rattle_expansion | volume_rattle_expansion | 4.50 | 0.2197 | cfg112_Al3Ni_volume_rattle_expansion | 0.7628 | 1.0095 | cfg043_Al3Ni_volume_rattle_expansion | 0.3269 | 0.219738 | cfg112_Al3Ni_volume_rattle_expansion | ADVISORY(below_thr) | PASS | PASS | **KEPT** |
| cfg294_Al3Ni_volume_rattle_expansion | volume_rattle_expansion | 5.00 | 0.4118 | cfg112_Al3Ni_volume_rattle_expansion | 0.7628 | 1.4871 | cfg043_Al3Ni_volume_rattle_expansion | 0.3269 | 0.269092 | cfg289_Al3Ni_iso_expansion | ADVISORY(below_thr) | PASS | PASS | **KEPT** |

DENSIFICATION KEPT: 7/10

## New sealed confirmation pair (proposed, replaces consumed cfg109/cfg110)

Strain values deliberately OFF the densification grid (3.75%, 4.25%) so each tests genuine interpolation inside the newly densified region rather than sitting on a trained rung. One iso_expansion, one volume_rattle_expansion -- same family split as cfg109/cfg110. Geometry and QE input written; DFT NOT run; energy/forces/stress do not exist for these structures yet. Sealing takes effect the moment this design is accepted: no future script may read their DFT labels except at a single, later, explicitly designated unsealing event, enforced the same way AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt enforced cfg109/cfg110.

| config_id | family | s (%) | min dist TRAIN | nearest TRAIN | thr(a) advisory | min dist RESERVED | nearest RESERVED | thr(b) | min dist ANY | nearest ANY | gate(a) | gate(b) | gate(c) | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cfg295_Al3Ni_iso_expansion | iso_expansion | 3.75 | 0.7229 | cfg029_Al3Ni_iso_expansion | 0.7628 | 0.4450 | cfg043_Al3Ni_volume_rattle_expansion | 0.3269 | 0.242091 | cfg287_Al3Ni_iso_expansion | ADVISORY(below_thr) | PASS | PASS | **KEPT** |
| cfg296_Al3Ni_volume_rattle_expansion | volume_rattle_expansion | 4.25 | 0.3904 | cfg112_Al3Ni_volume_rattle_expansion | 0.7628 | 0.7790 | cfg043_Al3Ni_volume_rattle_expansion | 0.3269 | 0.309601 | cfg292_Al3Ni_volume_rattle_expansion | ADVISORY(below_thr) | PASS | PASS | **KEPT** |

SEALED PAIR KEPT: 2/2

## Not done in this pass
DFT has not been run for any candidate (densification or sealed). No merge into any TRAIN/VALIDATION split. No retraining. cfg109/cfg110 were not read, referenced, or reintroduced to any split.

## Addendum (2026-08-18, appended before DFT launch): cfg043's exact strain

The gate computations in this file always used cfg043's real, precise
descriptor-derived strain (the actual gate(b) numbers above -- e.g.
cfg286's min_dist_reserved=0.322191 against threshold_b=0.3269 -- were
computed directly from cfg043's real DFT-relaxed cell geometry, not from
any rounded approximation). However, informal conversational commentary
in this design thread referred to cfg043 as sitting at "s~3.56%", which
was never a computed value -- just an unrefined eyeballed estimate from
trace(E)/3 rather than the correct closed-form inversion
s = sqrt(1+trace(E)/1.5) - 1.

Resolved precisely, two independent ways:
  1. Frozen manifest: data/datasets/ni_al_dataset100_blind_holdout_manifest.csv,
     cfg043 row, requested_strain=0.035.
  2. Geometry inversion of the actual relaxed DFT cell (trace(E)=0.106837):
     s = sqrt(1 + 0.106837/1.5) - 1 = 0.035000 exactly.

cfg043's true strain is **3.5000%**, not 3.56%. This does not change any
gate verdict above (they were already computed from the real geometry),
but under the corrected figure it is now on record that cfg286
(iso_expansion, s=3.50%) missed gate(b) by a margin of only 0.0047
(threshold 0.3269 vs measured 0.322191) -- essentially marginal, a
near-miss rather than a clear rejection. cfg291 (volume_rattle_expansion,
s=3.50%) missed by 0.1389 (0.3269 vs 0.188012) -- a real block, not
marginal. See configs/project_knowledge.md Section 5 for the full
cfg043-strain resolution and its role in the sealed-pair revision
(cfg298 retired as descriptor-degenerate with cfg043; replaced by
cfg299 at s=3.6%).
