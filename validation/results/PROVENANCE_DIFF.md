# Provenance diff - public sources vs the artifacts the validation consumed

**Mode: public-source only.** Permitted sources were `git clone` of the two public
GitHub repositories, `huggingface_hub`, and the upstream MACE foundation release.
No `D:/` path, no `/workspace` path and no `.tar.gz` was used to obtain a public
copy. The local archive was read but not modified or deleted; it is the left-hand
side of every comparison below.

**Sources**

| Source | Reference |
|---|---|
| GitHub | `Asiri1108/ni-al-mlip` @ `21d0996` (2026-08-23) |
| GitHub | `Asiri1108/NiAl_MACE` |
| HuggingFace | `asiri1/al3ni-mace` @ `fcb5020e4865` (models, 2026-08-30) |
| Upstream | `ACEsuit/mace-foundations`, release `mace_matpes_0` (base model only) |

## Methodological warning: the first diff was wrong

A naive `git clone` on this machine reported **32 of 43 artifacts as DIFFERENT**.
That was entirely an artefact. `core.autocrlf` is set to `true` globally here, so
git rewrote every text file's line endings from LF to CRLF on checkout. The public
copy of `ni_al_combined227_dft.extxyz` came out at 415,544 bytes against the local
413,278 - a difference of exactly 2,266 bytes, which is precisely the file's line
count (227 x 2 header lines + 1,812 atom lines).

Re-cloning with `git -c core.autocrlf=false clone` made every one of those 32
artifacts byte-identical. **Anyone repeating this diff on Windows must disable
autocrlf, or they will conclude the public release has been tampered with.**

## Step 1 - Result

| Status | Count |
|---|---|
| IDENTICAL | 35 |
| DIFFERENT | 0 |
| MISSING FROM PUBLIC RELEASE | 8 |

**No artifact is DIFFERENT.** Every artifact that exists in the public release is
byte-identical to the copy the validation consumed. The only gap is that eight of the
eleven model checkpoints are not published at all.

**Update, 2026-08-30.** Seeds `20260812` and `20260813` have since been published to
`asiri1/al3ni-mace` and re-verified from the public copy. The counts above reflect
that; they were 33 / 0 / 10 at the time of the original diff.

**Scope note.** The 43 artifacts counted here are the ones *this validation consumed*.
Two further checkpoints - `al3ni_combined220_seed20260812_lora_v1.model` and
`al3ni_combined220_seed20260813_lora_v1.model` - were registered in
`model_dataset_integrity.json` on 2026-08-30 (see the HuggingFace section below).
They are unpublished, but no number in this validation was computed from them, so
they are deliberately **not** added to the counts above; adding them would change
what this table measures. They appear instead in the RELEASE_TODO, where what
matters is what publishing them would unlock.

### Models

| Artifact | Public source | Status | SHA256 (local) |
|---|---|---|---|
| `al3ni_combined227_lora_v1.model` | huggingface asiri1/al3ni-mace | IDENTICAL | `e4fd54cc8a4a090f...` |
| `al3ni_combined227_seed20260812_lora_v1.model` | huggingface asiri1/al3ni-mace | IDENTICAL | `4328154a37f55c1b...` |
| `al3ni_combined227_seed20260813_lora_v1.model` | huggingface asiri1/al3ni-mace | IDENTICAL | `f676d87f8463a8ff...` |
| `pilot25_matpes_pbe_lora_v1.model` | *(none)* | **MISSING FROM PUBLIC RELEASE** | `94d8d4dade732207...` |
| `dataset100_matpes_pbe_lora_v1.model` | *(none)* | **MISSING FROM PUBLIC RELEASE** | `745f02582e604fed...` |
| `al3ni_combined113_lora_v1.model` | *(none)* | **MISSING FROM PUBLIC RELEASE** | `2530c549b654059e...` |
| `al3ni_combined127_lora_v1.model` | *(none)* | **MISSING FROM PUBLIC RELEASE** | `dd50128d79985224...` |
| `al3ni_combined129_lora_v1.model` | *(none)* | **MISSING FROM PUBLIC RELEASE** | `772453cefb8a3799...` |
| `al3ni_combined211_lora_v1.model` | *(none)* | **MISSING FROM PUBLIC RELEASE** | `e859554a0e0cdd32...` |
| `al3ni_combined218_lora_v1.model` | *(none)* | **MISSING FROM PUBLIC RELEASE** | `5944a24de571d38b...` |
| `al3ni_combined220_lora_v1.model` | *(none)* | **MISSING FROM PUBLIC RELEASE** | `1c39751f9b0cc5cb...` |

