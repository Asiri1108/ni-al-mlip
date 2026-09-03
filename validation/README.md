# Independent validation of `al3ni_combined227_lora_v1`

This directory holds a complete independent validation of the Ni-Al MACE model:
the scripts that were run, every artefact they produced, and the report assembled
from those artefacts.

It was run on **separate hardware, OS and PyTorch version** from the original
training, against checkpoints and datasets verified byte-identical to the
published ones.

**Start here → [`results/VALIDATION_REPORT.md`](results/VALIDATION_REPORT.md)**

For the project this validates — dataset lineage, training, sealed-holdout
protocol, LAMMPS deployment — see the [repository README](../README.md).

## Before you use the model

The report's *"Fit for"* and *"Not fit for, without further DFT"* sections are the
part that matters most. In short, the model is validated for the five known Ni-Al
phases within **x_Ni in [0.25, 0.75]** at strains up to about **±3%**, and is **not**
validated outside that composition range (including the pure elements), beyond
about ±4% strain, or for radiation damage and close-approach regimes.

Outside those bounds it returns plausible-looking numbers that are wrong, and
nothing in the output signals it.

## What was run

19 phases. Every number in the report is read from a file in `results/`; none is
transcribed from project documentation.

| Phase | Subject |
|---|---|
| 1-2 | Dataset and checkpoint integrity; sanity checks |
| 3 | Single-point benchmark over 227 DFT geometries |
| 4-5 | Relaxation, lattice parameters, equation of state |
| 6-8 | Distortion scans, formation energies, elastic constants |
| 9-10 | Phonons and dynamical stability; vacancy energetics |
| 11 | MD stability: 20 NVT + 10 NPT trajectories, 5 ps each |
| 12-14 | LAMMPS cross-check; out-of-distribution behaviour; screening tool |
| 15 | Development applications: NEB vacancy barrier, APB, GSFE, high-T probe |
| 16 | Data-efficiency curve across nine checkpoints |
| 17 | Report assembly |
| 18-19 | Dilution hypothesis (refuted); combined-220 threshold re-derivation |

## Layout

```
scripts/     the 27 phase scripts, exactly as run
results/     every artefact they produced
  VALIDATION_REPORT.md        the report (start here)
  DILUTION_HYPOTHESIS.md      Phase 18 in full
  PROVENANCE_DIFF.md          what the archive records vs what was measured
  model_dataset_integrity.json  SHA256 of every checkpoint and dataset
  published_models.json         which checkpoints are published, and verified
  environment.json              library versions the run used
  md/                           30 MD trajectories (.npz) and their figures
  eos/  distortion/  phonons/   per-phase scans and figures
  applications/                 Phase 15 outputs
```

## Two corrections, kept in the open

Two quantities were computed, found to be physically meaningless on inspection,
and recomputed. Both defects produced runs that exited successfully and printed
confident numbers.

1. **Phase 11 barostat.** `compressibility_au=5e-7` was passed to ASE's
   `NPTBerendsen`, which documents that argument in atomic units (Å³/eV); 5e-7 is
   a bar⁻¹-scale number, ~2×10⁶ too small. The cell never moved and thermal
   expansion came out six orders of magnitude low.
2. **Phase 15 fault-plane constraint.** `FixedPlane(i,(0,0,1))` was used under a
   comment reading *"relax only perpendicular to the fault plane"*. ASE's
   `FixedPlane` confines an atom **to** that plane - the opposite - so the GSFE
   curve collapsed into a step function.

The superseded outputs are kept, not deleted, under
`results/md/_archive_npt_broken/` and
`results/applications/_archive_broken_constraint/`, each with a README recording
the defect and the evidence. The report's *"Corrections applied during
validation"* section generates its before/after tables from those archived files.

## Reproducing this

The checkpoints are on Hugging Face at
[**asiri1/al3ni-mace**](https://huggingface.co/asiri1/al3ni-mace) - all 13 verified
byte-identical to the copies loaded here, hashes in
[`results/model_dataset_integrity.json`](results/model_dataset_integrity.json).
The datasets, splits and configs are in this repository's `data/` and `configs/`.

Clone with `core.autocrlf` disabled or 32 text artefacts will hash differently -
see [`results/README_PROVENANCE_SNIPPET.md`](results/README_PROVENANCE_SNIPPET.md).

```bash
git -c core.autocrlf=false clone https://github.com/Asiri1108/ni-al-mlip.git
```

Scripts expect the archive layout described in `scripts/common.py` and are run in
phase order. Phase 11 takes roughly a day on 12 CPU cores; the rest are minutes
to hours.

## Not included here

Model weights (published on Hugging Face instead), Python bytecode caches, and
working backups made during the corrections. Absolute local paths in
`model_dataset_integrity.json` were replaced with repository-relative ones before
publication; the SHA256 values, which are the authoritative record, are untouched.
