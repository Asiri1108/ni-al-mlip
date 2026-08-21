# Ni-Al Project Knowledge

Technical/scientific explainer for this project, for a reader with no prior
context. Distinct from `SESSION_STATE_AL3NI_EXPANSION_DESIGN.md` (a
resume-checkpoint for one workstream) — this document explains the whole
project and is kept updated as work progresses. Last updated: see the date
in the most recent entry of "Update log" at the bottom.

## 1. What this project is

Building a machine-learned interatomic potential (MLIP) for the Ni-Al
intermetallic system, covering five phases: **AlNi, Al3Ni2, AlNi3, Al3Ni5,
Al3Ni**. The goal is a model accurate enough to replace DFT for downstream
molecular dynamics (LAMMPS), trained by fine-tuning a MACE foundation model
on DFT-labeled structures (energy, forces, stress) spanning each phase's
relaxed geometry plus systematic strain/rattle perturbations around it.

## 2. DFT methodology

All labels come from Quantum ESPRESSO 7.6, PBE exchange-correlation.
- `ecutwfc = 90 Ry`, `ecutrho = 720 Ry`
- Pseudopotentials: `Al.pbe-n-kjpaw_psl.1.0.0.UPF`, `ni_pbe_v1.4.uspp.F.UPF`
  (fixed SHA256-pinned identities, verified before every production run)
- Marzari-Vanderbilt smearing, `degauss = 0.010 Ry`
- `conv_thr = 1.0d-10`, `mixing_beta = 0.30`, Davidson diagonalization
- K-grid depends on phase (Al3Ni uses `10 8 8 0 0 0`); irreducible k-point
  *count* varies with cell symmetry (e.g. Al3Ni: 150 for symmetric cells,
  324 once rattle breaks that symmetry) — this is expected, not a
  parameter mismatch.
- QE binary: `tools/qe_gpu/builds/sm_89_autoconf/PW/src/pw.x`, SHA256-pinned.
  **Correction (2026-08-16): GPU offload IS active.** A prior session
  misread the `"Serial multi-threaded version, running on 8 processor
  cores"` banner (which only describes MPI/OpenMP topology — no MPI ranks,
  8 OpenMP threads) as evidence of CPU-only execution. Every `qe.out` in
  this project, including that same run, also contains a separate status
  line ~30-40 lines later: `"GPU acceleration is ACTIVE.  1 visible GPUs
  per MPI rank"`. This was already independently proven with real
  `nvidia-smi` utilization telemetry and CPU/GPU numerical equivalence in
  `configs/GPU_QE_VALIDATION_STATUS.txt` and
  `configs/GPU_TIMING_BENCHMARK_STATUS.txt` (2026-08-11/12, i.e. before the
  incorrect claim was written). The binary is linked against real CUDA/
  OpenACC runtime libraries (`libcudart`, `libcublas`, `libcufft`, etc.) —
  confirmed via `ldd`/`strings`. No fix or rebuild was needed.
