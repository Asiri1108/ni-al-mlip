# Stage 4 — Split Strategy Confirmation

Confirms the split strategy proposed in
`AL3NI_MERGE_SPLIT_TRAIN_SCALEUP_PLAN.md`'s "Open question," now that
Stages 1-3 are complete and the merge has been audited.

## Decision

**No re-derivation of roles.** TRAIN/VALIDATION membership for v1
(cfg101-110) and round2 (cfg111-115) was already decided and gate-cleared
at design time (`SESSION_STATE_AL3NI_EXPANSION_DESIGN.md` Section 6,
`remediation_manifest.csv`). This stage confirms that decision holds after
merging with Dataset-100, rather than re-deciding from scratch.

**TEST+BLIND_HOLDOUT (Dataset-100's 20) is left unchanged** — no new
members added from v1 or round2, since neither round was designed with a
TEST/HOLDOUT role. cfg109/110 (sealed) continue to serve as this
remediation branch's own final holdout, unsealed once at the very end
per the roadmap. This was flagged as an open question in the plan and is
being taken as confirmed by proceeding through Stages 1-4 without
correction.

## Final counts

| Split | Dataset-100 | v1 (cfg101-108) | round2 (cfg111-115) | Combined |
|---|---|---|---|---|
| TRAIN | 65 | 6 | 4 | **75** |
| VALIDATION | 15 | 2 | 1 | **18** |
| TEST+BLIND_HOLDOUT | 20 | 0 | 0 | **20** (unchanged) |
| SEALED (excluded) | 0 | 2 (109/110) | 0 | **2** |
| **Total** | 100 | 8 | 5 | **113** usable + 2 sealed = 115 generated |

## Files (already written as part of Stage 3's merge)

- `data/datasets/ni_al_combined113_dft.extxyz` (113, all roles tagged)
- `data/datasets/ni_al_combined113_train_75.extxyz` (75) — ready for training
- `data/datasets/ni_al_combined113_validation_18.extxyz` (18) — ready for training
- Each with a `.sha256` sidecar

Note: Stage 3's merge script produced these split-ready files as a natural
byproduct of the merge itself (the underlying per-source TRAIN/VALIDATION
files were simply concatenated), so what the plan called "Stage 5 —
execute the split" is **already done**. Training (Stage 6) has not been
run — stopping here per "go ahead for stages 1-4."

## Audit result carried over from Stage 3

Population-wide descriptor check across the full merged Al3Ni population
(37 configs: Dataset-100's 24 + v1's 8 + round2's 5): no leakage risk (min
TRAIN-to-cfg043 distance 0.973, threshold 0.734644); one pre-existing,
already-documented near-duplicate TRAIN-TRAIN pair (cfg102/103 vs
historical Pilot-25 iso_m02/p02 controls, ~1e-7 Angstrom-level, flagged at
v1 generation time, not new, not a leakage or role violation).

## Status

**STAGE 4 COMPLETE.** Ready for Stage 5 (already materially done) / Stage 6
(train) on your go-ahead.
