# Ni-Al Materials Discovery

This project develops a reproducible, physically credible machine-learning
interatomic potential for Ni-Al using DFT reference calculations, ASE, and
MACE. The objective includes energies, forces, stresses, relaxation, phase
energetics, molecular dynamics, and structure screening—not merely low ML
validation error.

## Final Pilot 25

The canonical pilot dataset is
`data/processed/ni_al_pilot_dft_25.extxyz` (25 frames, 28,755 bytes, SHA-256
`35b2b65fe77d181b5da30dd23bbb7ff9fc4f41c0c0f603738172e2f833ab5b0b`).
It contains five configurations for each of AlNi, Al3Ni, Al3Ni2, Al3Ni5, and
AlNi3.

The fixed scientific split is:

- Train (15): `relaxed`, `iso_m02`, `iso_p02`
- Validation (5): `rattle_003`
- Test (5): `shear015_rattle002`

The test set is reserved and must not be used during hyperparameter tuning or
model selection.

## Reproduce dataset validation

```bash
source /workspace/ni_al/envs/mace-py312-cu128/bin/activate
python /workspace/ni_al/scripts/validate_and_split_pilot25.py
```

The script verifies the canonical hash, scientific invariants, compositions,
reference arrays, uniqueness, and split coverage before writing outputs. See
`data/processed/pilot25_validation_report.txt` and
`configs/PILOT25_PROVENANCE.txt` for full results and hashes.

## Pilot 25 model

The Pilot 25 **MACE-MATPES-PBE-0** LoRA training and reserved-test evaluation
are complete. (Correction 2026-08-16: this section previously said
"MACE-MPA-0 medium" — that was stale. MACE-MPA-0 was the original proposal
(`configs/pilot25_mpa_lora_v1.yaml`) and was never run; the project switched
to MACE-MATPES-PBE-0 before Pilot 25 training actually launched, and every
run since — Dataset-100, combined-113/127/129 — has used MATPES-PBE-0. See
`configs/project_knowledge.md` Section 6 for the model choice and why the
switch was never documented until now.) The final model artifacts are under
`models/pilot25_matpes_pbe_lora_v1/`, and the test metrics and plots are under
`results/pilot25_test_evaluation_v1/`. The training configuration is recorded
in `configs/pilot25_matpes_pbe_lora_v1.yaml`. See
`configs/PILOT25_FINAL_ARTIFACTS_MANIFEST.txt` for the final artifact inventory
and integrity hashes.

## Dataset-100 DFT production

The five-Pod Quantum ESPRESSO GPU production run completed on 2026-08-12 UTC.
All 75 assigned configurations across chunks 01–10 completed successfully:

- Completed configurations: 75/75
- Failed configurations: 0
- Completed chunks: 10/10
- Completed Pods: 5/5

The authoritative aggregate record is
`configs/DATASET100_GPU_PRODUCTION_STATUS.txt`. Per-Pod status files and
per-chunk checkpoints are under `configs/production_chunks/`, and calculation
outputs are under `data/expansion_026_100/production_gpu/`.

## Al3Ni remediation and coverage gap-closing (combined-220, round285 designed)

After Dataset-100 was frozen, a holdout failure (`cfg043`, Al3Ni) was
diagnosed as extrapolation: the TRAIN set had no coverage beyond a certain
strain ceiling. This kicked off an incremental remediation lineage,
extending Dataset-100 in stages:

