<!--
Edits for https://github.com/Asiri1108/ni-al-mlip/blob/main/README.md

Part A is a bug fix, not a cosmetic change: the README currently sends readers to
`models/...` directories, and this repository contains no .model file at all
(`git ls-files | grep '\.model$'` returns nothing). Anyone following those paths
hits a dead end. The checkpoints now live on Hugging Face, so the paths should
point there.

Part B adds the missing link in the other direction.
-->

# Part A - fix the dead `models/` paths

Four passages point at checkpoint directories that do not exist in this repo.
Replace each as follows.

**A1.**
> The final model artifacts are under `models/pilot25_matpes_pbe_lora_v1/`

becomes

> The final model artifacts are published at
> [`pilot25_matpes_pbe_lora_v1.model`](https://huggingface.co/asiri1/al3ni-mace/blob/main/pilot25_matpes_pbe_lora_v1.model)
> on Hugging Face.

**A2.**
> The trained checkpoint is `models/al3ni_combined220_lora_v1/`

becomes

> The trained checkpoint is
> [`al3ni_combined220_lora_v1.model`](https://huggingface.co/asiri1/al3ni-mace/blob/main/al3ni_combined220_lora_v1.model)
> on Hugging Face.

**A3.**
> Retrained (`models/al3ni_combined227_lora_v1/`, seed 20260811, same LoRA

becomes

> Retrained ([`al3ni_combined227_lora_v1.model`](https://huggingface.co/asiri1/al3ni-mace/blob/main/al3ni_combined227_lora_v1.model),
> seed 20260811, same LoRA

**A4.**
> `al3ni_combined227_lora_v1.model` exported to LAMMPS ML-IAP format via

Leave the sentence, but note that the ML-IAP export is **not** published: it
carries no recorded SHA256 and no phase of the validation loaded it. Suggested
addition at the end of that sentence:

> (the ML-IAP export itself is not published - it has no recorded hash and was
> not covered by the validation).

# Part B - add a "Model checkpoints" section

Place it immediately after the repository description, before the directory
layout.

---

## Model checkpoints

The trained checkpoints are **not** stored in this repository. All 13 are on
Hugging Face:

**[huggingface.co/asiri1/al3ni-mace](https://huggingface.co/asiri1/al3ni-mace)**

The production model is `al3ni_combined227_lora_v1.model`. The other twelve exist
so that the data-efficiency curve and both acceptance thresholds (2.6183 and
2.3865) can be re-derived rather than taken on trust.

This repository holds everything they are evaluated against - the 37 datasets and
splits, the configs, the status files - and every one of those is byte-identical
to the copy the validation used.

### Independent validation

[**VALIDATION_REPORT.md**](VALIDATION_REPORT.md) reports 19 phases run on separate
hardware, OS and PyTorch version, covering dataset integrity, single-point
benchmarks, relaxation, equation of state, elastic constants, phonons, MD
stability and development applications.

Read its **"Fit for" / "Not fit for, without further DFT"** sections before using
the model. In particular it is not validated outside `x_Ni in [0.25, 0.75]`, beyond
about ±4% strain, or for radiation damage and close-approach regimes.

Every checkpoint on Hugging Face was verified byte-identical to the copy the
validation loaded; the hashes are in
[`results/model_dataset_integrity.json`](results/model_dataset_integrity.json) and
the publication record in
[`results/published_models.json`](results/published_models.json).

### Verifying this release

Clone with `core.autocrlf` disabled, or every text artifact's hash will differ
from the recorded value - see
[`README_PROVENANCE_SNIPPET.md`](README_PROVENANCE_SNIPPET.md).

```bash
git -c core.autocrlf=false clone https://github.com/Asiri1108/ni-al-mlip.git
```
