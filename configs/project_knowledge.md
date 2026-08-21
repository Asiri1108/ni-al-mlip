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
combined-129: combined-127 + round4's 2
  -- TRAIN 91 / VALIDATION 18 (unchanged) / TEST+BLIND_HOLDOUT 20 (unchanged) / SEALED 2 (excluded)
  |
  | (round300 = the actual ~300-structure round, scoped as a full factorial
  |  gap-fill: every phase x deformation-family x direction x sign x
  |  rattle-state combo with ZERO TRAIN members, not just the audit's
  |  flagged points. 128 candidates proposed, 82 survived gates -- split
  |  across 10 pods, 2 run locally + 8 launched by the user on separate
  |  rented GPU pods, all sharing the same network volume)
  v
round300 (cfg146-cfg272, 82 configs, 10 pods)
  -- TRAIN 82 (all TRAIN role)
  |
  v
combined-211: combined-129 + round300's 82
  -- TRAIN 173 / VALIDATION 18 (unchanged) / TEST+BLIND_HOLDOUT 20 (unchanged) / SEALED 2 (excluded)
  |
  | (first reserved-set (TEST+BLIND_HOLDOUT, 20, never trained on) evaluation
  |  since Dataset-100 -- every checkpoint 113/127/129/211 had only ever
  |  been measured via the weak 2-point interim gate. Result: BLIND_HOLDOUT
  |  rel-energy RMSE -0.855 meV/atom vs the old dataset100 baseline, still
  |  improving, not plateaued -- see Section 6)
  |
  | (coverage audit for combined-211: 14/20 EXTRAPOLATION flags closed,
  |  6 remain: cfg042 Al3Ni shear, cfg074 Al3Ni2 shear, cfg059/cfg061
  |  Al3Ni5 shear+rattle, plus AlNi shear/volume_rattle thin buckets)
  v
round212+213+214 (cfg273-cfg282, 7 configs total, pods A/B/C)
  -- TRAIN 7 (all TRAIN role); closes the last 4 EXTRAPOLATION flags +
  |  AlNi's 2 remaining thin buckets. Required real iteration, not a
  |  first-try success -- see Section 4's "matched-strain axis collision"
  |  note.
  v
combined-218 (current): combined-211 + round212/213/214's 7
  -- TRAIN 180 / VALIDATION 18 (unchanged) / TEST+BLIND_HOLDOUT 20 (unchanged) / SEALED 2 (excluded)