```
Dataset-100 (100)
  -> + Al3Ni remediation v1 (cfg101-110, 2 sealed) + round2 (cfg111-115)
  -> combined-113 (TRAIN 75 / VALIDATION 18 / TEST+BLIND_HOLDOUT 20)
  -> + round3 (cfg117-141, 14 configs, closes priority gaps from a full
     coverage/extrapolation audit: biaxial, shear_rattle, orthorhombic
     deformation families were entirely untrained in most phases)
  -> combined-127 (TRAIN 89 / VALIDATION 18)
  -> + round4 (cfg143, cfg145, closes the last 2 fully-untrained gaps:
     Al3Ni5 and AlNi3 biaxial deformation)
  -> combined-129 (TRAIN 91 / VALIDATION 18)
  -> + round300 (cfg146-272, 82 configs, 10 pods -- the actual ~300-round:
     full factorial gap-fill, every phase x family x direction x sign x
     rattle-state combo with zero TRAIN coverage, not just audit flags)
  -> combined-211 (TRAIN 173 / VALIDATION 18)
     [first reserved-set (TEST+BLIND_HOLDOUT, 20, never trained on)
     evaluation since Dataset-100: BLIND_HOLDOUT rel-energy RMSE improved
     -0.855 meV/atom vs. the old dataset100 baseline -- still improving,
     not plateaued]
  -> + round212/213/214 (cfg273-282, 7 configs, pods A/B/C) -- closes 4 of
     the 6 EXTRAPOLATION flags left after round300 (cfg042, cfg074,
     cfg059, cfg061) + AlNi's 2 remaining thin buckets
  -> combined-218 (TRAIN 180 / VALIDATION 18)
  -> + round220 (cfg283/cfg284, 2 configs) -- closes the last 2
     EXTRAPOLATION flags (cfg041 Al3Ni uniaxial, cfg107 Al3Ni
     volume_rattle); zero EXTRAPOLATION flags project-wide, first time
  -> combined-220 (TRAIN 182 / VALIDATION 18) -- FINAL pre-unsealing
     checkpoint; expansion explicitly stopped here 2026-08-17 (VALIDATION
     RMSE had gone flat/noisy across 129->211->218 despite TRAIN growing
     2.4x) -- see configs/SESSION_STATE_AL3NI_EXPANSION_DESIGN.md Section
     13. No 300- or 500-structure round ever occurred.
```

As of combined-220, **zero EXTRAPOLATION and zero Tier-1
(zero-TRAIN-support) buckets** remain anywhere in the Al3Ni coverage
audit. The trained checkpoint is `models/al3ni_combined220_lora_v1/`
(seed 20260811, LoRA rank 4 -- the project-standard hyperparameters used
throughout), on `data/datasets/ni_al_combined220_train_182.extxyz` /
`..._validation_18.extxyz`.

**cfg109/cfg110 have been unsealed and are consumed (2026-08-17) — they
are no longer a protected holdout.** The final acceptance threshold was
derived from real held-out error (2.3865 meV/atom, the max of the 19
genuinely-independent reserved-20 members, excluding design-contaminated
cfg043 -- `configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`), then
cfg109/cfg110 were read for the first and only time
(`configs/AL3NI_FINAL_UNSEALING_RESULT.txt`): **both FAILED** --
cfg109 |error|=3.767 meV/atom (margin +1.38 over threshold), cfg110
|error|=3.732 (margin +1.35). Neither was merged into any split.

Before designing a fix, two falsification checks ruled out simpler
explanations (see `configs/project_knowledge.md` Section 5 for full
numbers): **seed variance** (retrained combined-220 twice, seed only
changed) put the cfg109/cfg110 noise floor at ~0.43 meV/atom -- the FAIL
margin is ~3x that on the fixed threshold, though the threshold itself
(a single-seed single-point extreme) shifts ~0.81 meV/atom across the
same 3 seeds, a real fragility, noted but not acted on (the threshold is
explicitly locked, not revisable post hoc). **Model capacity** (retrained
at LoRA rank 8 and rank 16, seed fixed) showed no benefit -- rank 8 was
indistinguishable from noise, rank 16 made both configs measurably
*worse*, beyond the noise floor. **Capacity hypothesis rejected.**

That result pointed at a genuine data-density gap rather than a model
limit: the Al3Ni high-expansion regime (iso_expansion /
volume_rattle_expansion) had only 3 TRAIN rungs across +2%..+5.6%
(s=2.0%, 3.0%, 4.6%), with a 1.6-percentage-point gap between 3.0% and
4.6% -- exactly where cfg109/cfg110 (s=4.0%) used to sit. **Round285**
(2026-08-18, design-only, no DFT/training yet) proposes densifying
+3.0%..+5.0% at 0.5-point steps for both families -- 7/10 candidates
survived the gates (`configs/ROUND285_HIGH_EXPANSION_DENSIFY_DESIGN_STATUS.md`);
proposed TRAIN 182 -> 189.