### Datasets

| Artifact | Public source | Status | SHA256 (local) |
|---|---|---|---|
| `ni_al_combined227_dft.extxyz` | ni-al-mlip | IDENTICAL | `9051860ae83dea78...` |
| `ni_al_combined227_train_189.extxyz` | ni-al-mlip | IDENTICAL | `41e4baf136bb430d...` |
| `ni_al_combined227_validation_18.extxyz` | ni-al-mlip | IDENTICAL | `079459f075a871d8...` |
| `ni_al_combined220_train_182.extxyz` | ni-al-mlip | IDENTICAL | `65ced37b1c61eeda...` |
| `ni_al_combined220_validation_18.extxyz` | ni-al-mlip | IDENTICAL | `079459f075a871d8...` |
| `ni_al_combined218_train_180.extxyz` | ni-al-mlip | IDENTICAL | `32da74200514506c...` |
| `ni_al_combined218_validation_18.extxyz` | ni-al-mlip | IDENTICAL | `079459f075a871d8...` |
| `ni_al_combined211_train_173.extxyz` | ni-al-mlip | IDENTICAL | `c1ed24fd236c61a4...` |
| `ni_al_combined211_validation_18.extxyz` | ni-al-mlip | IDENTICAL | `079459f075a871d8...` |
| `ni_al_combined129_train_91.extxyz` | ni-al-mlip | IDENTICAL | `4b5c68de598fe451...` |
| `ni_al_combined129_validation_18.extxyz` | ni-al-mlip | IDENTICAL | `079459f075a871d8...` |
| `ni_al_combined127_train_89.extxyz` | ni-al-mlip | IDENTICAL | `1517e9dd13541eec...` |
| `ni_al_combined127_validation_18.extxyz` | ni-al-mlip | IDENTICAL | `079459f075a871d8...` |
| `ni_al_combined113_train_75.extxyz` | ni-al-mlip | IDENTICAL | `86f1a844964bfcc8...` |
| `ni_al_combined113_validation_18.extxyz` | ni-al-mlip | IDENTICAL | `079459f075a871d8...` |
| `ni_al_dataset100_train_65.extxyz` | ni-al-mlip | IDENTICAL | `fe49d0130665bd8f...` |
| `ni_al_dataset100_validation_15.extxyz` | ni-al-mlip | IDENTICAL | `215e591a293fe802...` |
| `ni_al_pilot_train_15.extxyz` | ni-al-mlip | IDENTICAL | `b7f3711d565e912f...` |
| `ni_al_pilot_val_5.extxyz` | ni-al-mlip | IDENTICAL | `f09e54eceddba7b7...` |
| `ni_al_pilot_test_5.extxyz` | ni-al-mlip | IDENTICAL | `fff925984d04f51c...` |

### Config / status files