```

**Roadmap:** `110 structures -> train -> 300 structures -> train -> 500
structures -> train -> LAMMPS`. "110" = Dataset-100 (100) + v1 (10, incl.
2 sealed). combined-113/127/129 were incremental gap-closing checkpoints
within that same "110" stage; **round300 is the actual ~300-structure
round** (scoped as a full factorial gap-fill, landing at 213/300 = 71% of
the nominal milestone after gate attrition -- see Section 7). The
500-structure round is still future work, not yet designed; it must follow
`configs/EXPANSION_BATCH_DESIGN_POLICY.md`. **Correction:** an earlier
draft of this section projected "zero EXTRAPOLATION flags project-wide"
for combined-218 before the audit was actually re-run — that projection
was wrong. `scripts/update_full_coverage_audit_combined218.py` (run
2026-08-16, does not depend on the trained model, no reason to have
deferred it) found **2 flags still open**: `cfg041_Al3Ni_uniaxial_z_compression`
(BLIND_HOLDOUT, margin 0.007) and `cfg107_Al3Ni_volume_rattle_compression`
(VALIDATION, margin 0.015) — neither was ever targeted by round212/213/214,
which only closed cfg042/cfg074/cfg059/cfg061 + AlNi's 2 thin buckets, not
the full open-flag list from the combined-211 audit. Zero Tier-1
(zero-TRAIN-support) buckets remain, and 8 buckets are still
`INFO_LOW_TRAIN_COUNT` (1-2 TRAIN members: Al3Ni2 rattle/shear/volume_rattle,
Al3Ni5 volume_rattle, AlNi rattle/volume_rattle, AlNi3 rattle/shear). This
is a concrete demonstration of why a design-time projection should not be
treated as confirmed until the audit is actually re-run — it was wrong
here on the first check.

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

**Matched-strain axis collision, discovered closing round300's last 4 flags
(2026-08-16):** gate (a) as implemented does NOT include the policy's Gate
(c) role/matched-strain exemption (same gap as above, still not fixed).
This surfaced concretely when designing round212: a new pure-shear
candidate on the SAME axis as an existing round300 `shear_rattle` sibling
(e.g. Al3Ni `shear_xz` vs `cfg191_shear_rattle_xz_negative` at -0.029) got
*closer*, not farther, to that sibling as its magnitude increased —
because the descriptor can't cleanly separate "genuinely closer in strain
space" from "matched-strain-family, differs mainly by rattle noise" (the
same blind spot as cfg106/cfg108, just partial here: d_vol=0 exactly,
d_strain small-but-nonzero, not both exactly zero). Fix used: switch to a
DIFFERENT axis with no nearby rattled sibling (the coverage audit's
"shear" bucket pools all axes into one range check, so this still closes
the same flag) rather than implementing the real exemption. Two of
round212's four targets needed this; the other two (different phases, no
nearby round300 sibling) passed on a straightforward magnitude search.
Confirmed via direct sub-distance computation (`d_shape`/`d_vol`/`d_strain`
individually, not just combined distance) before concluding this, not
assumed.

## 5. Sealed-label policy

**STALE AS ORIGINALLY WRITTEN — cfg109/cfg110 are CONSUMED, corrected
2026-08-18.** The paragraph below described the *plan*; here is what
actually happened. There was never a 500-structure round (Section 3/6/7 —
the roadmap was superseded 2026-08-17, expansion stopped at combined-220).
`cfg109_Al3Ni_iso_expansion` / `cfg110_Al3Ni_volume_rattle_expansion` were
unsealed **exactly once**, 2026-08-17, against `al3ni_combined220_lora_v1`
(the actual final pre-unsealing checkpoint), per the locked threshold in
`configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt` (2.3865 meV/atom, the
max of the 19 genuinely-independent reserved-20 members, cfg060, excluding
design-contaminated cfg043 — see that file for the full derivation and a
same-day correction history). Result: **FAIL**, both configs
(cfg109 |error|=3.767, cfg110 |error|=3.732 meV/atom — both ~1.35-1.38
over threshold). Full result: `configs/AL3NI_FINAL_UNSEALING_RESULT.txt`.
This event does not repeat — cfg109/cfg110's labels are now ordinary
(consumed) data, were **not** merged into any split, and are no longer a
protected holdout for any gate.

**Follow-up investigation (2026-08-18, same day as the FAIL) before any
remediation was designed:** two questions were asked before assuming the
FAIL meant "need more data." (1) *Is the margin real or noise?* Retrained
combined-220 twice, identical data/hyperparameters, seed only (20260812,
20260813) — cfg109/cfg110 seed-to-seed spread ≈0.43 meV/atom, well inside
the ~1.35-1.38 meV/atom failure margin (robust FAIL on the fixed
threshold), but the *threshold itself* (derived from a single seed's
single-point reserved-20 max) shifts by ~0.81 meV/atom and changes which
config anchors it when reseeded — a real fragility in a threshold drawn
from n=1 model / n=19 points, flagged but not acted on (re-deriving the
threshold post hoc was explicitly out of scope — see
`configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`'s own "STATUS: LOCKED,
will NOT be revised" rule). (2) *Is this a model-capacity limit rather
than a data gap?* Retrained combined-220 at LoRA rank 8 and rank 16
(seed fixed at 20260811, the only variable changed). Rank 8: no
distinguishable effect (deltas smaller than the seed noise floor). Rank
16: error got measurably *worse* (~+0.92-0.93 meV/atom on cfg109/cfg110,
beyond the noise floor, wrong direction) — consistent with mild
overfitting at fixed data size, not a capacity ceiling being relieved.
**Capacity hypothesis rejected.** This is what justified treating the
FAIL as a genuine data-density gap and designing round285 (below) rather
than just cranking up rank or retrying with a different seed.

**Sealed confirmation pair — REVISED 2026-08-18, same day as the original
round285 design.** The first proposal, `cfg295_Al3Ni_iso_expansion`
(s=+3.75%) / `cfg296_Al3Ni_volume_rattle_expansion` (s=+4.25%), was
**retired, never DFT'd, no compute lost** — a dedicated reverse-leakage
verification pass (checking the sealed candidates against every approved
TRAIN rung, not just the RESERVED population the original design script
checked them against) found min distance to approved TRAIN = 0.2421
(cfg287 @ +4.0%), below both the policy-cited 0.734644 and round285's own
fresh threshold 0.3269.

**Root cause, worth keeping as a general principle:** a sealed
interpolation point placed *inside* a deliberately densified region is
self-contradictory. With 0.5-point TRAIN spacing, any interior point is
bound to ≤0.25 points of strain from its nearest TRAIN neighbor — density
and seal-isolation cannot coexist in the same interval. The original
round285 script never ran this specific check (sealed candidate vs.
newly-approved TRAIN candidates at leakage scale) because the sealed loop
only checked the RESERVED population (gate b) and a much tighter
duplicate epsilon (gate c) against the growing TRAIN pool — neither is
the leakage-scale reverse check that matters here. This is the same
category of error the project has hit before (a threshold or check
applied in the wrong regime), just a new instance of it: verify every
comparison direction a design decision implies, not just the ones the
original script's control flow happened to compute.

**First replacement (superseded same day):** `cfg297_Al3Ni_iso_expansion` /
`cfg298_Al3Ni_volume_rattle_expansion`, both s=3.5% — the one interval
(3.0%→4.0%) round285 could *not* densify to 0.5-point spacing (blocked by
leakage against cfg043, which sits at s=3.5000% almost exactly), and
therefore the only interval wide enough (1.0 points) for an interior
point to be meaningfully isolated from all 15 TRAIN rungs (8 existing +
7 new). Both cleared the regime-correct fresh threshold (0.3269) by
47-53%.

**cfg298 itself then retired — a second, more serious problem than
leakage.** cfg298 and cfg043 (same family, same nominal strain, s=3.5%)
collapse to the known matched-strain descriptor blind spot (d_vol/d_strain
≈1e-8/1e-9, only d_shape from the independent rattle draw differs). The
first pass judged this "acceptable — test redundancy, not leakage" (same
pattern as the historical cfg106/cfg108 false-duplicate flags). That
judgment was **wrong for this specific case and corrected same day**:
cfg043 is not an ordinary holdout — it is the FEEDBACK PROBE whose error
value steered 5+ remediation design rounds
(`AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`, CFG043 EXCLUSION
RATIONALE). A seal that is a descriptor-clone of the feedback probe
inherits that indirect design contamination — the two never-trained-on
points being "close" isn't the issue (that reasoning is fine for two
*clean* holdouts); the issue is that one of them isn't clean. `cfg297`
(iso_expansion, s=3.5%) was independently re-checked and retained — it's
a legitimate matched-*family* separation from cfg043 (different rattle
presence, d_shape≠0, ~0.27-0.28 combined distance, the ordinary tolerated
pattern), not a collapse.

**Final replacement:** `cfg299_Al3Ni_volume_rattle_expansion`, s=3.6% —
swept 3.1%-3.9% in 0.1-point steps inside the same 3.0%→4.0% gap for a
volume_rattle_expansion placement that (a) clears 0.3269 against all 15
TRAIN rungs and (b) is NOT descriptor-degenerate (d_vol, d_strain both
≪1e-3, verified explicitly, not assumed) against cfg043, cfg109, cfg110,
cfg115, *or* cfg297. 3.3%/3.4%/3.6%/3.7% all qualified (3.1%/3.2%/3.8%/3.9%
fail the TRAIN-distance threshold; exactly 3.5% is the cfg043 collision);
3.6% has the best margin (min_dist_TRAIN=0.4244) and was picked. Sealed
pair is now `{cfg297, cfg299}`. Full verification:
`configs/ROUND285_SEALED_PAIR_REVISION2_STATUS.md`; retirement record
(both retirements): `data/al3ni_remediation_v1/round285_sealed_retirement_log.txt`;
current policy: `configs/AL3NI_ROUND285_SEALED_CONFIRMATION_POLICY.txt`.
**DFT has not been run for cfg297/cfg299 yet** — geometry and QE input
only.

**Also resolved this pass: cfg043's exact strain.** An earlier informal
note in this project said "≈3.56%" (a rough trace/3 approximation, never
solved precisely). The correct value, confirmed two independent ways —
the frozen `ni_al_dataset100_blind_holdout_manifest.csv` row
(`requested_strain=0.035`) and inverting the actual DFT-relaxed cell's
Green-Lagrange trace via `s = sqrt(1+trace/1.5)-1` — is **exactly 3.5000%**.
The 3.56% figure was never a computed value; it should not be reused
anywhere else in this project's records.

*(Original text, kept for history — describes the never-executed
500-structure-round plan):* `cfg109_Al3Ni_iso_expansion` and
`cfg110_Al3Ni_volume_rattle_expansion` (the remediation branch's
CONFIRMATION_HOLDOUT pair) have their energy/forces/stress permanently
sealed until a final candidate model is frozen. Geometry (cell,
positions) may be read for design/screening at any time — labels may not,
under any circumstance, until unsealing. They are unsealed **exactly
once**, immediately before LAMMPS-readiness is assessed, against the
**final model trained on the full ~500-structure dataset** — never
against any intermediate checkpoint. Full statement:
`configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`.

## 6. Training approach

**Foundation model choice, documented here for the first time (2026-08-16):**
every training run in this project uses `mace-matpes-pbe-0` (checkpoint
`MACE-matpes-pbe-omat-ft.model`, 79.5 MB; medium-scale architecture --
`128x0e+128x1o` hidden irreps, 2 layers, correlation order 3, 6.0 Angstrom
cutoff -- though the model string itself carries no explicit size suffix,
unlike `medium-mpa-0`). This was **not the original plan**: the first Pilot-25
proposal (`configs/pilot25_mpa_lora_v1.yaml`) specified `medium-mpa-0`
(MACE-MPA-0), and `configs/RESUME_AUDIT.txt` (2026-08-11 07:09 UTC)
explicitly recommended launching that exact model as the next action. 28
minutes later, `configs/pilot25_matpes_pbe_lora_v1.yaml` appeared using
`mace-matpes-pbe-0` instead, and every run since (Pilot-25, Dataset-100,
combined-113/127/129) has silently inherited that choice -- **with no
written rationale anywhere in the project until this entry**. The switch
was real and consistent, just never explained in writing; `README.md`'s
"Pilot 25 model" section incorrectly said "MACE-MPA-0 medium" for the
matpes-pbe-0 artifacts until this same update corrected it.

The most defensible technical reason, reconstructed now rather than found
on record: this project's DFT reference labels all come from Quantum
ESPRESSO with the **PBE** exchange-correlation functional (Section 2).
MACE-MATPES-PBE-0 was itself trained on PBE-level reference data, while
MACE-MPA-0 was trained on a Materials Project + Alexandria mixture at a
different DFT setting. Matching the foundation model's training
functional to this project's own labeling functional is a sound reason to
prefer MATPES-PBE-0 for LoRA fine-tuning consistency -- but treat this as
a plausible reconstruction, not a decision anyone in this project actually
recorded at the time.

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

**Reserved-set (TEST+BLIND_HOLDOUT) evaluation, run for the first time
since Dataset-100 (2026-08-16):** every checkpoint between Dataset-100 and
combined-211 had only ever been measured via the 2-point non-sealed
interim gate — a deliberately weak progress signal, not a real
generalization check. `scripts/evaluate_combined211_reserved_set.py`
(reused `evaluate_dataset100_final.py`'s exact method) ran the actual
20-structure reserved set against combined-211 vs. the old dataset100
model, with a leakage check (0/20 reserved ids found in TRAIN, verified
not assumed). Result: BLIND_HOLDOUT relative-energy RMSE improved by
-0.855 meV/atom (TEST barely moved, -0.012) — real evidence the dataset
work through round300 was still improving generalization, not padding
already-saturated coverage. This directly informed the decision to keep
extending (round212/213/214) rather than stopping at combined-211.
**Caveat:** this evaluation was only ever run once, against combined-211
— it has not been re-run against combined-218. Do not assume the same
improving-not-plateaued conclusion still holds without re-running it.

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
- **Round300 (cfg146-cfg272, 82 configs, 10 pods): the actual ~300-structure
  round.** Scoped as a full factorial gap-fill (`scripts/scope_round300_design.py`):
  every phase x deformation-family x direction x sign x rattle-state combo
  with zero TRAIN members -- 128 candidates found, of which 82 survived
  gates (`scripts/design_round300_batch.py`). Split 3/2/2/... across 10
  pods by LPT (Longest Processing Time) time-balancing
  (`scripts/assign_round300_pods.py`), using an empirical (phase, rattle)
  timing model built from every real QE run on record. 2 pods ran on this
  session's GPU; the user launched the other 8 on separately-rented pods
  sharing the same network volume -- confirmed via `runpodctl get pod`
  that only 1-2 real GPUs existed at various points this session (the
  "pod01"-"pod10" naming in this project was historically just a tmux-
  session label on one machine, not real parallel infrastructure, until
  the user actually provisioned more). All 10 pods completed, 82/82, 0
  failures. Integrity-verified, extracted, outlier-screened, merged into
  **combined-211** (TRAIN 173/VALIDATION 18), trained
  (`al3ni_combined211_lora_v1`: force RMSE 5.6->5.1, stress 2.1->1.8
  meV/A^3 vs combined-129), interim-gated (cfg043 -0.21, cfg115 -0.65
  meV/atom, both improved -- this probe is directly relevant this round
  since round300 nearly doubled Al3Ni's own TRAIN depth, 17->44).
- **Coverage audit for combined-211**
  (`scripts/update_full_coverage_audit_combined211.py`): 14 of 20
  EXTRAPOLATION flags fully closed, zero remaining Tier-1 (zero-support)
  buckets, zero new/unexpected flags. 6 flags remained open (cfg042 Al3Ni
  shear, cfg074 Al3Ni2 shear, cfg059/cfg061 Al3Ni5 shear+rattle, plus 2
  more later found to be a miscount -- see below).
- **Reserved-set evaluation (2026-08-16): first real generalization check
  since Dataset-100.** `scripts/evaluate_combined211_reserved_set.py`
  measured combined-211 against the full 20-structure TEST+BLIND_HOLDOUT
  set (leakage-checked: 0/20 in TRAIN) vs. the old dataset100 model.
  BLIND_HOLDOUT relative-energy RMSE improved -0.855 meV/atom (TEST barely
  moved, -0.012) -- real evidence the work through round300 was still
  improving generalization, not chasing diminishing returns. This directly
  justified continuing to round212/213/214 rather than stopping. (Caught
  and fixed a units-display bug during this run: stress values were
  correctly computed in GPa but mislabeled/rescaled as meV/A^3 in the
  printed report -- data was right, only the display was wrong.)
- **Round212/213/214 (cfg273-cfg282, 7 configs, pods A/B/C): closes the
  final 4 EXTRAPOLATION flags + AlNi's 2 remaining thin buckets.** Real
  iteration required, not a first-try success: closing cfg042 (Al3Ni
  shear) and cfg074 (Al3Ni2 shear) on their original axis (shear_xz) kept
  matching round300's own `shear_rattle_xz` siblings as "nearest," getting
  closer rather than farther as magnitude increased (a partial matched-
  strain descriptor blind spot, see Section 4) -- fixed by switching to
  `shear_xy` (no rattled sibling there; the coverage bucket pools all
  axes) rather than implementing the real Gate (c) exemption. Al3Ni2's
  minimum-passing magnitude was explicitly swept (not guessed): -0.030
  and -0.038 failed, -0.045 passed. A duplicate-purpose candidate
  (`cfg274` at -0.06, an earlier pass at the same Al3Ni2 gap) was
  identified and retired once the -0.045 minimum was found -- structure/
  QE files deleted, manifest row removed, retirement documented rather
  than silently dropped. AlNi's 2 thin buckets (shear n=1->3,
  volume_rattle n=2->3) closed cleanly with axes chosen to avoid the same
  collision. All 7 DFT'd across 3 pods (3/2/2 split, time-balanced),
  integrity-verified, extracted, outlier-screened (2 flags, both
  deliberately-pushed rattle candidates, expected), merged into
  **combined-218** (TRAIN 180/VALIDATION 18) -- current dataset.
  Training/interim-gate/coverage-audit for combined-218 launched same
  session; see the Update log for final numbers once complete.
- Not yet done: the future 500-structure round (out of scope until
  explicitly taken up, needs a real reserved-set evaluation re-run to
  justify sizing, not a round-number target); re-confirming the "zero
  EXTRAPOLATION flags" projection with a formal combined-218 coverage
  audit rather than the round212/213/214 design-time projection alone;
  implementing the actual Gate (c) matched-strain-role exemption (worked
  around twice now via axis-switching, never fixed at the source).

## 8. LAMMPS/MACE deployment validation (Stage 9)

Validates the trained MACE model (`al3ni_combined227_lora_v1`, LoRA
fine-tune) in its actual deployment environment -- LAMMPS via the ML-IAP
unified interface -- rather than only through the ASE-based evaluation
pipeline used in Sections 5-7. Four sub-stages (A-D), all complete as of
2026-08-19. Full detail in `configs/LAMMPS_STAGE_{A,B,C,D}*STATUS*.txt`
and `configs/LAMMPS_MLIAP_KOKKOS_BUILD_STATUS.txt`.

**Build/loading note**: only the Kokkos/CUDA LAMMPS build
(`tools/lammps/install/mliap_kokkos`) can run this model at all -- the
non-Kokkos build's `MLIAPDataPy` lacks the forward_exchange/
reverse_exchange ghost-atom methods MACE's ML-IAP path calls
unconditionally. Model loading requires the Python interface
(`lammps.mliap.load_unified_kokkos`) to run before `pair_style mliap
unified EXISTS` is parsed -- confirmed empirically (not assumed) that a
bare `lmp -in <script>` fails with "ValueError: No unified model loaded"
on that exact command sequence, so every Stage A-D run goes through the
Python driver path, never a standalone `.in` script.

- **Stage A (single-point agreement)**: LAMMPS `pair_style mliap unified`
  vs. plain ASE/MACE, same geometry/weights/dtype (float64) -- energy
  agreement ~1e-12 eV (machine precision), max force diff ~1e-14
  eV/Angstrom. Confirms the export/integration path itself introduces no
  numerical discrepancy.
- **Stage B (5-phase relaxation)**: `box/relax tri` + minimize from the
  DFT relaxed geometry, all 5 phases. 5/5 completed, 5/5 symmetry
  preserved. Max volume/atom error vs DFT: 0.216% (Al3Ni5). Al3Ni5 also
  showed the largest lattice-angle deviation: alpha relaxes to 98.279 deg
  vs DFT's 96.478 deg (+1.87%).
- **Stage C (elastic constants, all 5 phases)**: finite-difference
  stress-strain (delta=0.75%, all 6 Voigt modes, both signs) at each
  phase's own LAMMPS zero-stress cell. Born-stable (all eigenvalues > 0):
  5/5. AlNi3 (Ni3Al, L1_2): C11/C12/C44 within ~8%/1%/5% of experimental
  literature. AlNi (B2): C11 -26.06% vs a DFT-literature reference (C12
  +5.90%, C44 -6.07%) -- an open, unexplained gap despite AlNi being one
  of only 2 phases with any literature reference at all. Al3Ni, Al3Ni2,
  Al3Ni5: **no elastic reference exists** (DFT or literature) -- reported
  as model predictions only, not validated.
- **Stage D (MD stability, all 5 phases)**: 300 K, 1 fs timestep, 15 ps
  NVT (Nose-Hoover) then 15 ps NPT (full triclinic barostat, ambient
  pressure), starting from each phase's own Stage B zero-stress cell.
  5/5 dynamically stable -- no NaN, no lost atoms, no runaway drift (all
  alpha/beta/gamma and volume drift stayed well under the CONCERN/
  INSTABILITY thresholds defined in `scripts/analyze_md_stability.py`).
- **Stage D-2 (supercell MD for the 3 small-cell phases)**: AlNi, AlNi3,
  and Al3Ni2 rebuilt as ~100-200 atom supercells (AlNi 128 = 4x4x4 of the
  2-atom primitive; AlNi3 108 = 3x3x3 of the 4-atom primitive; Al3Ni2 135
  = 3x3x3 of the 5-atom primitive), each replicated from that phase's own
  zero-stress relaxed primitive cell (translational symmetry means a
  zero-stress primitive cell replicates to an exact zero-stress
  supercell, so no separate supercell-scale relax was needed). Single-
  stage 15 ps NPT @ 300 K, 1 fs (no separate NVT stage this time), with
  per-species (Al vs Ni) MSD tracked via `compute msd`. All 3 STABLE, no
  flags. This resolves the small-cell statistics limitation recorded
  below after Stage D: instantaneous temperature fluctuation dropped from
  Stage D's ~82%-relative (AlNi, 2 atoms, 3 degrees of freedom) to ~7-8%
  relative (AlNi 301+/-23 K, AlNi3 303+/-25 K, Al3Ni2 300+/-22 K at ~130
  atoms) -- matching equipartition theory almost exactly, confirming
  beta/gamma drift is now real signal, not noise: 0.56-0.74 deg max
  drift across all 3 phases (vs Stage D's statistically meaningless 2-8
  deg swings on the primitive cells). Per-species MSD (Al and Ni
  separately) stayed at 0.01-0.02 Angstrom^2 with flat/slightly negative
  back-half slopes on all 3 phases -- consistent with ordinary thermal
  vibration about lattice sites, not diffusion or melting. Runtime
  observation (not a physics result, but useful for sizing any future
  production MD): all 3 phases took ~11-12 minutes regardless of atom
  count (108-135) at this scale -- GPU kernel-launch-bound, not
  atom-count-bound, so the naive linear-in-atoms cost projection made
  before launching overestimated the two larger phases. Full detail:
  `configs/LAMMPS_STAGE_D2_SUPERCELL_MD_STATUS.txt`.

**Limitations (explicit -- recorded as open issues, not resolved unless
stated, not conclusions):**
- **Small-cell statistical artifact: RESOLVED by Stage D-2 (see above).**
  AlNi (2 atoms), AlNi3 (4 atoms), and Al3Ni2 (5 atoms) originally had too
  few atoms for their Stage D beta/gamma drift figures to be
  statistically meaningful -- e.g. AlNi's instantaneous NVT temperature
  swung ~1-1140 K sample-to-sample (3 degrees of freedom -> ~82% relative
  fluctuation expected by equipartition, confirmed against the raw thermo
  trace rather than merely inferred; total energy stayed conserved to
  ~3e-5 relative over the same window, so this was statistics, not a
  thermostat fault). Supercells (Stage D-2) now give all 3 phases
  statistically meaningful shear-stability numbers alongside Al3Ni5.
- **Stage D-2 thermal expansion is a crude two-point estimate, not a
  measured CTE**: each phase's linear CTE was derived from exactly two
  points -- the 0 K relaxed cell and the 15 ps/300 K NPT volume/atom
  average -- not a temperature sweep with multiple T points fit to a
  curve, which is how a real thermal expansion coefficient is normally
  measured/computed. The reported 12-15e-6/K numbers are a single finite-
  difference slope, sensitive to exactly these two endpoints; do not treat
  as equivalent in rigor to Stage C's finite-difference elastic constants
  (which used 6 strain modes x 2 signs x symmetrized central differences).
- **AlNi's "verified" literature CTE is not a valid comparison**: the one
  live-search-verified number (16.0e-6/K) is a NiAl-Mo EUTECTIC COMPOSITE
  average measured perpendicular to the fiber direction over RT-800C --
  not pure single-crystal stoichiometric B2 NiAl, and not measured over
  this run's 0-300 K range. The model's -4.1% deviation from that number
  is not evidence of accuracy or inaccuracy against pure NiAl. The
  alternative value used for AlNi (13.0e-6/K, giving +18.0% deviation) is
  RECALLED, not independently verified this session -- the primary source
  (Miracle 1993 NiAl review) was paywalled/bot-blocked when fetched.
- **AlNi3's +1.1% literature agreement rests on an unverified recalled
  value**: the reference (12.5e-6/K) is RECALLED domain knowledge, not a
  session-verified citation -- a live web search found only an unsourced
  aggregator paraphrase, and the one directly on-topic primary source
  found (a 1989 IOPscience Ni3Al thermal-expansion paper) was blocked by
  an anti-bot redirect before its content could be retrieved. The close
  numeric agreement should not be read as confirmed literature validation.
- **Net (Stage D-2 thermal expansion): all 3 phases are effectively
  UNVALIDATED against literature**, not confirmed accurate -- AlNi's
  comparison is to the wrong kind of reference (composite, not pure
  crystal), AlNi3's is to an unverified recalled number, and Al3Ni2 has no
  reference at all (same convention as Stage C). What IS established is
  only that the magnitude is physically plausible for a metallic
  intermetallic (1.0-1.4% volumetric expansion 0->300 K, 12-15e-6/K
  linear CTE) -- not that it matches a verified reference.
- **Al3Ni5 alpha displacement**: this model's own energy minimum sits at
  alpha=98.28 deg vs. DFT's 96.478 deg, costing +0.873 meV/atom when
  constrained back to the DFT angle (Stage B diagnostic,
  `configs/LAMMPS_STAGE_B_AL3NI5_ALPHA_DIAGNOSTIC.txt`) -- a real feature
  of the trained model's PES, not a relaxation artifact (the constrained
  run's residual force is far higher than the unconstrained run's).
  Independently corroborated by Stage C: Al3Ni5's C44=33.15 GPa is ~3x
  softer than its own C55/C66 (~98-102 GPa) and softer than every other
  phase's shear constants -- same physical direction (yz/alpha-tilt), two
  independent observables agreeing. Whether alpha~98.3 deg is closer to
  or further from the TRUE (DFT) minimum than 96.5 deg is NOT
  established -- would require a new DFT relaxation or single-point at
  the shifted geometry (out of scope so far).
- **AlNi C11 -26% gap**: remains unexplained and unresolved. AlNi is one
  of only 2 phases (with AlNi3) that have any literature elastic
  reference at all, so this is the project's one directly-checkable
  elastic-constant discrepancy, and it is a large one.
- **3 of 5 phases have zero elastic-constant reference**: Al3Ni, Al3Ni2,
  and Al3Ni5's Stage C Cij values are model predictions only -- no DFT or
  literature comparison exists for any of them. Born-stability and
  internal consistency (symmetry, eigenvalue positivity) were checked;
  quantitative accuracy was not.

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
- 2026-08-16 (same day, later): Scoped and executed round300 (the actual
  ~300-structure round, full factorial gap-fill, 82/128 candidates
  survived gates, 10 pods -- 2 local + 8 user-launched on separately
  rented GPUs). Merged into combined-211, trained, interim-gated. Ran the
  first reserved-set (TEST+BLIND_HOLDOUT) evaluation since Dataset-100 --
  real evidence of continued improvement, not a plateau. Updated the
  coverage audit: 14/20 flags closed, 6 remained. Designed and DFT'd
  round212/213/214 (7 configs, pods A/B/C) closing 4 of those 6 flags
  (cfg042, cfg074, cfg059, cfg061) + AlNi's 2 thin buckets, requiring real
  iteration (matched-strain axis collision found and worked around,
  documented in Section 4). Retired a duplicate-purpose candidate (cfg274,
  superseded by a swept minimum) with a documented reason rather than a
  silent drop. Merged into combined-218 (current). Re-ran the coverage
  audit immediately after (does not depend on the trained model) --
  **caught an incorrect "zero flags project-wide" projection** written
  earlier in this same update: 2 flags remain open (cfg041 Al3Ni uniaxial,
  cfg107 Al3Ni volume_rattle), neither ever targeted this round. Corrected
  in Section 3/7 and README.md rather than left standing. Training/
  interim-gate for combined-218 launched in background, detached (PPID=1,
  confirmed survives session end); see the next entry for final numbers.
- 2026-08-17/18: Designed and DFT'd round220 (cfg283/cfg284, 2 configs,
  closing the last 2 open EXTRAPOLATION flags — cfg041 Al3Ni uniaxial_z,
  cfg107 Al3Ni volume_rattle — via the same swept-multiplier convention as
  round212). Merged into **combined-220** (TRAIN 182 / VALIDATION 18) —
  zero EXTRAPOLATION flags project-wide for the first time, re-run not
  projected. Same-day decision (`SESSION_STATE_AL3NI_EXPANSION_DESIGN.md`
  Section 13): **stop expansion at ~220 structures** — VALIDATION energy
  RMSE had gone flat/noisy across 129->211->218 despite TRAIN growing
  2.4x. The original 110->300->500-structure->LAMMPS roadmap is
  superseded; there was never a discrete 300- or 500-structure round
  (round300's ~82 configs served that gap-fill role at the combined-211
  stage instead). combined-220 became the **final pre-unsealing
  checkpoint**. Ran the reserved-20 evaluation against it
  (`scripts/evaluate_combined220_reserved_and_probes.py`) and derived the
  final numeric acceptance threshold from real data for the first time —
  **2.3865 meV/atom**, the max of the 19 genuinely-independent reserved
  points (cfg060), explicitly excluding cfg043 as design-contaminated
  (steered by 5+ remediation rounds' worth of "drive this number down"
  design decisions — indirect, not gradient, leakage). One same-day
  self-correction on record: an initial lock at 3.0402 (max *including*
  cfg043) was caught and fixed before any unsealing occurred — see
  `configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`'s own correction
  history. Then ran the single, designated, irreversible unsealing
  (`scripts/unseal_cfg109_cfg110_final_evaluation.py`) — **FAIL**:
  cfg109 |error|=3.767 meV/atom (+1.38 over threshold), cfg110
  |error|=3.732 (+1.35 over). Full detail: Section 5.
- 2026-08-18: Before designing any remediation for the FAIL above, ran two
  falsification checks rather than assuming "more data" was the answer.
  Seed-variance (identical data/hyperparameters, seed 20260811 vs 812 vs
  813): cfg109/cfg110 seed-noise floor ≈0.43 meV/atom — the FAIL margin
  (~1.35-1.38) is ~3x that, robust to reseeding on the fixed threshold,
  though the *threshold itself* (a single-seed single-point reserved-20
  max) shifts ~0.81 meV/atom and changes which config anchors it across
  the same 3 seeds — a real fragility, noted, not acted on (threshold is
  explicitly locked, not to be revised post hoc). Capacity test (LoRA
  rank 4 vs 8 vs 16, seed fixed at 20260811): rank 8 showed no
  distinguishable effect (within seed noise); rank 16 made cfg109/cfg110
  measurably *worse* (~+0.92-0.93 meV/atom, beyond the noise floor, wrong
  direction) — consistent with mild overfitting at fixed data size, not a
  relieved capacity ceiling. **Capacity hypothesis rejected**, which is
  what justified the next step as a data-density fix rather than a
  bigger-rank retrain. Full detail: Section 5.
- 2026-08-18 (same day, later): Designed round285 — densify the Al3Ni
  high-expansion regime (+3.0%..+5.0%, iso_expansion + volume_rattle_
  expansion), the region diagnosed as thin (only 3 TRAIN rungs — s=2.0%,
  3.0%, 4.6% — across the +2%..+5.6% span; the 3.0%->4.6% gap is exactly
  where cfg109/cfg110, s=4.0%, used to sit before being consumed).
  Design-only, no DFT, no training. Key policy change: gate (b) leakage
  no longer treats cfg109/cfg110 as protected (they're consumed) — uses
  the live Al3Ni RESERVED population instead (same substitution
  round220 already established). **Caught and fixed a gate-design error
  before it produced a bad result, not after**: gate (a) was initially
  implemented as a blanket TRAIN-vs-TRAIN reject (copied verbatim from
  round220's script), which rejected all 10 grid candidates —
  re-reading `EXPANSION_BATCH_DESIGN_POLICY.md` gate (c) confirmed this
  was wrong: "TRAIN-vs-TRAIN similarity at different strain values is an
  efficiency advisory only — informative, never a rejection reason,"
  exactly because a *deliberately dense* grid is supposed to sit close to
  existing TRAIN at neighboring strain values. Fixed by making gate (a)
  advisory-only for same-role comparisons and moving true-duplicate
  detection to gate (c), using a numerically calibrated combined-distance
  epsilon (1e-3 — true duplicate measured at ~1e-7, closest legitimate
  different-strain neighbor at ~0.097, closest legitimate matched-strain
  pair at ~0.28) rather than the exact-byte geometry hash, which proved
  fragile to floating-point reconstruction noise. Final result: 7/10
  densification candidates kept (cfg287-cfg290, cfg292-cfg294 — cfg285
  rejected as an exact duplicate of existing cfg029 at s=3.0%; cfg286/
  cfg291 rejected for leakage against cfg043, which sits at s≈3.56% and
  blocks the entire 3.5% rung for both families — a genuine, gate-derived
  gap, not a design oversight). Also designed and sealed 2 new
  CONFIRMATION_HOLDOUT structures (cfg295 iso_expansion s=3.75%, cfg296
  volume_rattle_expansion s=4.25%, both off-grid interpolation tests) to
  replace cfg109/cfg110's vacated role — both pass all gates, DFT not yet
  run. Proposed: TRAIN 182->189 (+7), VALIDATION unchanged at 18. Not yet
  done: DFT for the 7 TRAIN candidates or the 2 sealed structures,
  merging into a combined-227 dataset, retraining. Full detail: Section 5,
  `configs/ROUND285_HIGH_EXPANSION_DENSIFY_DESIGN_STATUS.md`.
- 2026-08-18 (same day, later still): **Design verification caught the
  sealed pair above was compromised before any DFT was spent on it.** A
  dedicated reverse-leakage check — distance from each of the 7 approved
  TRAIN candidates to cfg295/cfg296, which the original round285 script
  never computed (it only checked the sealed pair against the RESERVED
  population and a tight duplicate epsilon, never against the newly-
  approved TRAIN candidates at leakage scale) — found min distance
  0.2421 (cfg287 @ +4.0% to cfg295 @ +3.75%), below both the policy-cited
  0.734644 and round285's own fresh 0.3269. Retired cfg295/cfg296 (never
  DFT'd, nothing lost) and replaced with `cfg297_Al3Ni_iso_expansion` /
  `cfg298_Al3Ni_volume_rattle_expansion`, both s=3.5%, placed in the one
  interval (3.0%->4.0%) round285 could not densify to 0.5-point spacing
  (blocked by leakage against cfg043 at s=3.5000%) — the only interval
  wide enough for genuine seal isolation. Verified against all 15 TRAIN
  rungs (8 existing + 7 new); both clear the regime-correct fresh
  threshold by 47-53%. Root cause recorded in Section 5: a sealed
  interpolation point cannot be both inside a densified region and
  isolated from it — density and seal-isolation are mutually exclusive
  in the same interval. Also quantified, on request, the cost of
  protecting cfg043 rather than overriding it: the 3.0%->4.0% interval
  stays a single 1.0-point step (cfg286 missed the fresh threshold by
  only 0.0047 -- essentially marginal; cfg291 missed by 0.1389 -- a real
  block) instead of splitting into two 0.5-point steps — decision left
  unchanged, cost quantified as requested. Full detail: Section 5,
  `configs/ROUND285_SEALED_PAIR_REVISION_STATUS.md`,
  `data/al3ni_remediation_v1/round285_sealed_retirement_log.txt`.
- 2026-08-18 (same day, third pass): **cfg298 itself retired — a more
  serious problem than cfg295/cfg296's leakage.** cfg298 (volume_rattle_
  expansion, s=3.5%) is descriptor-degenerate with cfg043 (d_vol/d_strain
  ≈1e-8/1e-9, same family, same strain) — and cfg043 is not an ordinary
  holdout, it is the FEEDBACK PROBE that steered 5+ remediation design
  rounds. A seal that is a clone of the feedback probe inherits its
  indirect design contamination and cannot serve as an independent test
  — the previous entry's "test redundancy, not leakage" framing was
  correct in general but wrong applied to a contaminated probe
  specifically; corrected same day, not left standing. cfg297
  (iso_expansion, s=3.5%) re-verified and retained — legitimate matched-
  family separation from cfg043, not a collapse. Swept
  volume_rattle_expansion placements 3.1%-3.9% in the same 3.0%->4.0% gap
  for one that clears the 0.3269 TRAIN threshold AND is non-degenerate
  against cfg043/cfg109/cfg110/cfg115/cfg297 simultaneously — found
  `cfg299_Al3Ni_volume_rattle_expansion` at s=3.6% (best margin among 4
  qualifying candidates). Also resolved a standing loose approximation:
  cfg043's strain was informally noted as "≈3.56%" in an earlier pass —
  confirmed exactly 3.5000% from the frozen dataset100 manifest
  (`requested_strain=0.035`) and independently from geometry inversion;
  3.56% was never a computed value and should not be reused. Sealed pair
  is now `{cfg297, cfg299}`. Full detail: Section 5,
  `configs/ROUND285_SEALED_PAIR_REVISION2_STATUS.md`.
- 2026-08-19: **Stage 9 (LAMMPS/MACE deployment validation) complete.**
  Stage A (single-point, ~1e-12 eV agreement) through Stage D (5-phase
  15 ps NVT + 15 ps NPT MD stability, all 5 dynamically stable) all done
  this session, using the Kokkos/CUDA LAMMPS build and the Python
  mliappy interface -- the only verified-working model-loading path; a
  bare `lmp -in` cannot load this model (confirmed empirically, not
  assumed). Al3Ni5 (softest C44=33.2 GPa) run first as the known risk,
  confirmed stable, then the other 4 phases run and merged into the same
  report. See Section 8 for full numeric results and four explicit
  limitations recorded as open issues, not resolved here: the Stage D
  small-cell statistical artifact for AlNi/AlNi3/Al3Ni2, the Al3Ni5
  alpha/C44 PES feature (real but not verdict on DFT-accuracy), the
  unexplained AlNi C11 -26% gap, and the 3 phases (Al3Ni, Al3Ni2, Al3Ni5)
  with no elastic-constant reference at all.
- 2026-08-19 (same day, later): **Stage D-2 (supercell MD for the 3
  small-cell phases) complete.** AlNi (128 atoms), AlNi3 (108), Al3Ni2
  (135) -- each a supercell of that phase's own zero-stress relaxed
  primitive cell, single-stage 15 ps NPT @ 300 K, 1 fs, with per-species
  MSD. All 3 STABLE. Resolves the small-cell statistical-artifact
  limitation recorded right after Stage D: temperature fluctuation
  dropped from ~82% relative (AlNi's 2-atom primitive cell) to ~7-8%
  relative, matching equipartition theory, so beta/gamma drift
  (0.56-0.74 deg) is now real signal. MSD stayed at 0.01-0.02 Angstrom^2
  with flat back-half slopes on all 3 -- vibrational, not diffusive.
  Runtime was ~11-12 min/phase regardless of atom count (GPU
  kernel-launch-bound at this scale, not atom-count-bound) -- noted for
  sizing future production MD, not a physics result. Added 4 new
  explicit limitations rather than presenting the thermal-expansion
  numbers as validated: the CTE is a crude two-point (0 K vs 300 K)
  estimate, not a temperature-swept measurement; AlNi's one
  live-verified literature number is a NiAl-Mo composite average, not
  pure B2 NiAl, so the comparison is not valid on its own terms; AlNi3's
  close (+1.1%) agreement rests on a recalled, not session-verified,
  literature value (primary source blocked); and net, all 3 phases
  remain effectively UNVALIDATED against literature on thermal
  expansion -- only the physical plausibility of the magnitude (1.0-1.4%
  volumetric, 12-15e-6/K linear) is established. See Section 8 for full
  detail; `configs/LAMMPS_STAGE_D2_SUPERCELL_MD_STATUS.txt` for raw
  numbers.