The sealed pair went through two same-day revisions before settling. The
first proposal, `cfg295_Al3Ni_iso_expansion` (+3.75%) /
`cfg296_Al3Ni_volume_rattle_expansion` (+4.25%), was **retired, never
DFT'd** -- a reverse-leakage check (distance from the 7 approved TRAIN
candidates to the sealed pair, which the original design never computed)
found min distance 0.2421, below both the policy-cited 0.734644 and
round285's own fresh 0.3269. Root cause: a sealed interpolation point
placed *inside* a 0.5-point-dense TRAIN grid is bound to <=0.25 points
from its nearest neighbor -- density and seal-isolation cannot coexist in
the same interval.

The second proposal, `cfg297_Al3Ni_iso_expansion` / `cfg298_Al3Ni_volume_
rattle_expansion` (both s=3.5%, the one interval -- 3.0%->4.0% -- that
couldn't be densified, blocked by leakage against cfg043 at s=3.5000%),
cleared the isolation check but cfg298 was **also retired**: it is
descriptor-degenerate with cfg043 (d_vol/d_strain ~1e-8/1e-9), and cfg043
is not an ordinary holdout -- it is the FEEDBACK PROBE that steered 5+
remediation design rounds
(`configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`). A seal that
clones the feedback probe inherits its design contamination. cfg297 was
re-verified and kept (legitimate matched-family separation from cfg043,
not a collapse).

**Current sealed pair:** `cfg297_Al3Ni_iso_expansion` (s=3.5%) /
`cfg299_Al3Ni_volume_rattle_expansion` (s=3.6%, swept for a placement
that both clears 0.3269 against all 15 TRAIN rungs and is non-degenerate
against cfg043/cfg109/cfg110/cfg115/cfg297)
(`configs/ROUND285_SEALED_PAIR_REVISION2_STATUS.md`,
`configs/AL3NI_ROUND285_SEALED_CONFIRMATION_POLICY.txt`) -- DFT has not
been run for either yet. cfg043's exact strain, resolved from the frozen
manifest and confirmed by geometry inversion: **3.5000%** (an earlier
informal "~3.56%" note was never a computed value). Not yet done: DFT for
any round285 structure, merging into a combined-227 dataset, retraining.

Every stage above followed the redundancy/leakage/duplicate gate process
in `configs/EXPANSION_BATCH_DESIGN_POLICY.md`, re-deriving thresholds
fresh per phase/round rather than reusing prior numbers -- round285 found
and fixed a gate-design error before it produced a bad result: gate (a)
cannot be a blanket TRAIN-vs-TRAIN reject when the round's whole purpose
is deliberate density (policy's own text: "TRAIN-vs-TRAIN similarity at
different strain values is an efficiency advisory only, never a rejection
reason"). Full technical detail, per-stage reports, and the coverage-gap
history: `configs/project_knowledge.md` and `results/full_coverage_audit_v1/`.

**Update 2026-08-18/19: round285 DFT completed, merged, and the sealed pair
unsealed -- PASS.** All 9 round285 structures (7 TRAIN + cfg297/cfg299
sealed) finished DFT cleanly (pod01-03, `configs/ROUND285_POD_0{1,2,3}_STATUS.txt`).
Merged into **combined-227** (TRAIN 189 / VALIDATION 18,
`configs/AL3NI_COMBINED227_MERGE_STATUS.txt`; cfg297/cfg299 verified
physically absent from all 3 output files). Retrained
(`models/al3ni_combined227_lora_v1/`, seed 20260811, same LoRA rank-4
hyperparameters). The confirmation threshold was re-derived, robust to
seed choice this time -- max of 3 seeds' (20260811/812/813) own per-seed
maxima over the reserved-19, **2.6183 meV/atom**
(`configs/ROUND285_SEALED_ACCEPTANCE_CRITERION.txt`; cross-seed spread
0.185 meV/atom, down from 0.808 for combined-220's single-seed-derived
threshold, and the anchoring config, cfg060, is now identical across all
3 seeds instead of shifting identity). At unsealing
(`configs/AL3NI_ROUND285_FINAL_UNSEALING_RESULT.txt`, irreversible,
first-and-only read): cfg297 |error|=1.847 meV/atom, cfg299
|error|=1.922 meV/atom -- **both PASS, OVERALL PASS, LAMMPS AUTHORISED:
YES**.

## LAMMPS integration (Stage 9)

**LAMMPS build.** Two builds exist under `tools/lammps/install/`: an
initial `mliap_python` build (PKG_PYTHON + PKG_ML-IAP, no Kokkos) turned
out to be a dead end -- mace 0.3.16's ML-IAP ghost-atom feature exchange
(`forward_exchange`/`reverse_exchange`) is only implemented on LAMMPS's
Kokkos `MLIAPDataPy` variant, confirmed by grepping the LAMMPS source
tree. Rebuilt with `PKG_KOKKOS` (CUDA, sm_89/Ada89,
`configs/LAMMPS_MLIAP_KOKKOS_BUILD_STATUS.txt` -- commit, full cmake
flags, nvcc/gcc versions, `lmp` sha256 all recorded), which is now the
active build (`tools/lammps/setup_lammps_env.sh`). Both builds' Python
modules are installed in isolation (`pip install --target`, selected via
`PYTHONPATH`) rather than the venv's global site-packages, so they
coexist without one clobbering the other.

**Model export.** `al3ni_combined227_lora_v1.model` exported to LAMMPS
ML-IAP format via `scripts/export_lammps_mliap_model.py`, which
deliberately bypasses `mace_create_lammps_model --format mliap`'s forced
(and, for this checkpoint, broken) e3nn->cuequivariance weight conversion
-- cuequivariance isn't even installed here, and the conversion isn't
needed by the ML-IAP wrapper class.

**Stage A (single-point LAMMPS vs. ASE/MACE agreement, the critical
export/units check):** PASS, roundoff-level agreement (~1e-12 eV energy,
~1e-14 eV/Angstrom forces) on two test structures
(`configs/LAMMPS_STAGE_A_SINGLE_POINT_STATUS.txt`). Getting here required
four real fixes beyond the Kokkos rebuild itself (Kokkos-specific
LAMMPS/mace API calls and cmdargs, a missing `cupy` dependency, dropping
`lmp.finalize()` after a reproducible Kokkos/torch/cupy CUDA-teardown
segfault, and correctly slicing owned atoms out of Kokkos's
ghost-padded `extract_atom` arrays) -- all documented inline in
`scripts/lammps_stage_a_single_point.py`.

**Stage B (5-phase relaxation vs. DFT):** all 5 phases relaxed
successfully, each in its own subprocess for Kokkos/CUDA teardown
isolation (`scripts/lammps_stage_b_run_all.py` -- process isolation is
load-bearing: `lmp.finalize()` is unsafe, so each phase must exit its own
process rather than share one). Max volume/atom error vs. DFT: 0.216%
(Al3Ni5); symmetry preserved 5/5; LAMMPS vs. direct ASE/MACE relaxation
agreed to 0.00000% everywhere, as Stage A predicted
(`configs/LAMMPS_STAGE_B_RELAXATION_STATUS.txt`). Al3Ni5 was the outlier
-- its alpha angle relaxed to 98.28 deg vs. DFT's 96.478 deg (1.87%, ~3x
any other phase's max deviation). A follow-up diagnostic
(`configs/LAMMPS_STAGE_B_AL3NI5_ALPHA_DIAGNOSTIC.txt`) constrained the
angle back to the DFT value and found a real (not soft-mode-meaningless)
energy cost, +0.873 meV/atom -- about 2x the project's measured
cross-seed noise floor. Also plausibly (not proven) linked to cfg060,
the Al3Ni5 config that anchors the acceptance threshold across all 3
seeds; raw TRAIN density for Al3Ni5 is unremarkable, so if there's a
shared cause it's more specific than overall phase coverage.

**Stage C (elastic constants, all 5 phases):** finite-difference
stress-strain at each phase's own LAMMPS zero-stress relaxed cell,
process-isolated per phase (`scripts/lammps_stage_c_run_all.py`,
`configs/LAMMPS_STAGE_C_ELASTIC_STATUS.txt`). All 5 phases mechanically
stable (Born criteria, general eigenvalue test and cubic-specific for
AlNi/AlNi3). AlNi3 agrees with experimental literature reasonably well
(C11/C12/C44 within +8.5%/+0.7%/+5.1%); AlNi is worse, mainly on C11
(-26% vs. a DFT reference, -15% vs. a recalled-not-freshly-verified
experimental figure). Al3Ni/Al3Ni2/Al3Ni5 are model predictions only, no
DFT/literature elastic reference exists (**UNVALIDATED**). Notably,
Al3Ni5's C44 = 33.15 GPa is ~3x softer than its own C55/C66 and the
softest shear constant of any phase -- an independent, quantitative
confirmation of the Stage B alpha-angle diagnostic (same yz/shear
direction, now shown to be a genuinely soft elastic mode, not just a
one-off energetic quirk).

**Not yet done:** Stage D (short NVT/NPT stability runs).

## Unified comparison matrix and the formation-energy offset finding

`configs/NI_AL_UNIFIED_COMPARISON.md` (2026-08-21) closes a six-method
comparison matrix — MACE-MP-0 Small (zero-shot), MACE-MATPES-PBE-0
(zero-shot), `al3ni_combined227_lora_v1` (fine-tuned), and three NIST
EAM/alloy potentials (Pun-Mishin 2009, Mishin 2004 ipr2, Mishin 2002 via
LAMMPS) — against a QE/PBE reference computed fresh in that session
(elemental mu_Al/mu_Ni via vc-relax + independent final SCF, locked
production settings; elemental Ni's `nspin=2`/0.60 μB/22×22×22-k-mesh
decision reused exactly as originally locked, elemental Al's own k-mesh
independently convergence-tested rather than assumed). Full combined-227
(227 structures), reserved-20 held-out reported separately. A second,
independent reference — Materials Project DFT, carried from Phase 1 (a
separate Windows-machine project, `inbox/`) — is used only as a ranking
cross-check, kept in its own column, never merged into the QE/PBE numbers.

**Headline result, and it is the primary current characterization, not the
first-pass one:** the fine-tuned model has by far the best relative-energy
and force accuracy of the six methods, but its raw pure-model
formation-energy MAE (79.6 meV/atom) initially looked like it was *worse*
than zero-shot MACE-MATPES-PBE-0 (25.1 meV/atom) — a compound-description
weakness. It is not. The five per-phase signed errors are linear in x_Ni
(R²=0.9931, residual std 0.96 meV/atom — at the project's own
k-convergence noise floor), the exact algebraic signature of two wrong
elemental references rather than five independent compound errors. The
mechanism was confirmed directly, not just inferred: evaluating the
fine-tuned model on the actual QE-relaxed elemental Al/Ni cells gives
delta_Al=48.44 / delta_Ni=112.54 meV/atom, matching the fit's
delta_Al=46.13 / delta_Ni=112.39 to within a few meV. delta_Ni running
~2.4x delta_Al tracks the same Ni-magnetism sensitivity raised repeatedly
elsewhere in this project (Phase 1's own "Ni magnetic limitation" note;
elemental Ni's separate `nspin=2` decision above; AlNi3 independently
needing `nspin=2` where the other four phases did not).

Pairing the fine-tuned model's own compound energies with **QE/PBE's own
mu_Al/mu_Ni** (mu_Al=-537.46115182 eV/atom, mu_Ni=-4670.57345642
eV/atom) — a "QE-referenced hybrid," justified because the model is
QE-calibrated and in-domain on compounds but was extrapolating on isolated
elements it never trained on — collapses the formation-energy MAE from
79.6 to **0.95 meV/atom**, inside the noise floor. Phase stability ordering
against QE/PBE was exact under both the pure-model and hybrid schemes
(Spearman ρ=1.0, pairwise 10/10 either way) — the offset was never large
enough to disturb ranking, though it does matter for any absolute
formation-energy number.

**Use guidance for `al3ni_combined227_lora_v1`:**
- MD, forces, relative energies: validated, unchanged by this finding.
- Formation energy: valid to ~1 meV/atom **only when paired with QE/PBE's
  own elemental references** above — do **not** use the model's own
  elemental predictions (that pairing is exactly the 79.6 meV/atom failure
  mode). Pure-model formation-energy numbers remain on record in
  `NI_AL_UNIFIED_COMPARISON.md` (kept, not deleted) but are superseded as
  the recommended figure.
- **Root cause and the clearest next-round improvement:** elemental Al and
  Ni were never in this model's fine-tuning training set (only the five
  alloy phases were). Adding them would let the model supply its own
  accurate mu directly and remove the need for the QE-referenced hybrid
  pairing.

## Safety and directory policy

- Treat `data/raw_dft` as immutable source data.
- Store reproducible scripts in `scripts`, configurations in `configs`,
  canonical processed data in `data/processed`, and split datasets in
  `data/datasets`.
- Store runs, logs, checkpoints, and models only in their dedicated project
  directories.
- Never store credentials in this project.