| Artifact | Public source | Status | SHA256 (local) |
|---|---|---|---|
| `STEPB_ELEMENTAL_REFERENCES_STATUS.txt` | ni-al-mlip | IDENTICAL | `f55f0a1589c36edf...` |
| `AL3NI_ROUND285_FINAL_UNSEALING_RESULT.txt` | ni-al-mlip | IDENTICAL | `414761f44c4ab8c9...` |
| `ROUND285_SEALED_ACCEPTANCE_CRITERION.txt` | ni-al-mlip | IDENTICAL | `7e4fc32a8efa49c0...` |
| `AL3NI_COMBINED227_MERGE_STATUS.txt` | ni-al-mlip | IDENTICAL | `d8c281eac1012ae3...` |
| `LAMMPS_STAGE_A_SINGLE_POINT_STATUS.txt` | ni-al-mlip | IDENTICAL | `8f988fd179ac9cbf...` |
| `LAMMPS_STAGE_B_AL3NI5_ALPHA_DIAGNOSTIC.txt` | ni-al-mlip | IDENTICAL | `0001dab9a7f12bd9...` |
| `LAMMPS_STAGE_C_ELASTIC_STATUS.txt` | ni-al-mlip | IDENTICAL | `0e139bc720e56a5d...` |
| `pilot25_matpes_pbe_lora_v1_PROVENANCE.txt` | ni-al-mlip | IDENTICAL | `21c667f6a5925c89...` |
| `al3ni_combined227_lora_v1.yaml` | ni-al-mlip | IDENTICAL | `f68575b8d545501c...` |
| `ROUND285_SUCCESS_CRITERIA.txt` | ni-al-mlip | IDENTICAL | `01a5b57494757cb3...` |
| `AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt` | ni-al-mlip | IDENTICAL | `8e38968a1ce2b2e1...` |
| `AL3NI_FINAL_UNSEALING_RESULT.txt` | ni-al-mlip | IDENTICAL | `2f7120cd4a329691...` |

### Base model (upstream, not a project repo)

| Artifact | Source | Status |
|---|---|---|
| `MACE-matpes-pbe-omat-ft.model` | github.com/ACEsuit/mace-foundations release mace_matpes_0 | IDENTICAL |

SHA256 `e618ad58...` matches the pin recorded in
`configs/pilot25_matpes_pbe_lora_v1_PROVENANCE.txt`, which is itself public and
identical. The base model is fully verifiable from public sources.

### HuggingFace

Repository `asiri1/al3ni-mace` @ `fcb5020e4865` contains five files: `.gitattributes`,
`README.md`, and three model checkpoints. All three were downloaded from the public
repository and hashed from the downloaded bytes (not merely read from the LFS
metadata), and all three match `results/model_dataset_integrity.json` exactly:

| File | Bytes | SHA256 (public download) | vs local | Status |
|---|---:|---|---|---|
| `al3ni_combined227_lora_v1.model` | 12,211,680 | `e4fd54cc8a4a090fc9e32d6625269142824bfada8315433127b3aa3118c65cee` | match | **IDENTICAL** |
| `al3ni_combined227_seed20260812_lora_v1.model` | 12,212,993 | `4328154a37f55c1ba99c209e978ad76a0f36e5f3d8a41b25c107b27efefe17af` | match | **IDENTICAL** |
| `al3ni_combined227_seed20260813_lora_v1.model` | 12,212,993 | `f676d87f8463a8ffcd4fa7d6b81796b5d42b89602267109010316cbdb4c97e6a` | match | **IDENTICAL** |

The three-seed evidence is therefore now checkable from public artifacts alone.

**`pilot25_matpes_pbe_lora_v1.model` is still not published.** `HfApi.list_models(author=...)`
returns exactly one repository for `asiri1` and nothing for the spellings `asiri1108`,
`Asiri1108`, `asiri`, `asiri-1` or `asiri11`; a full-text search for `pilot25` returns no
result. `pilot25` remains **MISSING FROM PUBLIC RELEASE**, and with it the three-way
comparison and the VALIDATION-18 anomaly breakdown remain not publicly reproducible.

#### Commit history

