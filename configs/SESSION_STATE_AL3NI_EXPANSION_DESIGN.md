# Al3Ni Expansion-Branch Redesign — Session State Checkpoint

Checkpoint written for zero-context-loss resume. Read this file fully before
taking any action in this workstream. It assumes no memory of the session
that produced it.

STATUS AT CHECKPOINT: DFT COMPLETE FOR cfg111-cfg115, VALIDATED, ASSEMBLED
INTO LABELED TRAIN/VALIDATION FILES (`data/datasets/ni_al_round2_*`). NOT
YET MERGED with Dataset-100/cfg101-108. No training run. No existing
dataset file modified. cfg109/cfg110 remain sealed. **cfg115 placement question (former
Section 7) is RESOLVED — full cfg111-cfg115 design passes all four gates.**
Unsealing trigger redefined (Section 11): tied to the FINAL model trained
on the full ~500-structure dataset, not this checkpoint — see
`configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`. See Section 12 for
the round-2 DFT execution/validation record.
Batch-design gate policy for all future rounds (300, 500, ...) written to
`configs/EXPANSION_BATCH_DESIGN_POLICY.md`. Next action is Section 10 item
4 (single-point SCF convergence check) — not yet started.

---

## 1. Current phase

Al3Ni expansion-branch redesign. **Design stage only.** No DFT has been run
for cfg111-cfg115. Nothing has been retrained. Nothing beyond this markdown
file has been written to disk for this workstream. (All computation this
session — reconstructing the Section 3 descriptor pipeline, generating
synthetic cfg111-115 structures to screen candidate placements — was done
in-memory / in a scratch dir outside the project tree; nothing was written
under `data/` or `configs/` other than this file.)

## 2. Why this phase exists

The cfg101-cfg108 remediation batch did **not** fix the cfg043 failure.

Root cause, established this session: cfg043 (+3.5% isotropic strain) and
cfg109/cfg110 (+4.0%) were **extrapolation points** — above the TRAIN
expansion ceiling of +3.0% (cfg029_Al3Ni_iso_expansion, Dataset-100 TRAIN).
The original diagnosis of "coverage gap" (sparse-but-present coverage) was
wrong; the correct diagnosis is extrapolation (no TRAIN support above the
ceiling at all on the expansion side).

cfg101-cfg108 added **no TRAIN point above +3.0% on the expansion side**.
cfg104_Al3Ni_volume_rattle_compression and cfg107_Al3Ni_volume_rattle_compression
did usefully reinforce the **compression** side (TRAIN + VALIDATION flanking
the previously-lone compression point cfg037) — that part of the remediation
batch is sound and is not in question.

## 3. Accepted thresholds and their provenance

- **Redundancy threshold = 0.794907** — the 5th percentile of the 171
  pairwise descriptor distances among all 19 Dataset-100 Al3Ni configs
  (intra-Dataset-100 population).
- **Leakage threshold = 0.734644** — the **minimum** of the 52 pairwise
  descriptor distances between every Dataset-100 Al3Ni TRAIN member (13:
  cfg026-cfg038) and every Dataset-100 Al3Ni HOLDOUT member (4: cfg041,
  cfg042, cfg043, cfg044). This is the tightest TRAIN/HOLDOUT separation the
  frozen split already accepted. **The minimum pair is cfg029 <-> cfg043
  itself** (rank 0 of 52, i.e. the 0th percentile).
- **RETRACTED — do not reintroduce:**
  - the "2x redundancy" leakage threshold (`2 x 0.794907 = 1.5898`) — an
    invented multiplier with no basis in the frozen split's own data.
  - the "2x benchmark" bracket-quality flag (bracket width > 2x the
    cfg029->cfg043 gap of 0.236 A^3/atom) — also an invented number.
