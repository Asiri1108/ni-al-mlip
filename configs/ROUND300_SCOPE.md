# 300-Structure Round -- Scope (design-only, not generated/gated/DFT'd)

Single large batch targeting ALL remaining gaps at once, per explicit instruction --
not the round3/round4 pattern of small hand-picked batches. "All remaining gaps" =
every (phase, deformation-family, direction, sign[, rattle on/off]) combination with
zero TRAIN members: a strictly stronger, complete criterion than the coverage audit's
VALIDATION/HOLDOUT-outside-range flags, which it recovers as a special case.

## Sizing

Current project total (combined-129 non-sealed + 2 sealed cfg109/cfg110): **131**
Missing directional/isotropic-rattle combo slots (full factorial completion): **124**
Pure-rattle depth-equalization (bring every phase to Al3Ni's own depth of 3): **4**
Total new candidates proposed: **128**
Projected total after this round: 131 + 128 = **259**

This lands at 259/300 (86%) — approximating the ~300
milestone, not forced to hit it exactly. Per this project's own stated policy
(`ROUND3_BATCH_DESIGN_STATUS.md`'s "never pad a design to hit a round number"), no
extra candidates were added purely to close the remaining ~40-structure gap to 300 --
the actual gate pass rate (see below) will also reduce this number further before DFT.

## Per-phase breakdown

| Phase | New candidates |
|---|---|
| AlNi | 26 |
| Al3Ni | 23 |
| Al3Ni2 | 27 |
| Al3Ni5 | 25 |
| AlNi3 | 27 |

## Per-family breakdown

| Family | New candidates |
|---|---|
| biaxial | 25 |
| orthorhombic | 25 |
| rattle | 4 |
| shear | 23 |
| shear_rattle | 24 |
| uniaxial | 23 |
| volume_rattle | 4 |

## Magnitude assignment methodology

For each missing slot, magnitude = median of that exact (strain_type, sign, rattle-state)
combination's magnitudes already used in OTHER phases (cross-phase reference, same
principle as round4's 1.5x-probe rule: reuse data already on file, never invent a
number). Falls back to the mirrored opposite-sign magnitude, then to any-sign/any-
rattle-state median for that strain_type, if no direct reference exists. Fallback used for
**55/128** candidates (43%) -- flagged in the
roster's `magnitude_source` column, not silently applied.

**Notable finding surfaced by this scoping pass, not previously diagnosed explicitly:**
`isotropic pos + rattle=True` (i.e. volume_rattle EXPANSION) is a missing TRAIN slot in
**4 of 5 phases (AlNi, Al3Ni2, Al3Ni5, AlNi3)** -- Al3Ni is the only phase with
volume_rattle expansion TRAIN coverage (via round2's ladder extension); every other phase
has only ever been trained on volume_rattle COMPRESSION. This directly explains the
large-margin EXTRAPOLATION flags on cfg075 (Al3Ni2, margin 0.060) and cfg060 (Al3Ni5,
margin 0.060) in the coverage audit -- the single largest still-open margins of any flag.
No magnitude reference exists for this combo in any of those 4 phases, so
each uses the cross-phase-median fallback (from Al3Ni's own expansion value) and deserves
particular scrutiny once gates (a)-(d) actually run.

## What this does NOT do

- Does not construct Atoms objects, generate QE inputs, or run gates (a)-(d). The roster
  above is a target list, not frozen candidates -- round3/round4 both showed roughly
  half of proposed candidates fail gate (a) redundancy in practice, so expect the
  post-gate survivor count to be meaningfully below 128, not equal to it.
- Does not run any DFT.
- Does not touch cfg109/cfg110 (sealed) at all -- not even for geometry comparison,
  since this scoping pass never needed to.
- Does not decide VALIDATION/TEST/BLIND_HOLDOUT role assignment for any new structure --
  every candidate here is scoped as TRAIN, matching every round since v1. Whether the
  300-round should also deepen VALIDATION/TEST/BLIND_HOLDOUT is an open question this
  scope deliberately leaves for explicit confirmation, not a default assumption.

## Resource estimate for actually executing this (next step, needs confirmation)

Generation + gate-checking 128 candidates is a much larger version of round4's
2-candidate pass -- mechanically the same code, no new risk category, but ~35-70x the
volume. Assuming a similar ~50-85% gate survival rate to round3's, expect roughly
64-108 structures to actually reach DFT. At this project's
observed QE wall-clock range (~7-40 min/structure depending on phase/rattle, and
unpredictable given the GPU/driver variance documented in `project_knowledge.md` Section
6), sequential DFT alone could plausibly run **7-72 hours**
even before accounting for any failures/reruns. Splitting across multiple pods (the
`ROUND3_POD_ASSIGNMENT.csv`-style convention already established) would cut wall time
roughly linearly with pod count. This is a materially larger compute commitment than
any prior round in this project and should be explicitly confirmed before launching
generation+gating, let alone DFT.

Roster: `/workspace/ni_al/data/al3ni_remediation_v1/round300_scope_roster.csv`
