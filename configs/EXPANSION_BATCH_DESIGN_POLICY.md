# Expansion Batch Design Policy

Written this session as a **required** step for every future
structure-generation batch on this project — the 300-structure round, the
500-structure round, and any other future expansion. It generalizes the
gate process developed and repeatedly fixed during the Al3Ni
expansion-branch remediation (see
`configs/SESSION_STATE_AL3NI_EXPANSION_DESIGN.md`, Sections 3-8) into a
standing policy so the same mistakes are not re-made in a different phase
or composition.

**Read this before designing any new batch of TRAIN/VALIDATION/HOLDOUT
structures.**

## Why this exists

Five consecutive design rounds in the Al3Ni expansion-branch session failed
or were retracted, all from the same underlying category of error: a
threshold was either invented outright, or was correctly derived but then
applied outside the regime it was derived for. In order:

1. The "2x redundancy" leakage threshold (`2 x 0.794907 = 1.5898`) —
   invented, no basis in the frozen split's own data.
2. The "2x benchmark" bracket-quality flag — also invented.
3. Gate (c) applying the redundancy threshold uniformly to matched-strain
   rattle pairs — the descriptor cannot resolve rattle-only differences
   (`d_vol = 0`, `d_strain = 0` exactly for a matched-strain pair), so the
   redundancy threshold was being applied in a regime where it is
   meaningless.
4. Gate (c) applying the redundancy threshold (a **duplication** test) to
   TRAIN-vs-VALIDATION proximity, where the actual requirement is the
   opposite — VALIDATION should be **close to** TRAIN, not far from it.
   This pushed a VALIDATION point (cfg115) past the TRAIN ceiling into
   extrapolation territory to force a spurious pass.
5. (Same root cause as #4, confirmed and fixed by deriving a
   direction-correct gate instead of reusing the duplication threshold.)

The fix each time was the same: stop reusing a number, and instead derive
the correct number from the data actually available, in the regime it will
actually be applied to. This policy makes that the required procedure, not
something to rediscover per round.

## Required gate process for every new batch

Every future structure-generation batch must pass all four gates below
before being frozen for DFT submission. All thresholds must be **re-derived
from the data available at design time** — never reused verbatim from a
prior phase or composition, and never invented as a round number.

### Gate (a) — Redundancy (vs existing TRAIN)

- Compare each new candidate against **all existing TRAIN members of the
  same phase/composition** (not other phases — a threshold derived from
  Al3Ni diversity does not apply to Al3Ni2 or Al3Ni5 candidates).
- Threshold = the **5th percentile of the intra-phase pairwise descriptor
  distance** among all existing frozen members of that phase/composition
  (TRAIN + VALIDATION + HOLDOUT together, as in the original 19-member
  Dataset-100 Al3Ni population — see
  `SESSION_STATE_AL3NI_EXPANSION_DESIGN.md` Section 3).
- **Recompute this percentile for every new phase/composition and every
  new round** — do not reuse the Al3Ni value (0.794907) for Al3Ni2, Al3Ni5,
  or any later Al3Ni round without recomputing it against that round's own
  population.
- Reject candidates below threshold (too similar to something already in
  TRAIN).

### Gate (b) — Leakage (vs sealed holdouts)

- Compare each new candidate against **every currently sealed confirmation
  point** — currently `{cfg043, cfg109, cfg110}`, and any future sealed
  confirmation points added in later rounds (e.g. 300- or
  500-structure-round confirmation holdouts, once designated).
- Threshold = the **minimum pairwise descriptor distance already accepted
  between the frozen TRAIN set and the frozen HOLDOUT set** for that
  phase/composition (the tightest separation the existing split already
  lives with) — same derivation method as the current Al3Ni value
  (0.734644), but **recompute it, do not reuse 0.734644 verbatim**, if the
  phase, composition, or descriptor definition changes.
- Reject candidates below threshold (too close to a sealed point — leakage
  risk).
- Only geometry (cell, positions) may be read from sealed points to compute
  this. Energy, forces, and stress from any sealed point must never be
  read while the gate is being evaluated.

### Gate (c) — Role-based (matched-strain family pairs)

- A matched-strain family pair (e.g. `iso_expansion` vs
  `volume_rattle_expansion` at the same strain value) **must share role**
  — never split across TRAIN and VALIDATION (or TRAIN and HOLDOUT, etc).
  The descriptor cannot certify independence for such a pair (it collapses
  to a rattle-only shape perturbation against a scale calibrated for much
  larger strain-driven differences), so any split across roles is
  unverifiable by construction.
- The gate (a) redundancy threshold applies **only** to pairs with
  different roles **and** different strain values — the regime where the
  descriptor is actually valid. Same-role or same-strain pairs are exempt
  from gate (a) and handled by this gate instead.
- TRAIN-vs-TRAIN similarity at different strain values is an **efficiency
  advisory only** — informative, never a rejection reason.

### Gate (d) — TRAIN-vs-VALIDATION placement

- A VALIDATION candidate must be evaluated against its **nearest** TRAIN
  point on its own branch (farther TRAIN points are advisory only, same
  treatment as gate (c)'s advisory rule).
- **Ceiling**: reject if the nearest-TRAIN distance is farther than the
  loosest nearest-TRAIN distance the frozen split has already accepted for
  a VALIDATION point in that phase/composition (derived the same way as
  gate (b)'s leakage threshold, but in the opposite direction — this
  guards against **extrapolation**, not duplication).
- **Floor**: reject if the nearest-TRAIN distance is closer than the
  matched-strain degeneracy scale for that phase (the distance below which
  the descriptor cannot certify the candidate as a distinct point — see
  gate (c)).
- **Do not use the gate (a) redundancy/duplication threshold for this
  gate.** VALIDATION wants to be in-distribution (close to TRAIN); gate
  (a) exists to detect duplication (too close is bad). Applying gate (a)'s
  threshold here was the error in design round 4/5 above.
- This gate is separate from and in addition to gate (b) — passing gate
  (d) does not exempt a candidate from gate (b), and vice versa.

## The one rule that matters more than any of the above

**Before applying any threshold to a new comparison, verify two things:**

1. The descriptor can actually resolve the difference being tested. If two
   candidates differ only in a way the descriptor's normalization can't
   see (e.g. rattle-only perturbation against a strain-calibrated scale),
   no threshold derived from that descriptor is meaningful for that
   comparison.
2. The regime the threshold was derived from matches the regime it is
   being applied to. A threshold derived from TRAIN-vs-HOLDOUT separation
   is not automatically valid for TRAIN-vs-VALIDATION separation, and a
   threshold derived from one phase/composition's population is not valid
   for another's. Re-derive it from the analogous data every time the
   regime changes — that includes every new round (300-structure,
   500-structure, ...) and every new phase/composition, not just the first
   time a gate is defined.

**Never reuse a threshold verbatim across a phase, composition, or round
boundary without re-deriving it. Never invent a round number when a gate
seems hard to satisfy — that is what produced every one of the five failed
rounds this policy exists to prevent.**