- **TRAIN-vs-VALIDATION ceiling = 0.628835** — derived this session to
  resolve Section 7. Definition: for each of the 2 Dataset-100 Al3Ni
  VALIDATION members (cfg039_Al3Ni_biaxial_xy_expansion,
  cfg040_Al3Ni_rattle_medium), the descriptor distance to its **nearest**
  Dataset-100 TRAIN member (13: cfg026-038) was computed; the ceiling is the
  **maximum** of those two nearest-neighbor distances (cfg039 -> nearest
  cfg027, d=0.628835; cfg040 -> nearest cfg035, d=0.539467). This is the
  loosest TRAIN-to-nearest-VALIDATION proximity the frozen split already
  accepted as "in-distribution." Same derivation pattern as the leakage
  threshold (Section 3), but the failure mode is the opposite: leakage
  rejects pairs **closer** than anything the frozen split accepted;
  this ceiling rejects VALIDATION candidates whose nearest-TRAIN distance is
  **farther** than anything the frozen split accepted (i.e. extrapolation).
  Applies as a nearest-neighbor-only test (a VALIDATION point only needs to
  be near *one* TRAIN point to be in-distribution) — distances to farther
  TRAIN rungs are advisory only, same treatment as gate (c) rule 3.
- **TRAIN-vs-VALIDATION floor = 0.297055** — derived this session, same
  resolution. Definition: the minimum descriptor distance observed between
  a matched-strain iso_expansion/volume_rattle_expansion pair this session
  (cfg111<->cfg112, both +4.60%, d=0.2971; cfg113<->cfg114, both +5.60%,
  d=0.5280 — floor takes the smaller). Below this, the descriptor cannot
  distinguish the candidate from "the same point rendered twice" (Section
  4), so a VALIDATION candidate whose nearest-TRAIN distance falls below it
  is a duplication risk, not a legitimate close-but-independent point.
  Applied only to the same nearest-TRAIN pair the ceiling test uses.
  **Reproduction note:** both new thresholds were computed by
  reconstructing the Section 3 descriptor pipeline from scratch this
  session (no saved script existed on disk for it). The reconstruction was
  validated against the frozen Section 3 numbers before being trusted:
  recomputed leakage threshold = 0.734603 vs frozen 0.734644 (diff
  0.0056%), same minimum pair (cfg029<->cfg043) identified in both. Treated
  as a confirmed-fidelity reconstruction, not a re-derivation of Section 3's
  own frozen values (those remain 0.794907 / 0.734644 as recorded above).

Descriptor definition (unchanged since first use, `geometry_redundancy.csv`
methodology): per-config feature = {sorted 120-length minimum-image pairwise
distance vector (shape), volume/atom, Green-Lagrange strain tensor relative
to the Pilot-25 `Al3Ni_relaxed` reference cell}. Pairwise distance = Euclidean
combination of three sub-distances (shape RMSD, |delta vol/atom|, strain
Frobenius norm), each z-scored by its own population std computed over the
171 intra-Dataset-100-Al3Ni pairs.

## 4. Descriptor blind spot — important

The descriptor is normalized by a population std dominated by strain/volume
diversity. For a **matched-strain iso_expansion / volume_rattle_expansion
pair**, `d_vol = 0` and `d_strain = 0` **exactly** (same cell, same strain
tensor by construction) — the descriptor is measuring only the small
rattle-induced shape perturbation against a scale calibrated for much larger
strain-driven differences. **The descriptor cannot resolve rattle-only
differences.**

Consequence: the first-round REDUNDANT flags on cfg106_Al3Ni_rattle_020 and
cfg108_Al3Ni_rattle_030 were **measurement artifacts**, not real duplication:

| pair | d_shape | d_vol | d_strain | combined | threshold | status |
|---|---|---|---|---|---|---|
| cfg106 <-> cfg035_Al3Ni_rattle_small (DS100) | 0.0155 | 0.0000 | 0.0000 | 0.3608 | 0.794907 | ARTIFACT |
| cfg108 <-> cfg040_Al3Ni_rattle_medium (DS100) | 0.0222 | 0.0000 | 0.0000 | 0.5179 | 0.794907 | ARTIFACT |

