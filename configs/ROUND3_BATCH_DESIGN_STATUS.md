# Round-3 Batch Design Status

Design-only. No DFT run. No training. cfg109/cfg110 untouched throughout
(design used geometry reads of other configs only; sealed labels never
accessed). This batch targets the priority gaps identified in
`results/full_coverage_audit_v1/priority_ranking.md`, in the agreed order:
Al3Ni2 biaxial + cfg098/cfg056 first, then Al3Ni/AlNi biaxial, then
shear_rattle/orthorhombic gaps.

## Scope note

This is **not** the full ~185-structure "reach 300" batch. It is the
right-sized set that closes the specific gaps already diagnosed, following
this project's established rule (`EXPANSION_BATCH_DESIGN_POLICY.md`): never
pad a design to hit a round number. 14 structures passed every gate; more
were tried and rejected rather than forced through (see below). Reaching
the full 300-structure milestone needs additional design work beyond these
flagged gaps — out of scope for this pass.

## Method

1. Reused the exact deformation/QE-generation logic from
   `scripts/generate_dataset100_expansion.py` (`deformation()` function,
   per-phase `PHASE_INFO` — k-grids, spin flags, compositions) rather than
   reinventing it, so new structures are generated identically to the
   historical ones they extend.
2. **Caught and corrected two stale-reference issues before generating
   anything**: (a) the historical QE inputs' `pseudo_dir` path
   (`/workspace/ni_al/pseudo`) no longer exists on disk — corrected to
   `tools/qe_pseudos`, matching every other DFT batch this session; (b)
   discovered AlNi3 uses spin-polarized DFT (`nspin=2,
   starting_magnetization(2)=0.60`) that none of the other 4 phases use —
   would have produced scientifically wrong AlNi3 inputs if missed.
3. For each gap, proposed a candidate at roughly half the existing
   VALIDATION/HOLDOUT probe's magnitude ("inner") and one beyond it
   ("outer"), same sign/axis as the probe.
4. Gates (a) redundancy and (b) leakage **re-derived fresh per phase**
   (AlNi, Al3Ni, Al3Ni2, Al3Ni5, AlNi3 each got their own 5th-percentile
   redundancy threshold and min-TRAIN-to-holdout leakage threshold from
   that phase's own population) — never reused Al3Ni's session-specific
   numbers (0.794907 / 0.734644 / 0.628835 / 0.297055), per policy.
5. Gate (c) (no exact/near-duplicate geometry, vs existing population and
   vs the other new candidates) checked for every candidate.

## Result: every "inner" candidate failed gate (a)

All 12 "inner" (half-magnitude) candidates failed the redundancy gate —
too close to that phase's relaxed reference (strain=0) or an existing
small-magnitude TRAIN member. This makes sense in hindsight: the relaxed
reference itself is a TRAIN-role member at zero deformation, so it already
serves as the natural inner anchor for these signed perturbation families.
Adding another point near it was redundant, not new information. **Dropped
all 12** rather than force them through — consistent with the point of
having a gate at all.

One "outer" candidate (cfg133, AlNi shear_rattle_yz_negative at
shear=-0.029) failed gate (b) — too close to the holdout point it was
meant to flank (`cfg088_AlNi_shear_rattle_yz_negative`, shear=-0.022,
same rattle sigma 0.015), consistent with Section 4's descriptor blind
spot for matched-rattle-sigma pairs. **Widened to shear=-0.045**, which
cleared both gates with margin (a: d=1.73 vs threshold 0.85; b: d=0.88 vs
threshold 0.65) — kept, not dropped.

## Final 14 configs (all gates PASS)

| config_id | phase | gap addressed | strain/shear | rattle | pod |
|---|---|---|---|---|---|
| cfg117_Al3Ni2_biaxial_xy_compression | Al3Ni2 | A1 (cfg073) | -0.027 | 0 | 1 |
| cfg118_AlNi3_volume_rattle_compression | AlNi3 | A2 (cfg098) | -0.020 | 0.02 | 2 |
| cfg119_AlNi3_volume_rattle_compression | AlNi3 | A2 (cfg098) | -0.035 | 0.02 | 3 |
| cfg121_Al3Ni5_uniaxial_x_expansion | Al3Ni5 | A3 (cfg056) | +0.024 | 0 | 4 |
| cfg123_Al3Ni_biaxial_xy_expansion | Al3Ni | B1 (cfg039) | +0.018 | 0 | 5 |
| cfg125_AlNi_biaxial_xz_compression | AlNi | B2 (cfg087) | -0.027 | 0 | 6 |
| cfg127_Al3Ni2_shear_rattle_yz_positive | Al3Ni2 | C1a (cfg072) | shear +0.027 | 0.025 | 7 |
| cfg129_Al3Ni5_shear_rattle_xz_positive | Al3Ni5 | C1b (cfg057) | shear +0.027 | 0.025 | 8 |
| cfg131_AlNi_shear_rattle_xz_positive | AlNi | C1c (cfg086) | shear +0.027 | 0.025 | 9 |
| cfg133_AlNi_shear_rattle_yz_negative | AlNi | C1c (cfg088) | shear -0.045 (revised) | 0.015 | 10 |
| cfg135_AlNi3_shear_rattle_xz_negative | AlNi3 | C1d (cfg100) | shear -0.029 | 0.025 | 1 |
| cfg137_Al3Ni2_orthorhombic_xy | Al3Ni2 | C2a (cfg071) | +0.024 | 0 | 2 |
| cfg139_AlNi_orthorhombic_yz | AlNi | C2b (cfg085) | +0.024 | 0 | 3 |
| cfg141_AlNi3_orthorhombic_xz | AlNi3 | C2c (cfg097) | +0.024 | 0 | 4 |

All 14: TRAIN role. Seeds follow the project convention
(20261000 + numeric config ID). Composition/atom-count/min-distance/
finite-value sanity checks all passed during generation.

## Per-phase gate thresholds (freshly derived, this round)

| Phase | n members | n TRAIN | redundancy (5th pct) | leakage (min TRAIN-holdout) |
|---|---|---|---|---|
| AlNi | 18 | 12 | 0.853179 | 0.645250 |
| Al3Ni2 | 19 | 12 | 0.913233 | 0.743985 |
| Al3Ni5 | 22 | 14 | 0.923534 | 0.657245 |
| AlNi3 | 17 | 11 | 0.780401 | 0.684678 |
| Al3Ni | 37 | 26 | 0.380625 | 0.380183 |

## Artifacts

- `configs/ROUND3_POD_ASSIGNMENT.csv` — config_id, pod_number, status
- `data/al3ni_remediation_v1/round3_structures/pod_01/` .. `pod_10/` —
  EXTXYZ + QE `.in` per config, disjoint by pod, no ID ever assigned to
  two pods
- `data/al3ni_remediation_v1/round3_manifest.csv` — full design record
  (strain/rattle/seed/gap-reference/paths/min-distance per config)

## Not done in this pass

DFT has not been run. No production directory execution. cfg109/cfg110
remain sealed. The remaining audit-flagged gaps not addressed here (Al3Ni5
and AlNi3 biaxial specifically, and any gap beyond the agreed priority
list) are still open — not silently dropped, just out of this pass's
explicit scope.