| Revision | Date | Files after this commit |
|---|---|---|
| `2bbf8d40788c` | 2026-08-23 | `.gitattributes` |
| `f5740c805a69` | 2026-08-23 | + `al3ni_combined227_lora_v1.model` |
| `5f64e2d0308e` | 2026-08-23 | + `README.md` |
| `3f35327ae3bf` | 2026-08-23 | unchanged (README edit) |
| `404a5206b7d7` | 2026-08-30 | + `al3ni_combined220_seed20260812_lora_v1.model`, `al3ni_combined220_seed20260813_lora_v1.model` |
| `e68943868ab2` | 2026-08-30 | + `al3ni_combined227_seed20260812_lora_v1.model`, `al3ni_combined227_seed20260813_lora_v1.model` |
| `5c5b78cf31cc` | 2026-08-30 | - `al3ni_combined220_seed20260812_lora_v1.model` |
| `fcb5020e4865` (main) | 2026-08-30 | - `al3ni_combined220_seed20260813_lora_v1.model` |

#### Correction: two files WERE published and later removed - now explained

The earlier version of this document stated that "nothing was published and later
removed." **That is no longer true and must not be repeated** - the repository
history is not append-only. Commit `404a5206b7d7` published two checkpoints named
`al3ni_combined220_seed20260812_lora_v1.model` and
`al3ni_combined220_seed20260813_lora_v1.model`; commits `5c5b78cf31cc` and
`fcb5020e4865` then deleted them and the correct combined-**227** seeds were
uploaded in their place.

**Explanation (from the uploader, 2026-08-30):** this was a **filename/selection
error at upload time** - the wrong two files were picked from a directory of
similarly named checkpoints - and it was corrected by deleting them and uploading
the intended pair. It is emphatically **not** a byte-level rename: the combined-220
and combined-227 seed checkpoints are genuinely different models, trained on
different data (TRAIN 182 vs TRAIN 189), and their hashes differ accordingly.

**Both files were located in the local archive and hashed** (2026-08-30). They are
genuine combined-220 seed replicas, and the local copies match the deleted HF blobs
exactly:

| File | Bytes | SHA256 (local archive) | vs deleted HF blob |
|---|---:|---|---|
| `al3ni_combined220_seed20260812_lora_v1.model` | 12,212,993 | `3166409492adce575c5aefcb71dc9c4dcc5104a27402de2a4c63d35b45d53687` | **identical** |
| `al3ni_combined220_seed20260813_lora_v1.model` | 12,212,993 | `78c316da04ee50ead05d6725e403d878b95df8b212a34d5bd422d12bcb46f29d` | **identical** |

Both load cleanly (`r_max` 6.0, 655,534 parameters) and are now registered in
`results/model_dataset_integrity.json`, which previously recorded only
`al3ni_combined220_lora_v1` for that generation. They are flagged there as
`used_in_validation: false` - no number in this validation was computed from them.