Both are rattle-only perturbations of the same unstrained reference cell
(vol/atom = 14.7463 A^3/atom for all four configs involved).

**Not affected:** the cfg104_Al3Ni_volume_rattle_compression flag (d=0.774
vs cfg037_Al3Ni_volume_rattle_compression, DS100 TRAIN) — that pair has
*differing* strain values, so `d_vol` and `d_strain` are non-zero and the
descriptor is operating in its valid regime there. That flag stands.

## 5. Gate definitions as currently accepted

- **(a) Redundancy** — vs Dataset-100 TRAIN (13 Al3Ni configs, cfg026-038)
  union cfg101-cfg108. Threshold 0.794907. Reject below.
- **(b) Leakage** — vs {cfg043, cfg109, cfg110} (geometry only — cell and
  positions; energy/forces/stress never read from any of the three).
  Threshold 0.734644 (derived, Section 3). Reject below.
- **(c) Role-based (corrected version — supersedes the first, retracted
  "reject any pair" version)**:
  1. A matched-strain iso_expansion/volume_rattle_expansion pair **must
     share role** (never split across TRAIN and VALIDATION) — the
     descriptor cannot certify independence for such a pair (Section 4), so
     the split would be unverifiable by construction.
  2. The 0.794907 threshold applies **only** to pairs with **different
     roles AND different strain values** — the regime where the descriptor
     is valid.
  3. TRAIN-vs-TRAIN similarity (different strain) is reported as an
     **efficiency advisory only** — never rejected.
