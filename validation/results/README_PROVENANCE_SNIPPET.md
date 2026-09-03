<!--
Ready-to-paste block for the public README of Asiri1108/ni-al-mlip
(and, with the second clone line, Asiri1108/NiAl_MACE).

Reason this exists: an independent validation of al3ni_combined227_lora_v1
cloned this repository on Windows and its first hash comparison reported 32 of
43 artifacts as DIFFERENT. All 32 were false positives caused by git's
autocrlf line-ending rewrite. Without this note, every Windows user who tries
to verify the release will reach the same wrong conclusion.
-->

## Verifying this release

Artifacts in this repository are line-ending sensitive: the `.extxyz` datasets and
the `configs/*` status files are hashed and cross-referenced by SHA256 throughout the
project, and several of those hashes are pinned inside status files as integrity
records.

**Clone with `core.autocrlf` disabled**, or every text artifact's hash will differ
from the recorded value:

```bash
git -c core.autocrlf=false clone https://github.com/Asiri1108/ni-al-mlip.git
git -c core.autocrlf=false clone https://github.com/Asiri1108/NiAl_MACE.git
```

If you already have `core.autocrlf=true` set globally (the Git for Windows default),
a plain `git clone` rewrites LF to CRLF on checkout. This adds one byte per line to
every text file and changes its SHA256. The symptom is unmistakable once you look for
it: the checked-out `data/datasets/ni_al_combined227_dft.extxyz` is exactly **2,266
bytes** larger than the recorded size, which is precisely its line count
(227 configurations x 2 header lines, plus 1,812 atom lines).

To confirm a correct checkout:

```bash
sha256sum data/datasets/ni_al_combined227_dft.extxyz
# expected: 9051860ae83dea782d9e5e49e4bf68f992103eed703ad81ca1ded5ea98db29eb
```

That value is also recorded in `configs/AL3NI_COMBINED227_MERGE_STATUS.txt`, together
with the TRAIN(189) and VALIDATION(18) split hashes.

### Model artifact

The fine-tuned models are distributed via HuggingFace, not this repository.
`https://huggingface.co/asiri1/al3ni-mace` hosts three checkpoints:

```
al3ni_combined227_lora_v1.model            (seed 20260811, the model under test)
sha256: e4fd54cc8a4a090fc9e32d6625269142824bfada8315433127b3aa3118c65cee

al3ni_combined227_seed20260812_lora_v1.model
sha256: 4328154a37f55c1ba99c209e978ad76a0f36e5f3d8a41b25c107b27efefe17af

al3ni_combined227_seed20260813_lora_v1.model
sha256: f676d87f8463a8ffcd4fa7d6b81796b5d42b89602267109010316cbdb4c97e6a
```

The first hash also appears inside `configs/AL3NI_ROUND285_FINAL_UNSEALING_RESULT.txt`,
so the published model can be confirmed to be the exact artifact named in the sealed
confirmation record. The two seed replicas make the statistical reproducibility claim
below independently checkable.

The foundation checkpoint it was fine-tuned from is upstream:

```
ACEsuit/mace-foundations, release mace_matpes_0  ->  MACE-matpes-pbe-omat-ft.model
sha256: e618ad582b84239905b9c3b77ce6e9ce111b0ecd1533223a1a6aac7a696b8aa0
```

pinned in `configs/pilot25_matpes_pbe_lora_v1_PROVENANCE.txt`.

### On reproducibility

Retraining from `configs/al3ni_combined227_lora_v1.yaml` is **not** expected to
regenerate the published model bitwise. The config sets a seed but no determinism
controls, training runs on CUDA, and the toolchain (Python 3.12.3, torch 2.8.0+cu128,
CUDA 12.8, RTX 4090) is pinned by documentation rather than by a container. This is
normal for GPU training and is not a defect.

The reproducibility claim that *is* supported is statistical: three independent seeds
(20260811/20260812/20260813) trained on identical data and hyperparameters agree to
0.078 meV/atom in overall error, well inside the measured 0.43 meV/atom seed-noise
floor. All three checkpoints are published, so you can recompute this yourself - and
with it the 2.6183 meV/atom acceptance threshold, which is the maximum of the three
seeds' reserved-19 maxima (2.5232 / 2.4333 / 2.6183).