- Label extraction: parsed from QE's `data-file-schema.xml` (not
  text-scraped from `qe.out`), converting Hartree->eV and Bohr->Angstrom,
  and flipping the stress sign (QE reports positive-compression; the
  project's ASE/extxyz convention is positive-tension). This is the
  extraction method established in `scripts/extract_dataset75.py` and
  reused for every subsequent DFT batch.

## 3. Dataset lineage

```
Pilot-25 (25, historical foundation)
  + Expansion-75 (75, systematic perturbations: iso/uniaxial/biaxial/shear/rattle)
  = Dataset-100 (100, frozen canonical) -- TRAIN 65 / VALIDATION 15 / TEST+BLIND_HOLDOUT 20
  |
  | (cfg043 Al3Ni holdout failure discovered)
  v
Al3Ni remediation v1 (cfg101-cfg110, 10 configs)
  -- TRAIN 6 (101-106) / VALIDATION 2 (107-108) / CONFIRMATION_HOLDOUT 2 (109-110, SEALED)
  |
  v
round2 (cfg111-cfg115, 5 configs, extends the expansion branch to +5.60%)
  -- TRAIN 4 (111-114) / VALIDATION 1 (115)
  |
  v
combined-113: Dataset-100 + v1's 8 usable + round2's 5
  -- TRAIN 75 / VALIDATION 18 / TEST+BLIND_HOLDOUT 20 (unchanged) / SEALED 2 (109-110, excluded)
  |
  | (results/full_coverage_audit_v1: Tier-1 zero-TRAIN-support gaps found --
  |  biaxial all 5 phases, shear_rattle 4/5, orthorhombic 3/5, plus AlNi3
  |  volume_rattle (cfg098) and Al3Ni5 uniaxial (cfg056) coverage failures)
  v
round3 (cfg117-cfg141, 14 configs, closes priority gaps from that audit)
  -- TRAIN 14 (all TRAIN role; 9 via pod01, 5 via pod02)
  |
  v
combined-127: combined-113 + round3's 14
  -- TRAIN 89 / VALIDATION 18 (unchanged) / TEST+BLIND_HOLDOUT 20 (unchanged) / SEALED 2 (excluded)
  |
  | (coverage audit reconstructed for combined-127: 4 gaps fully closed,
  |  Al3Ni5/biaxial + AlNi3/biaxial the only 2 buckets still fully
  |  zero-TRAIN-support -- round3 didn't design biaxial candidates for
  |  either phase)
  v
round4 (cfg143 Al3Ni5, cfg145 AlNi3, 2 configs, closes the last 2 Tier-1 gaps)
  -- TRAIN 2 (both TRAIN role; "outer" candidates, 1.5x the existing
  |  BLIND_HOLDOUT probe magnitude, same sign/axis -- the "inner" 0.5x
  |  candidates for both phases failed the redundancy gate, same failure
  |  mode as round3's 12 inner rejections)
  v
combined-129 (current): combined-127 + round4's 2
  -- TRAIN 91 / VALIDATION 18 (unchanged) / TEST+BLIND_HOLDOUT 20 (unchanged) / SEALED 2 (excluded)
```

**Roadmap:** `110 structures -> train -> 300 structures -> train -> 500
structures -> train -> LAMMPS`. "110" = Dataset-100 (100) + v1 (10, incl.
2 sealed); combined-113/127/129 are incremental gap-closing checkpoints
within that same "110" stage, not a redefinition of the roadmap milestones.
The 300- and 500-structure rounds are future work, not yet designed; each
must follow `configs/EXPANSION_BATCH_DESIGN_POLICY.md`. After combined-129,
every phase/family bucket has at least one TRAIN member for the first
time — no more Tier-1 (zero-support) gaps remain, though many buckets are
still thin (`INFO_LOW_TRAIN_COUNT`, 1-2 TRAIN members) or still flagged
`EXTRAPOLATION` against a degenerate single-point range. See
`results/full_coverage_audit_v1/priority_ranking_combined129.md` for the
full remaining list.

**Why the remediation branch exists:** cfg043 (+3.5% isotropic Al3Ni
expansion, Dataset-100 HOLDOUT) was originally diagnosed as a "coverage
gap" (sparse-but-present TRAIN support). Re-diagnosed this session as
**extrapolation**: Dataset-100's Al3Ni TRAIN ceiling on the expansion side
was only +3.0% (cfg029) — cfg043 (+3.5%) and cfg109/110 (+4.0%) sit
entirely above it, with zero TRAIN support at any higher strain. The v1 and
round2 batches exist to extend the TRAIN ceiling on the expansion branch
(now to +5.60%, cfg113/114) so the model is interpolating, not
extrapolating, in that region.

## 4. Descriptor and gate methodology (developed this session)

Used to screen every new candidate structure before it's accepted into
TRAIN/VALIDATION, and to audit a population after merging.

**Descriptor** (per config): `{sorted species-grouped (Al-Al / Ni-Ni /
Al-Ni) minimum-image pairwise distance vector (shape), volume/atom,
Green-Lagrange strain tensor relative to the phase's relaxed reference
cell}`. Pairwise distance between two configs = Euclidean combination of
three z-scored sub-distances (shape RMSD, |delta vol/atom|, strain
Frobenius norm), each normalized by its own population standard deviation.

**Known blind spot:** for a matched-strain `iso_expansion` /
`volume_rattle_expansion` pair (same cell, same strain, only a rattle
perturbation differs), `d_vol = d_strain = 0` exactly — the descriptor is
measuring only a small rattle-induced shape change against a scale
calibrated for much larger strain-driven differences, so it **cannot
resolve rattle-only differences**. This caused two false-positive
"redundant" flags early in the session and drove gate (c) below.

**Four gates** (full definitions and re-derivation rules in
`EXPANSION_BATCH_DESIGN_POLICY.md`):
- **(a) Redundancy** — vs existing TRAIN of the same phase. Threshold =
  5th percentile of intra-population pairwise distance. Reject below
  (too similar to something already in TRAIN).
- **(b) Leakage** — vs the sealed/holdout set. Threshold = minimum
  pairwise distance the frozen split already accepts between TRAIN and
  HOLDOUT. Reject below (too close to a sealed point).
- **(c) Role-based** — a matched-strain family pair must share role
  (never split across TRAIN/VALIDATION); the descriptor can't certify
  independence for such a pair. Gate (a)'s threshold only applies to
  different-role, different-strain pairs — the regime where it's valid.
- **(d) TRAIN-vs-VALIDATION placement** — VALIDATION's nearest-TRAIN
  distance must sit between a floor (matched-strain degeneracy scale —
  below this it's a duplication risk) and a ceiling (the loosest
  nearest-TRAIN distance the frozen split already accepts for a
  VALIDATION point — above this it's an extrapolation risk). This gate
  was added this session; see "Recurring failure pattern" below for why.

**Recurring failure pattern (five rounds, all fixed the same way):** every
failed design round this session came from a threshold either invented
outright, or correctly derived but then applied outside the regime it was
derived for (most notably: reusing the redundancy/duplication threshold to
judge TRAIN-vs-VALIDATION proximity, where the actual failure mode is the
opposite — extrapolation, not duplication). The fix each time was the
same: derive the threshold from the data actually available, in the regime
it will actually be applied to, never reuse a number across a phase/round
boundary without re-deriving it. This is now a standing project policy
(`EXPANSION_BATCH_DESIGN_POLICY.md`), not just a one-off lesson.

**Provenance note (2026-08-16):** no saved script for this descriptor was
ever found on disk for round3's or the coverage audit's original runs (both
done inline in an earlier session). The round4 design
(`scripts/design_round4_biaxial_al3ni5_alni3.py`) and the coverage-audit
updates (`scripts/update_full_coverage_audit_combined127.py` /
`..._combined129.py`) are from-scratch reconstructions of this same
descriptor from the prose spec in `SESSION_STATE_AL3NI_EXPANSION_DESIGN.md`
Section 3 — that section's own reconstruction was independently validated
to 0.0056% fidelity against the frozen Al3Ni leakage threshold (0.734603 vs
0.734644) before being trusted. Round4's inner-candidate rejections
reproduced the exact same failure mode documented for round3's 12 inner
rejections (redundant vs. an existing small-strain TRAIN member), which is
corroborating evidence the reconstruction is behaving correctly — but
treat any newly-derived threshold as high-confidence, not re-proven to
that same 0.0056% figure each time.

## 5. Sealed-label policy

`cfg109_Al3Ni_iso_expansion` and `cfg110_Al3Ni_volume_rattle_expansion`
(the remediation branch's CONFIRMATION_HOLDOUT pair) have their energy/
forces/stress permanently sealed until a final candidate model is frozen.
Geometry (cell, positions) may be read for design/screening at any time —
labels may not, under any circumstance, until unsealing. They are unsealed
**exactly once**, immediately before LAMMPS-readiness is assessed, against
the **final model trained on the full ~500-structure dataset** — never
against any intermediate checkpoint (not the 113/127/129-structure merges,
not a future 300-structure interim model). Full statement:
`configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`. The final numeric
acceptance threshold is intentionally left undefined until immediately
before that 500-structure round, to avoid inventing a number ahead of the
data that should determine it.

## 6. Training approach

MACE, LoRA fine-tuning (rank 4, alpha 1.0) of the `mace-matpes-pbe-0`
foundation model — not training from scratch. `WeightedEnergyForcesStressLoss`
(weights energy=1, forces=10, stress=1), float64 precision, Adam
lr=0.001, EMA decay=0.995, batch size 2, single GPU. Reference run
(`dataset100_matpes_pbe_lora_v1`, 65 TRAIN/15 VALIDATION): **339 seconds**
wall-clock for 100 epochs, best checkpoint at epoch 98 (energy RMSE 0.70
meV/atom, force RMSE 5.97 meV/Angstrom, stress RMSE 2.13 meV/Angstrom^3).
No multi-GPU/distributed training precedent exists in this project yet —
every training run so far has been single-GPU, single-job.

**Wall-time is not stable across container sessions.** The combined-113
run (2026-08-15) took 350s on GPU UUID `GPU-794993dd-...` (driver
580.159.04, mean utilization 44.3%). The combined-127 and combined-129 runs
(2026-08-16, same session) took ~800-860s each on a *different* GPU UUID
`GPU-54d38414-...` (driver 570.172.08, mean utilization 17-18%) — 2.3-3.1x
slower, uniform across every epoch (not a startup/ramp artifact), despite
near-identical dataset size and setup-phase timing. Root cause: this
project's pod is not pinned to the same physical GPU across
restarts/reassignments on the underlying cloud infrastructure. Training
correctness is unaffected (same architecture, same code path — only
wall-clock), but **do not use this project's historical per-epoch/
per-structure timing numbers for capacity planning** (e.g. sizing the
300-structure round) without accounting for this variance.

## 7. Current status (as of the most recent update below)

- Dataset-100: frozen, unchanged since creation.
- v1 (cfg101-cfg110): DFT complete for all 10; cfg101-108 assembled into
  labeled extxyz this session; cfg109/110 remain sealed, geometry-only.
- round2 (cfg111-cfg115): designed, gate-cleared, DFT executed for real,
  validated, and assembled into labeled extxyz this session.
- **Combined-113 dataset**: Dataset-100 + v1's 8 usable + round2's 5,
  merged this session into `data/datasets/ni_al_combined113_{dft,
  train_75,validation_18}.extxyz`. TEST+BLIND_HOLDOUT (Dataset-100's 20)
  left untouched by design — no TEST/HOLDOUT role exists for v1 or round2;
  cfg109/110 continue to serve as this branch's own final holdout.
- Population-wide audit after merging: no leakage risk (min TRAIN-to-cfg043
  distance 0.973, threshold 0.734644), one pre-existing/documented
  near-duplicate pair (cfg102/103 vs historical Pilot iso_m02/p02 controls,
  both TRAIN role, ~1e-7 Angstrom-level, already flagged at v1 generation
  time — not a new issue).
- **Training on combined-113: COMPLETE.** LoRA fine-tune
  (`al3ni_combined113_lora_v1`), 350s wall-clock, epoch 99 selected.
  Validation: energy RMSE 1.8 meV/atom, force RMSE 6.1 meV/Angstrom (rel.
  3.29%), stress RMSE 2.4 meV/Angstrom^3 -- somewhat higher than the
  Dataset-100 baseline (0.70/5.97/2.13), expected since TRAIN/VALIDATION
  now spans up to +5.60% Al3Ni strain vs the old +3.0% ceiling. Full report:
  `configs/AL3NI_COMBINED113_MACE_TRAINING_STATUS.txt`. Model frozen
  read-only: `models/al3ni_combined113_lora_v1/`.
- **Interim gate evaluation: COMPLETE.** Relative-energy error (identical
  formula to `scripts/evaluate_dataset100_final.py`, the one that
  originally flagged cfg043), new model vs old Dataset-100 model:
  - cfg043: 6.60 -> 2.88 meV/atom (-3.72, ~56% reduction)
  - cfg115: 12.35 -> 6.14 meV/atom (-6.21, ~50% reduction)
  Both improve substantially. No threshold applies (progress signal, not a
  gate) -- but this is the first real evidence the remediation branch is
  doing what it was designed to do. Full report:
  `configs/AL3NI_INTERIM_GATE_STATUS.txt`. cfg109/cfg110 not evaluated
  (sealed).
- **Round3 (cfg117-cfg141, 14 configs): DFT complete, integrity-verified,
  extracted, screened, merged, trained, gate-evaluated.** Ran across two
  pods (`ni_al_round3_pod01`: 9 configs, orphaned mid-batch by an apparent
  container restart at 6/9, resumed cleanly after patching the runner
  script to skip already-COMPLETE configs; `ni_al_round3_pod02`: 5/5 in one
  pass). Full comprehensive integrity check (SCF convergence, NaN/Inf,
  frozen-design SHA256, per-phase QE parameter uniformity, AlNi3 `nspin`
  correctness, k-point-count sanity) passed 14/14. Extracted via
  `scripts/extract_round3_dft.py` (reused `extract_dataset75.py`'s XML
  parsing verbatim). Outlier screen (self-population MAD + phase-context
  percentile vs combined-113) flagged 2 configs (cfg119, cfg135, both
  AlNi3) at the top of their phase's historical distribution — expected
  and by design, since both were deliberately generated beyond the
  existing TRAIN ceiling.
- **Combined-127**: combined-113 + round3's 14 (`scripts/merge_round3_into_combined113.py`).
  TRAIN 89 / VALIDATION 18 (unchanged). Training
  (`al3ni_combined127_lora_v1`): validation RMSE_E 1.6 meV/atom, RMSE_F 5.5
  meV/Angstrom, RMSE_stress 2.0 meV/Angstrom^3 — improved on every metric
  vs combined-113 baseline (same VALIDATION set both times). Interim gate
  vs combined-113: cfg043 2.88->2.15 meV/atom, cfg115 6.14->4.64 meV/atom,
  both improved. Full reports: `configs/AL3NI_COMBINED127_MERGE_STATUS.txt`,
  `configs/AL3NI_COMBINED127_MACE_TRAINING_STATUS.txt`,
  `configs/AL3NI_INTERIM_GATE_127_STATUS.txt`.
- **Coverage audit reconstructed for combined-127**
  (`scripts/update_full_coverage_audit_combined127.py` —
  `results/full_coverage_audit_v1/priority_ranking_combined127.md`): no
  saved script existed for the original audit either, reconstructed from
  documented conventions and cross-validated to 100% flag agreement with
  the original CSV. Round3 fully closed 4 of its ~13 targeted gaps
  (cfg056, cfg086, cfg088, cfg098); the rest were downgraded from
  zero-TRAIN-support to thin single-point-anchor, still formally flagged.
  **Al3Ni5/biaxial and AlNi3/biaxial were the only 2 buckets still fully
  zero-TRAIN-support** (round3 designed no biaxial candidates for either
  phase).
- **Round4 (cfg143 Al3Ni5, cfg145 AlNi3, 2 configs): designed, DFT'd,
  extracted, screened, merged, trained, gate-evaluated — closes those last
  2 Tier-1 gaps.** Design
  (`scripts/design_round4_biaxial_al3ni5_alni3.py`) proposed both an
  "inner" (0.5x) and "outer" (1.5x) candidate per phase at the existing
  BLIND_HOLDOUT probe's magnitude/sign/axis and let the redundancy/leakage
  gates decide rather than presupposing the outcome; both inner candidates
  failed redundancy (same failure mode as round3's 12 inner rejections),
  both outer candidates passed. DFT ran with live-verified GPU utilization
  (mean 65.9%, peak 95% across both configs) — see the GPU correction in
  Section 2. Outlier screen: no flags (self-population screen explicitly
  skipped, n=2 too small to be meaningful; phase-context percentile showed
  both mid-distribution).
- **Combined-129 (current)**: combined-127 + round4's 2
  (`scripts/merge_round4_into_combined127.py`). TRAIN 91 / VALIDATION 18
  (unchanged). Training (`al3ni_combined129_lora_v1`): validation RMSE_E
  1.7 meV/atom, RMSE_F 5.6 meV/Angstrom, RMSE_stress 2.1 meV/Angstrom^3 —
  essentially flat vs combined-127 (expected: round4 targeted coverage in
  2 different phases, not aggregate accuracy). Interim gate vs
  combined-127: cfg043 2.15->2.36 meV/atom (+0.21), cfg115 4.64->5.29
  meV/atom (+0.65) — both slightly worse, small in absolute terms and
  plausibly LoRA-fit noise since round4 added zero Al3Ni-phase TRAIN
  (cfg043/cfg115 are both Al3Ni); reported as-is per the project's
  no-threshold interim-gate policy, not spun either way. Full reports:
  `configs/AL3NI_COMBINED129_MERGE_STATUS.txt`,
  `configs/AL3NI_COMBINED129_MACE_TRAINING_STATUS.txt`,
  `configs/AL3NI_INTERIM_GATE_129_STATUS.txt`.
- **Coverage audit updated for combined-129**
  (`scripts/update_full_coverage_audit_combined129.py` —
  `results/full_coverage_audit_v1/priority_ranking_combined129.md`, diffed
  against the combined-127 audit rather than the original combined-113
  one, to isolate round4's effect). Zero new/unexpected flags. **Zero
  remaining Tier-1 (fully zero-TRAIN-support) buckets** — every phase/
  family combination in the project now has at least one TRAIN member for
  the first time. 20 `EXTRAPOLATION` flags remain open (thin single-point
  anchors and other deformation families untouched by round3/round4) —
  full list in that file.
- Not yet done: anything related to the future 300-structure round (out of
  scope until explicitly taken up) — that round is a much larger, formally
  undesigned effort distinct from round3/round4's incremental gap-closing.
  This closes out the merge -> split -> train -> interim-gate plan
  (`AL3NI_MERGE_SPLIT_TRAIN_SCALEUP_PLAN.md`, Stages 1-7) and its
  natural continuation through combined-129.

## Update log

- 2026-08-15: Initial version. Covers through Stage 3/4 of the merge ->
  split -> train plan (`AL3NI_MERGE_SPLIT_TRAIN_SCALEUP_PLAN.md`):
  cfg101-108 assembled, combined-113 dataset merged and audited, split
  strategy confirmed (TRAIN 75 / VALIDATION 18 / TEST+HOLDOUT 20 unchanged
  / SEALED 2). Training and interim gate evaluation not yet run.
- 2026-08-15 (same day, later): Stage 6 (train) complete -- see Section 7.
- 2026-08-15 (same day, later still): Stage 7 (interim gate) complete --
  cfg043 and cfg115 relative-energy error both improved substantially
  (~56% and ~50% reduction respectively). Merge -> split -> train ->
  interim-gate plan fully closed out. Next work is the future 300-structure
  round, not yet started.
- 2026-08-16: Round3 pod01 resumed after an orphaned mid-batch stop
  (container restart), integrity-verified (14/14), extracted, outlier-
  screened, merged into combined-127, trained, interim-gated -- see
  Section 7. Corrected a standing documentation error in Section 2 (GPU
  offload was always active; a prior session misread the QE MPI/OpenMP
  banner). Reconstructed the full coverage audit for combined-127 (no
  saved script existed for the original either) -- found Al3Ni5/biaxial
  and AlNi3/biaxial as the last 2 fully zero-TRAIN-support gaps. Designed,
  DFT'd (GPU-monitored), extracted, screened, and merged round4 (2
  configs) closing both -- combined-129, zero Tier-1 gaps remaining
  project-wide. See Section 7 for full detail on every step.
