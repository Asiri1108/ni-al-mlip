# Ni-Al Materials Discovery — Project Status

Last updated: 2026-08-10 UTC

## Current stage

Stage 3 — Dataset Engineering. Final Pilot 25 integrity validation and the fixed
train/validation/test split are complete. Foundation-model training has not
started.

## Completed

- Verified the two independently uploaded Pilot 25 copies are each 28,755
  bytes, have the expected SHA-256, and are byte-for-byte identical.
- Established the unchanged canonical dataset at
  `data/processed/ni_al_pilot_dft_25.extxyz`.
- Validated 25 unique configurations with ASE: five phases and five prescribed
  configuration types, each represented exactly five times.
- Verified finite energies, forces, stresses, cells, and coordinates; correct
  force/stress shapes; positive periodic cells; and phase-consistent Al:Ni
  composition.
- Found no duplicate `config_id` values or duplicate geometry fingerprints.
- Created the fixed 15 train / 5 validation / 5 test split. Every split covers
  all five phases, and all 25 IDs occur exactly once across the splits.
- Independently re-read all split files and confirmed reference keys `energy`,
  `forces`, and `stress`.

## Dataset artifacts

| Artifact | Frames | Bytes | SHA-256 |
|---|---:|---:|---|
| Canonical Pilot 25 | 25 | 28755 | `35b2b65fe77d181b5da30dd23bbb7ff9fc4f41c0c0f603738172e2f833ab5b0b` |
| Train | 15 | 16530 | `b7f3711d565e912f3da12bc24ccddbca59ecdbb7c6cfdced8a7ef09892951c6a` |
| Validation | 5 | 6042 | `f09e54eceddba7b7d445b46f243f70af328061266773c727a13009718889392d` |
| Test | 5 | 6183 | `fff925984d04f51cfc0d8add614a8287605c2539b14b72e0784e65ca6c132705` |

## Outlier review

The validation report's conservative robust high-side screen found no maximum
force flags. It marked `AlNi_rattle_003` and `AlNi3_rattle_003` for RMS-force
review and `AlNi3_iso_m02` and `Al3Ni5_iso_m02` for stress-magnitude review.
These are physically plausible categories for elevated values (rattles and
strained cells), but they remain review flags rather than proof of bad DFT.
Nothing was removed or modified. Exact metrics are in
`data/processed/pilot25_validation_report.txt`.

## Previous pipeline-only model result

The earlier Pilot 01 MACE-MPA LoRA proof run achieved approximately 2.4
meV/atom energy MAE and 4.3 meV/angstrom force MAE on training, and 4.3
meV/atom energy MAE and 9.6 meV/angstrom force MAE on its temporary validation
split. These are pipeline evidence only, not final scientific performance.

## Outstanding issues

- Pilot 25 has only 15 training structures; resulting metrics will have high
  statistical uncertainty and cannot establish production readiness.
- Review the four robust outlier flags against original DFT convergence/output
  evidence before interpreting model errors. Raw DFT data remains immutable.
- GPU determinism can still depend on CUDA kernels even with a fixed seed.
- The unseen five-configuration test set must remain excluded from tuning and
  model selection.

## Next recommended action

Review and approve (or revise) `configs/pilot25_mpa_lora_v1.yaml`. The proposal
uses MACE-MPA-0 medium with rank-4 LoRA, estimated E0s, float32 CUDA, fixed seed,
stress-aware weighted loss, checkpointing, and early stopping. No training has
been launched.