- **(d) TRAIN-vs-VALIDATION placement (new gate, added this session,
  resolves Section 7)** — applies only to a VALIDATION candidate against
  the TRAIN rungs on its own branch:
  1. Compute the candidate's descriptor distance to its **nearest** TRAIN
     rung only (farther rungs are advisory, per rule 3's pattern).
  2. **Reject if nearest-TRAIN distance > 0.628835** (ceiling, Section 3) —
     candidate is farther from TRAIN than the frozen split ever accepted
     for a VALIDATION point; this is the extrapolation failure mode that
     produced the Section 7 problem.
  3. **Reject if nearest-TRAIN distance < 0.297055** (floor, Section 3) —
     candidate is close enough that the descriptor cannot certify it is a
     distinct point (Section 4 degeneracy), i.e. a duplication risk.
  4. This gate is **separate from and in addition to** gate (b) leakage,
     which still applies unchanged against the sealed set.

## 6. Current proposed design (NOT approved for DFT)

Retained from the prior accepted round, unchanged:

| config_id | role | family | strain | rattle sigma (A) | seed | vol/atom (A^3) |
|---|---|---|---|---|---|---|
| cfg111_Al3Ni_iso_expansion | TRAIN | iso_expansion | +4.60% | 0 | — | 16.8763 |
| cfg112_Al3Ni_volume_rattle_expansion | TRAIN | volume_rattle_expansion | +4.60% | 0.015 | 20261112 | 16.8763 |

Newly proposed this round, **cfg115 RESOLVED this session (Section 7)**:

| config_id | role | family | strain | rattle sigma (A) | seed | vol/atom (A^3) |
|---|---|---|---|---|---|---|
| cfg113_Al3Ni_iso_expansion | TRAIN | iso_expansion | +5.60% | 0 | — | 17.3650 |
| cfg114_Al3Ni_volume_rattle_expansion | TRAIN | volume_rattle_expansion | +5.60% | 0.015 | 20261114 | 17.3650 |
| cfg115_Al3Ni_iso_expansion | VALIDATION | iso_expansion | +5.30% | 0 | — | 17.2174 |

cfg115 strain revised from +6.30% (extrapolation, retracted) to +5.30%
(interior — between cfg111/112 at +4.60% and cfg113/114 at +5.60%, strictly
below the TRAIN ceiling). See Section 7 for full derivation.

Reference: Al3Ni_relaxed vol/atom = 14.746286 A^3/atom (Pilot-25 canonical).
cfg029 (Dataset-100 TRAIN, lower bracket) = +3.0% / 16.1137 A^3/atom.
cfg043 (Dataset-100 HOLDOUT) = +3.5% / 16.3495 A^3/atom.
cfg109/cfg110 (sealed) = +4.0% / 16.5876 A^3/atom.

### Gate (a) / (b) results, cfg113-cfg115 (cfg115 recomputed at resolved +5.30%)

| config_id | d(a) vs DS100-TRAIN u cfg101-108 | gate(a) | d(b) vs {043,109,110} | gate(b) |
|---|---|---|---|---|
| cfg113 | 3.6073 | OK | 2.2302 | OK |
| cfg114 | 3.5534 | OK | 2.1992 | OK |
| cfg115 (+5.30%) | 3.1733 (nearest: cfg029) | OK | 1.8017 (min of three, below) | OK |

d(b) breakdown, cfg115 vs each sealed-set member individually (geometry
only; cfg109/cfg110 read from `data/al3ni_remediation_v1/structures/`,
which contains pre-DFT geometry with no energy/forces/stress fields —
verified before reading):

| vs | d_b | threshold | verdict |
|---|---|---|---|
| cfg043_Al3Ni_volume_rattle_expansion | 2.645089 | 0.734644 | OK |
| cfg109_Al3Ni_iso_expansion (sealed, geometry only) | 1.801734 | 0.734644 | OK |
| cfg110_Al3Ni_volume_rattle_expansion (sealed, geometry only) | 1.935518 | 0.734644 | OK |

Gate (b) verdict uses the minimum of the three (cfg109, d=1.8017) —
still >2x the threshold.

### Gate (c) full pairwise matrix, all five (cfg111-cfg115, cfg115 at resolved +5.30%)

| pair | roles | same strain? | distance | verdict |
|---|---|---|---|---|
| 111 <-> 112 | TRAIN/TRAIN | yes | 0.2971 | EXEMPT |
| 111 <-> 113 | TRAIN/TRAIN | no | 1.3977 | advisory |
| 111 <-> 114 | TRAIN/TRAIN | no | 1.4020 | advisory |
| 111 <-> 115 | TRAIN/VALIDATION | no | 0.9728 | advisory (not nearest TRAIN — gate d not evaluated on this pair) |
| 112 <-> 113 | TRAIN/TRAIN | no | 1.4782 | advisory |
| 112 <-> 114 | TRAIN/TRAIN | no | 1.4043 | advisory |
| 112 <-> 115 | TRAIN/VALIDATION | no | 1.0689 | advisory (not nearest TRAIN — gate d not evaluated on this pair) |
| 113 <-> 114 | TRAIN/TRAIN | yes | 0.5280 | EXEMPT |
| 113 <-> 115 | TRAIN/VALIDATION | no | 0.4188 | **gate (d): nearest TRAIN — OK** (floor 0.297055 < 0.4188 < ceiling 0.628835) |
| 114 <-> 115 | TRAIN/VALIDATION | no | 0.6133 | advisory (not nearest TRAIN) |

Gate (d) (Section 5) evaluates only the nearest-TRAIN pair per VALIDATION
candidate: cfg115's nearest TRAIN is cfg113 (d=0.4188), which clears both
the floor and the ceiling with comfortable margin (floor margin +0.122,
ceiling margin +0.210). Zero hard failures under gates (a), (b), (c), (d).
**All four gates formally PASS. cfg115 is RESOLVED — see Section 7.**

### TRAIN ladder, expansion branch (matched-strain pairs merged into one rung)

| vol/atom (A^3) | rung | gap from previous |
|---|---|---|
| 16.1137 | cfg029 | — |
| 16.8763 | cfg111 / cfg112 | 0.7626 |
| 17.3650 | cfg113 / cfg114 | 0.4887 |

Max consecutive TRAIN gap on the expansion branch: 0.7626 A^3/atom
(cfg029 -> cfg111/112; unchanged by this round's additions).

## 7. cfg115 placement — RESOLVED this session

**Original problem:** cfg115 (VALIDATION) was placed at +6.30%, **above**
the TRAIN ceiling of +5.60% (cfg113/114) — an extrapolation point relative
to TRAIN, which distorts early stopping and model selection.

**Why it ended up there (historical record):** placing VALIDATION *between*
cfg111/112 (+4.60%) and cfg113/114 (+5.60%) was tried first (+5.10%) and
failed gate (c) against three of the four surrounding TRAIN points
(distances 0.6972, 0.7005, 0.7919, all below 0.794907). VALIDATION was
moved past the ceiling (+6.30%) to force a pass, which resolved gate (c)
mechanically but produced the extrapolation problem.

**Root cause, confirmed:** gate (c) was applying the *redundancy* threshold
(0.794907, derived to detect **duplication** from Dataset-100-wide
strain/volume diversity) to a TRAIN-vs-VALIDATION proximity test, where the
desired property is the opposite — VALIDATION should be **close to** TRAIN
(in-distribution), not far from it. Same category of error as every prior
retracted round (Section 8): a threshold applied outside the regime it was
derived from.

**Fix applied:** a new gate (d) was derived this session (Section 3/5),
using the same "derive from the frozen split's own accepted extremes"
method as the leakage threshold, but in the direction that matches what
TRAIN-vs-VALIDATION proximity actually needs to guard against
(extrapolation, not duplication):
- **Ceiling = 0.628835** — the loosest nearest-TRAIN distance the frozen
  Dataset-100 split already accepted for a VALIDATION point (max over
  cfg039's and cfg040's nearest-TRAIN distances). Reject candidates farther
  than this from every TRAIN rung.
- **Floor = 0.297055** — the matched-strain degeneracy scale (min of the
  cfg111<->cfg112 and cfg113<->cfg114 exempt-pair distances, Section 4).
  Reject candidates closer than this to their nearest TRAIN rung (can't be
  certified as a distinct point).

**Resolution:** cfg115 redesigned at **+5.30%** isotropic expansion
(vol/atom 17.2174 A^3), strictly interior to the TRAIN ladder (between
cfg111/112 at +4.60% and cfg113/114 at +5.60%, i.e. **not** past the
ceiling). Nearest TRAIN rung is cfg113 (d=0.4188), which clears both the
new floor and ceiling with margin (+0.122 above floor, +0.210 below
ceiling). Gate (b) leakage vs {cfg043, cfg109, cfg110} individually =
2.6451 / 1.8017 / 1.9355 (min = cfg109, still >2x threshold), far clear of
0.734644. Gate
(a) redundancy vs nearest Dataset-100 TRAIN (cfg029) = 3.1733, far clear of
0.794907. All four gates — (a), (b), (c), (d) — PASS. See Section 6 for the
full updated tables.

A location satisfying both the ceiling and the floor **was** found; no
conflict to report.

## 8. Recurring failure pattern — read before proposing any threshold

Five design rounds this session failed or were retracted for the same
underlying reason: a threshold was applied outside the regime it was derived
from (the "2x redundancy" leakage multiplier; the "2x benchmark" bracket
rule; the original gate (c) applying the redundancy threshold uniformly to
matched-strain rattle pairs; the original gate (c) applying the redundancy
threshold — a duplication test — to TRAIN-vs-VALIDATION proximity, which
needed an extrapolation test instead; **confirmed and fixed in Section 7**
by deriving a direction-correct gate (d) from the frozen split's own data).

**Before applying any threshold to a new comparison, verify two things:**
1. The descriptor can actually resolve the difference being tested (see
   Section 4 — it cannot resolve rattle-only differences).
2. The regime the threshold was derived from matches the regime it is being
   applied to (e.g. a threshold derived from TRAIN-vs-HOLDOUT separation
   should not be assumed valid for TRAIN-vs-VALIDATION separation without
   re-deriving it from the analogous data).

## 9. Invariants that must never be violated

- cfg109/cfg110 **labels** (energy, forces, stress) remain SEALED at all
  times. Geometry (cell, positions) may be read for design/screening
  purposes — this has been done repeatedly this session and is permitted.
  Energy, forces, and stress may **not** be read under any circumstance in
  this phase.
- cfg109/cfg110 remain SEALED through the **entire** roadmap up to and
  including the 300-structure round and the 500-structure round (and their
  respective training runs). They are unsealed **exactly once**: immediately
  before LAMMPS readiness is assessed, against the **final model trained on
  the full ~500-structure dataset** — never against the 110-structure
  remediation checkpoint, never against any 300-structure interim model.
  See Section 11 for the full roadmap and the current interim (non-sealed)
  progress check.
- `configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt` now exists (written
  this session) and documents this trigger. The **numeric** final-gate
  threshold itself is still TBD by design — it must be derived from data
  available at 500-structure-round time (Section 8's no-invented-numbers
  pattern), fixed before the 500-structure retraining run begins, and
  strictly before cfg109/cfg110 are ever unsealed.
- No DFT has been run for cfg111-cfg115. No structures or QE inputs exist
  for them on disk. No file under `data/al3ni_remediation_v1/production_dft/`,
  Dataset-100, or cfg101-cfg108 has been modified by this workstream.

## 11. Training roadmap and unsealing trigger (added this session)

**Roadmap:**

```
110 structures -> train -> 300 structures -> train -> 500 structures -> train -> LAMMPS
```

- **110 structures** = the current remediation batch (cfg101-cfg110 frozen
  design + cfg111-cfg115 gate-clean design, Section 6) — this checkpoint.
- **300 structures** and **500 structures** = future expansion rounds, not
  yet designed. Each must follow the gate process in
  `configs/EXPANSION_BATCH_DESIGN_POLICY.md` (written this session) —
  thresholds re-derived per round, never reused verbatim.
- **LAMMPS** = the downstream production-MD use of the final model; readiness
  for it is what the final unsealing decides.

**Unsealing trigger (authoritative, restated from Section 9):** cfg109 and
cfg110 stay SEALED through the 300-structure round and the 500-structure
round, including their training runs. They are unsealed **exactly once**,
**immediately before LAMMPS readiness is assessed**, against the **final
model trained on the full ~500-structure dataset** — not against this
110-structure checkpoint, not against any 300-structure interim model. Full
statement in `configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`.

**Interim gate for the current (110-structure) checkpoint — NOT sealed, NO
pass/fail threshold, progress check only:**

1. Relative-energy error on **cfg043_Al3Ni_volume_rattle_expansion**
   (Dataset-100 HOLDOUT, not sealed) — new 110-structure model vs the OLD
   Dataset-100 model. Same comparison used to originally diagnose the
   cfg043 failure (Section 2).
2. Relative-energy error on **cfg115_Al3Ni_iso_expansion** (VALIDATION, not
   sealed, this session's resolved +5.30% design, Section 6/7).

No threshold is defined or required at this stage — this checkpoint is a
progress signal into the 300-structure round, not a go/no-go gate. Do not
invent a pass/fail number here; that would repeat the Section 8 pattern.

## 12. Round-2 (cfg111-cfg115) DFT execution and validation

**DFT status: COMPLETE.** All 5 configs ran real single-point SCF QE
production jobs and passed. Not part of the frozen v1 (cfg101-cfg110)
batch — entirely separate `round2_*` directories under
`data/al3ni_remediation_v1/`, so the v1 frozen manifests/hashes and
cfg109/cfg110 are untouched (re-verified by hash after this round's DFT
ran; see Invariants below).

**Artifacts:**
- `data/al3ni_remediation_v1/round2_structures/` — 5 EXTXYZ structures
  (isotropic strain + Cartesian rattle, same construction convention as
  `scripts/generate_al3ni_remediation_v1.py`)
- `data/al3ni_remediation_v1/round2_qe_inputs/` — 5 QE `.in` files (same
  ecutwfc/ecutrho/smearing/k-grid/pseudopotentials as Dataset-100)
- `data/al3ni_remediation_v1/round2_production_dft/` — 5 completed QE runs,
  one `attempt_001/` each, sequential (single GPU), all `EXIT_CODE=0`,
  `JOB_DONE=YES`, `SCF_CONVERGED=YES`
- `data/al3ni_remediation_v1/round2_manifest.csv` — config_id/role/family/
  strain/rattle/seed/hashes/dft_status for all 5, `assembled_into_dataset=NO`
- `results/al3ni_remediation_dft_validation_v1/round2_config_validation.csv`
  and `configs/AL3NI_ROUND2_DFT_VALIDATION_STATUS.txt` — full scientific
  validation (see below)

**Validation performed (mirrors `validate_al3ni_remediation_dft.py`
methodology): 5/5 VALID, 0 failures.**
1. Geometry-echo identity: QE's own XML-recorded geometry vs the canonical
   input, for all 5 — MATCH (max delta < 2e-8 bohr, i.e. floating-point
   identical). Since this was single-point SCF (no ionic relaxation), the
   DFT-executed geometry is confirmed identical to what gates (a)-(d) in
   Section 6 already evaluated — **no gate recomputation needed**, the
   existing PASS verdicts stand on the actual DFT geometry, not just the
   pre-DFT design.
2. QE parameter compatibility vs Dataset-100: ecutwfc=90.0 Ry, ecutrho=720.0
   Ry, XC=SLA PW PBX PBC, Marzari-Vanderbilt smearing, degauss=0.0100 Ry —
   identical for all 5. Irreducible k-point count is 150 for the two
   non-rattle configs and 324 for the two rattle configs, matching the same
   150-vs-324 split Dataset-100's own rattle-family configs
   (cfg035/036/037) show at the identical 10x8x8x0x0x0 K_POINTS card (k-point
   count is symmetry-derived, not a QE input parameter — rattle breaks the
   symmetry the non-rattle cell has).
3. Exit code 0, unique `JOB DONE.`, SCF converged, non-truncated, exactly
   one finite final energy, exactly 16 finite 3-vector forces, one finite
   3x3 stress tensor, Al12Ni4/16-atom composition, no NaN/Inf token
   anywhere, correct execution-input identity, no duplicate output hashes
   — all 5/5.

**Final energies (Ry):** cfg111 -1847.52097825, cfg112 -1847.51994921,
cfg113 -1847.47723059, cfg114 -1847.47505204, cfg115 -1847.49101404.

**Invariants re-confirmed after round-2 DFT (all byte-identical to their
previously recorded hashes):** cfg109/cfg110 structure files, v1
`split_membership_manifest.csv`/`remediation_manifest.csv`, cfg101/cfg108
`qe.out` (spot check), Dataset-100 `ni_al_dataset100_dft.extxyz`. No
cfg109/cfg110 label (energy/forces/stress) was read.

**Assembly: COMPLETE.** Labels extracted from each config's QE
`data-file-schema.xml` using the exact convention of
`scripts/extract_dataset75.py` (Hartree->eV, Bohr->Angstrom, QE
positive-compression stress flipped to ASE positive-tension — same units
as Dataset-100/Pilot-25: eV, Angstrom, eV/Angstrom, eV/Angstrom^3).
Round-trip verified (read back matches: geometry atol 5e-8, energy atol
1e-10, forces atol 5e-9, stress atol 1e-14 — same tolerances as
`extract_dataset75.py`).

Output files (new, `data/datasets/`, none pre-existing):
- `ni_al_round2_dft.extxyz` (+`.sha256`) — all 5, labeled
- `ni_al_round2_train_4.extxyz` (+`.sha256`) — cfg111/112/113/114
- `ni_al_round2_validation_1.extxyz` (+`.sha256`) — cfg115
- `ni_al_round2_dft_manifest.csv` — per-config energy/force/stress provenance
- `configs/AL3NI_ROUND2_ASSEMBLY_STATUS.txt` — full assembly report

Energy range: -25136.80 to -25136.18 eV. Max |force| range: 0.058-0.269
eV/Angstrom. `round2_manifest.csv` now records
`assembled_into_dataset=YES` for all 5.

**Explicitly NOT done:** these new round2 files are **not merged** into
`ni_al_dataset100_train_65.extxyz` / `ni_al_dataset100_validation_15.extxyz`
or any other existing Dataset-100 file (untouched, hash-verified after this
step). cfg101-cfg108 were never assembled into a labeled dataset this
session either. Combining Dataset-100 + cfg101-108 + round2 into the actual
train/validation/test split used for the next training run is a separate,
explicit decision — not yet made.

## 10. Next actions, in order

1. ~~Resolve the cfg115 validation-placement question (Section 7).~~ DONE.
2. ~~Re-run all gates on the revised design.~~ DONE — gates (a)-(d) PASS.
3. ~~Write the pre-registered acceptance criterion.~~ DONE
   (`configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`).
4. ~~Single-point SCF convergence check at the highest approved strain.~~
   DONE — cfg113 (+5.60%), 23 iterations, converged cleanly.
5. ~~Structure/QE-input generation for cfg111-cfg115.~~ DONE.
6. ~~Run full production DFT for cfg111-cfg115.~~ DONE — 5/5 PASS,
   scientifically validated (Section 12).
7. ~~Assemble cfg111-cfg115 into labeled TRAIN/VALIDATION dataset files.~~
   DONE — `data/datasets/ni_al_round2_{train_4,validation_1,dft}.extxyz`
   (Section 12). Not yet merged with Dataset-100/cfg101-108.
8. **Decide and execute the merge** of Dataset-100 + cfg101-108 + round2
   into the actual combined train/validation/test split for the next
   training run — not started. cfg109/cfg110 remain excluded/sealed
   throughout.
9. Train the resulting model and record the interim gate numbers (Section
   11: relative-energy error on cfg043 and cfg115 vs the OLD Dataset-100
   model, no threshold) — not started; no training has occurred yet.

---

## 13. Decision log

### 2026-08-17 — DECISION: STOP EXPANSION AT ~220 STRUCTURES

**DECISION:** Stop expansion at ~220 structures.

**EVIDENCE:**
- VALIDATION energy RMSE flat/noisy across 129->211->218 (1.7/1.7/1.9
  meV/atom), despite TRAIN growing 91->180 (2.4x) and closing nearly all
  Tier-1 gaps.
- Force RMSE still improving but sharply diminishing returns (-0.5/-0.5/-0.1).
- cfg043/cfg115 probe swings correlate with ROUND SIZE not phase content:
  large rounds (+10/+14/+82) always improved both probes; small rounds
  (+2/+7) always regressed them, no exceptions across 5 transitions.

**NEXT ACTION:** Close only the 2 remaining EXTRAPOLATION flags (cfg041,
cfg107), retrain once more, then move directly to acceptance-criterion +
unsealing. Do NOT push toward 300/500 without new justification (e.g. a
held-out re-evaluation showing continued gains).

cfg109/cfg110 remain sealed; not read, designed, or touched by this entry.

confirmation written, STOPPING NOW.