**What they are for.** They are the evidence base for LESSON 2 of
`configs/ROUND285_SEALED_ACCEPTANCE_CRITERION.txt` ("do not derive from a single
seed"): the seed-variance investigation that found the combined-220 threshold
fragile. That investigation has now been **independently reproduced from these two
checkpoints** - see `results/combined220_seed_thresholds.json` and the RELEASE_TODO
entry in `results/VALIDATION_REPORT.md`. The recorded finding is a 0.808 meV/atom
spread in the reserved-19 maximum with the anchor moving cfg060 -> cfg075 -> cfg060;
recomputation gives 0.8080 and cfg060 -> cfg075 -> cfg060, matching to the digit.

The retraction above stands: the history did change, and the change is now
explained and accounted for rather than merely noted. Nothing here affects any hash
comparison in this document - the three checkpoints currently on `main` are the ones
verified, and all three match.

The `combined227` hash also matches the pin inside
`configs/AL3NI_ROUND285_FINAL_UNSEALING_RESULT.txt`, which is public and identical.
So the model under test, the published model, and the model named in the sealed
unsealing record are all one and the same file, confirmed from public sources alone.

## Step 2 - Blast radius

The critical distinction: **no number in the completed validation changes**, because
every input that is public is byte-identical. What changes is *reproducibility* -
which conclusions a third party with only public access could independently re-derive.

### Fully reproducible from public sources

Phases **1, 2, 2b, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17** need only the
`combined227` model (on HuggingFace), the `combined227` dataset, and config files -
all present and identical. In particular:

- **Phase 7 / 10 / 13 / 14** depend on `mu_Al` and `mu_Ni`, whose sole source
  `STEPB_ELEMENTAL_REFERENCES_STATUS.txt` is public and identical.
- **Phase 12**'s entire verdict rests on `LAMMPS_STAGE_A_SINGLE_POINT_STATUS.txt`,
  which is public and identical.
- **Phase 4**'s alpha-angle corroboration and **Phase 8**'s elastic cross-check rest
  on the Stage B and Stage C status files, both public and identical.

Two analyses moved into this category on 2026-08-30, when seeds `20260812` and
`20260813` were published and verified identical:

- **The 2.6183 threshold derivation.** All three seed checkpoints
  (`20260811` / `20260812` / `20260813`) are now public, so all three reserved-19
  maxima (2.5232 / 2.4333 / 2.6183) and the fact that cfg060 anchors all three can
  be recomputed by a third party. **The locked acceptance threshold is therefore now
  independently re-derivable** - it is the maximum of three publicly recomputable
  numbers.
- **Phase 3.5, the multi-seed comparison and the seed noise floor.** The 0.078
  meV/atom cross-seed spread, and its comparison against the 0.43 meV/atom noise
  floor, are fully reproducible from public artifacts.

### Degraded

| Analysis | Effect of the missing checkpoints |
|---|---|
| **Phase 3, three-way comparison** | Becomes **two-way**. `base` (public upstream) vs `combined227` (public) still gives the headline result that fine-tuning cuts energy MAE 4.3x and force MAE 15.7x. The `pilot25` middle term is lost, so the claim *"combined227 improves on pilot25 in every column"* is **not publicly reproducible**. |
| **Phase 16, data-efficiency curve** | **Unrunnable.** Eight of the nine points (N = 25, 100, 113, 127, 129, 211, 218, 220) require unpublished checkpoints. Only N = 227 survives - a one-point curve. The central research claim (~100 configurations suffices; 100 -> 227 buys only -16% energy MAE) is **not publicly reproducible**, even though every dataset it used is public. |
| **Limitation 3 evidence** | Partly lost. The reserved-19 maximum regression 2.3865 -> 2.5232 still needs `combined220`, which is unpublished. The cross-seed confirmation that cfg107/cfg115 degrade in all three seeds **is now reproducible**, since both seed checkpoints are public. |
| **Phase 16 val18 anomaly** | **Unrunnable.** The whole pilot25-vs-combined227 breakdown needs `pilot25`. Note the *contamination* finding itself survives, since it is a pure set-membership check over public datasets. |

### What would restore full reproducibility

Publishing the eight remaining `.model` files - roughly 11 MB each, about 88 MB total.
Nothing else is needed: every dataset, split, config and status file they would be
evaluated against is already public and verified identical.

`pilot25_matpes_pbe_lora_v1.model` is now the highest-value single file on that list:
alone it restores the three-way model comparison, the VALIDATION-18 anomaly breakdown,
and the N = 25 point of the data-efficiency curve.

## Training code: has it diverged?

Reported separately, as requested. **This does not affect the validation, which
tested the artifact, not the code that produced it.**

### The code has NOT diverged

| Comparison | Result |
|---|---|
| Scripts present in both copies | **148 / 148 byte-identical** |
| Scripts differing | **0** |
| Present only in the public repo | 4 |
| Present only locally | 0 |

The public repository is indeed newer - HEAD is `21d0996`, 2026-08-23, later than the
local archive snapshot - but the difference is purely additive, and the four added
files are all downstream analysis, not training:

- `lammps_stage_b_relax_phase_matpes0_zeroshot.py`
- `lammps_stage_b_report_matpes0_zeroshot.py`
- `lammps_stage_b_run_all_matpes0_zeroshot.py`
- `save_lammps_0K_zeroshot_structures.py`

All four add a **zero-shot MACE-MATPES-PBE-0 LAMMPS baseline** for comparison against
the fine-tuned model. None touches training, data assembly, or any threshold.
`run_al3ni_combined227_mace_training.sh` and `al3ni_combined227_lora_v1.yaml` are both
byte-identical to the versions used for the model under test.

### Would rerunning them reproduce the pinned hash? Almost certainly not

This was **not** tested empirically - it needs a CUDA GPU, which this machine does not
have, and retraining is outside the permitted scope. The assessment below is from
reading the pinned, byte-identical launch script and config.

The reason is *environmental determinism*, not code drift:

1. **The script cannot run unmodified anywhere else.** It hard-codes
   `ROOT=/workspace/ni_al` and invokes the interpreter at
   `/workspace/ni_al/envs/mace-py312-cu128/bin/mace_run_train`. It is a RunPod
   container script, not a portable recipe.
2. **Training is not performed by repository code at all.** The script is a thin
   wrapper around upstream `mace_run_train` from MACE 0.3.16. Reproducibility is
   therefore a property of the upstream package and the environment, not of this
   repository.
3. **The config sets `seed: 20260811` but no determinism controls.** There is no
   `torch.use_deterministic_algorithms`, no `CUBLAS_WORKSPACE_CONFIG`. With
   `device: cuda`, non-deterministic atomics and autotuned cuBLAS kernel selection
   mean even the same machine need not reproduce bitwise-identical weights.
4. **The original environment is pinned but not containerised in the public repo:**
   Python 3.12.3, torch 2.8.0+cu128, CUDA 12.8, RTX 4090, driver 580.173.02. A
   different torch or CUDA version changes kernel choice and floating-point
   accumulation order, which changes the weights, which changes the SHA256.

Two inputs that *could* have caused divergence are ruled out: `E0s: estimated` is
deterministic given the training data, and that data is byte-identical; and
`foundation_model: mace-matpes-pbe-0` resolves to the upstream checkpoint whose hash
`e618ad58...` was verified identical.

### How to read this: statistical, not bitwise

Hash-irreproducibility of a GPU training run is the normal state of affairs. It is
**not** a defect, and it is **not** evidence of tampering or of code divergence - the
code here demonstrably has not diverged.

The reproducibility property that matters for a fitted interatomic potential is
statistical, and it is the one this validation confirms:

> **Three independent seeds (20260811 / 20260812 / 20260813), trained on identical
> data with identical hyperparameters, agree to 0.078 meV/atom in overall error - far
> inside the measured 0.43 meV/atom seed-noise floor.** Their reserved-19 maxima
> (2.5232 / 2.4333 / 2.6183) reproduced the recorded values exactly, on a different
> operating system, PyTorch version and processor, and the anchoring configuration
> (cfg060) was identical across all three.

A bitwise hash match would demonstrate less than that: it would show one run repeated,
not that the training procedure lands in the same place from different starting noise.

**As of 2026-08-30 all three seeds are public**, so this statistical evidence is no
longer checkable only inside this validation: a third party can download the three
checkpoints from `asiri1/al3ni-mace` and recompute both the 0.078 meV/atom cross-seed
spread and the three reserved-19 maxima that define the 2.6183 threshold. This was
Priority 1 in the RELEASE_TODO section of `results/VALIDATION_REPORT.md` and it is now
done; the project's central threshold has moved from asserted to independently
verifiable.

The accurate provenance statement is therefore:

> The published artifact `al3ni_combined227_lora_v1.model` is verified identical to the
> file that was validated and to the file named in the sealed unsealing record. The
> code and configuration that produced it are public and unmodified. Its reproducibility
> is established statistically across seeds, not bitwise; bitwise regeneration would
> require a pinned container and enforced deterministic kernels, and is not claimed.

---

*Generated by `scripts/provenance_diff.py` and `scripts/write_provenance_diff.py`.*
*Machine-readable form: `results/provenance_diff.json`.*
