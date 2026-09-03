# Independent Validation Report - `al3ni_combined227_lora_v1` (Ni-Al MACE)

Independent re-validation performed from the local Windows archive, on a
different operating system, PyTorch version and processor from the original
training run. No number in this report was copied from project documentation;
every value was recomputed from the model and DFT files on disk.

**Environment.** Python 3.13.7, torch 2.12.1+cpu, MACE 0.3.16, ASE 3.29.0, on Windows-11-10.0.26200-SP0. Device: **cpu** (CUDA available: False).

## Provenance and public-source verification

Every artifact this validation consumed was re-fetched from public sources only
(`git clone` of `Asiri1108/ni-al-mlip` and `Asiri1108/NiAl_MACE`, `huggingface_hub`,
and the upstream `ACEsuit/mace-foundations` release) and compared by SHA256 against
the local copies actually used. Full detail: `results/PROVENANCE_DIFF.md`.

**33 artifacts byte-identical, 0 different, 10 missing from the public release.**
The ten missing are all model checkpoints; every dataset, split, config and status
file is public and identical.

### The CRLF trap

A plain `git clone` on Windows reports **32 of 43 artifacts as DIFFERENT**. That is
false. Where `core.autocrlf=true`, git rewrites LF to CRLF on checkout and every
text artifact's hash changes. The tell is that the public copy of
`ni_al_combined227_dft.extxyz` comes out exactly 2,266 bytes larger than the local
one - precisely its line count (227 x 2 header lines + 1,812 atom lines).

**Clone with this flag, or you will wrongly conclude the release was tampered with:**

```
git -c core.autocrlf=false clone https://github.com/Asiri1108/ni-al-mlip.git
git -c core.autocrlf=false clone https://github.com/Asiri1108/NiAl_MACE.git
```

This warning belongs in the public repository README as well as here; a ready-to-
paste block is provided in `results/README_PROVENANCE_SNIPPET.md`.

### Identity of the model under test

The model this validation tested, the model published on HuggingFace, and the hash
pinned inside the sealed unsealing record are **the same file**, and all three are
confirmable from public sources:

| Claim | SHA256 | Source |
|---|---|---|
| Model under test | `e4fd54cc...` | local artifact, hashed in this validation |
| Published model | `e4fd54cc...` | `huggingface.co/asiri1/al3ni-mace` |
| Hash pinned in the sealed record | `e4fd54cc...` | `configs/AL3NI_ROUND285_FINAL_UNSEALING_RESULT.txt`, public and identical |

The base model is likewise verifiable: `MACE-matpes-pbe-omat-ft.model`, `e618ad58...`,
matching the pin in the public `pilot25_matpes_pbe_lora_v1_PROVENANCE.txt`.

### NOT reproducible by a third party

Ten checkpoints are unpublished. HuggingFace hosts exactly one model, and that
repository's commit history confirms no other model was ever uploaded and later
removed; no second account or repository exists. Consequently the following results,
though correct as reported here, **cannot currently be independently re-derived from
public artifacts**:

1. **The 2.6183 threshold derivation.** The bar is the maximum across seeds
   20260811/812/813. Only seed 20260811 is public, so the threshold itself cannot be
   re-derived - only its middle contributing value, 2.5232, is recomputable.
2. **The seed noise floor.** The 0.078 meV/atom cross-seed spread requires seeds
   20260812 and 20260813.
3. **Phase 16, the data-efficiency curve.** Eight of its nine points need unpublished
   checkpoints, leaving a one-point curve. Every dataset it uses is public; only the
   models are missing.

Also affected: the three-way model comparison degrades to two-way (base vs
combined227, both public - the 4.3x energy and 15.7x force headline survives), and
the VALIDATION-18 anomaly breakdown needs `pilot25`. The *contamination* finding
within it survives, being a pure set-membership check over public datasets.

### What reproducibility means here: statistical, not bitwise

Bitwise regeneration of the model from source is **not expected**, and its absence is
not a defect. The training code is public and demonstrably unmodified - 148 of 148
shared scripts are byte-identical, and the public repository is newer only by four
additive zero-shot analysis scripts that touch neither training nor any threshold.
What prevents bitwise reproduction is environmental: CUDA non-determinism with no
determinism flags set, and an un-containerised toolchain pin.

**The demonstrated claim is statistical: three independent seeds trained on identical
data agree to 0.078 meV/atom, far inside the 0.43 meV/atom noise floor.** That is the
meaningful reproducibility property for a fitted interatomic potential, and it is the
one this validation confirms. A bitwise hash match would demonstrate less.

The honest limit of that claim: the three-seed evidence is checkable only inside this
validation, because two of the three seeds are unpublished. That is exactly why
releasing them is the highest-value action in the list below.

## Seal status - read first

**No unopened seal exists. This is NOT a blind test.**

All confirmation seals were consumed before this validation began: cfg109/cfg110
(FAIL, unsealed 2026-08-17) and cfg297/cfg299 (PASS, unsealed 2026-08-19).
Nothing in this report may be described as a blind test, and no sealed
configuration was re-unsealed or tuned against. Any future blind claim requires
a new seal, designed from scratch, DFT-computed, and untouched until one single
unsealing event.

## Threshold table

Every threshold was fixed before the corresponding measurement was made.

| Quantity | Pre-registered | Measured | Status | Note |
|---|---|---|---|---|
| Force MAE (all 227) | < 0.05 eV/A | 0.0012 eV/A | **PASS** | 18x inside target; worst phase Al3Ni 0.0027 |
| Reserved-19 max \|E_rel\| error | <= 2.6183 meV/atom | 2.5232 meV/atom | REPRODUCTION, NOT A GATE | circular: 2.6183 IS the max over these same 19 points across 3 seeds |
| cfg297 \|E_rel\| error (sealed pair) | <= 2.6183 meV/atom | 1.846570 meV/atom | PASS (2026-08-19, seal now CONSUMED) | the only genuine held-out test of this threshold |
| cfg299 \|E_rel\| error (sealed pair) | <= 2.6183 meV/atom | 1.922083 meV/atom | PASS (2026-08-19, seal now CONSUMED) | not re-run here; no unopened seal remains |
| Relaxation \|d(a,b,c)\| | < 0.05 A | max 0.0370 A | **PASS** | 5/5 phases |
| Relaxation \|dV/V\| | < 2% | max 0.199% | **PASS** | 5/5 phases |
| Formation energy sign | all negative | 5/5 negative | **PASS** | QE mu only |
| Pairwise stability ranking | 10/10 vs DFT | 10/10 | **PASS** | tightest pair 19.9 meV/atom gap vs 1.6 meV/atom error |
| Seed-noise floor | 0.43 meV/atom | 0.078 meV/atom spread (3 seeds) | consistent | seed differences are noise, as required |
| Zero-shot reference | 21.23 meV/atom | 21.23 on Pilot-25; 53.51 on all 227 | REGIME-SPECIFIC | see caveat below - not reused across regimes |
| Elastic constants | none pre-registered | see Phase 8 | REPORTED, NOT GATED |  |
| Bulk modulus B0 | none pre-registered | see Phase 5 | REPORTED, NOT GATED |  |
| Dynamical stability | no imaginary modes | 5/5 phases stable | **PASS** |  |
| Vacancy formation energies | none possible (no DFT truth) | see Phase 10 | REPORTED, NOT GATED | model prediction only |
| Al3Ni5 alpha angle | none pre-registered | 96.478 -> 98.248 deg (+1.77) | REPORTED, NOT GATED | known defect, independently reproduced |

**Threshold-discipline caveat.** The pre-registered *zero-shot reference* of
21.23 meV/atom is the base model's worst error **on the Pilot-25 subset only**
(`AlNi_iso_m02`). On the full 227-configuration set the zero-shot worst error is
**53.51** meV/atom, and on Dataset-100 it is 35.73. Reusing 21.23 as an anchor
for the 227 regime would violate the rule against carrying a threshold across
regimes, so it is reported for its own regime and not applied elsewhere.

**The reserved-19 comparison is circular and is not a gate.** The 2.6183 bar was
*derived* as the maximum, across seeds 20260811/812/813, of each seed's own maximum
over these same 19 configurations. Observing that seed 20260811's reserved-19
maximum (2.5232) is <= 2.6183 is therefore true by construction - 2.6183 is
max(2.5232, 2.4333, 2.6183). It demonstrates that the derivation reproduces exactly,
which is a real and valuable integrity result, but it tests nothing.

**The only genuine held-out test of the 2.6183 threshold was cfg297/cfg299**, which
were sealed when the bar was locked and were unsealed once, on 2026-08-19, giving
1.846570 and 1.922083 meV/atom - both passing. **Those seals are now consumed.**
They were not re-run in this validation and could not be: re-reading a consumed seal
would add no evidence. Consequently **no unopened held-out test of this model
remains**, and any future blind claim needs a new seal built from scratch.

## Phase 1 - Integrity

- Datasets `combined227` all/train/validation: **227 / 189 / 18**, and all three
  SHA256 match the values recorded in `AL3NI_COMBINED227_MERGE_STATUS.txt`.
- `al3ni_combined227_lora_v1.model` SHA256 `e4fd54cc...` **matches the hash pinned
  in the unsealing record**. The HuggingFace copy (`asiri1/al3ni-mace`) stores its
  LFS blob under that same hash, so the published and local models are identical.
- Base `MACE-MATPES-PBE-0` downloaded fresh: SHA256 `e618ad58...`, 79,471,284 bytes
  - **byte-identical** to the checkpoint recorded in the training provenance.
- Splits derived independently: 189 TRAIN + 18 VALIDATION + 20 RESERVED.
  cfg297/cfg299 are **absent from all 227**, confirming the merge record by direct check.
- Chemical potentials located: `mu_Al = -537.46115182`, `mu_Ni = -4670.57345642` eV/atom (QE/PBE).

### Documented numerical conflict - resolved in favour of the file

The task cited a disagreement between 1.1927/1.5780 and 1.847/1.922 meV/atom for
the cfg297/cfg299 sealed pair, and named `configs/ROUND285_CONFIRMATION_STATUS.txt`.

- **That file does not exist.** The actual record is
  `configs/AL3NI_ROUND285_FINAL_UNSEALING_RESULT.txt`.
- It states **cfg297 = 1.846570** and **cfg299 = 1.922083** meV/atom, threshold
  2.6183, both PASS.
- The values **1.1927 / 1.5780 appear in no status or report document anywhere in
  the archive**; they occur only as coincidental substrings inside MACE training-loss
  JSON lines.
- **Resolution: the file wins. 1.847 / 1.922.**

## Independent reproduction of recorded values

These were recomputed on different hardware, OS and PyTorch version. They are the
strongest available evidence that the original pipeline was honest and reproducible.

| Recorded quantity | Archive value | This validation | Match |
|---|---|---|---|
| Reserved-19 max, seed 20260811 | 2.5232 | 2.5232 | exact |
| Reserved-19 max, seed 20260812 | 2.4333 | 2.4333 | exact |
| Reserved-19 max, seed 20260813 | 2.6183 | 2.6183 | exact |
| Anchoring config, all 3 seeds | cfg060 | cfg060 | exact |
| Combined-220 threshold | 2.3865 | 2.3865 | exact |
| Al3Ni5 relaxed alpha | 98.279 deg (LAMMPS) | 98.248 deg (ASE) | 0.031 deg |
| Stage A ASE anchor, Al3Ni_relaxed | -25138.19240948 eV | -25138.19240948 eV | 4e-9 eV |

The per-seed distributions also match on every quartile (seed 811: min 0.0035,
median 0.2662, p75 0.9297, p90 1.6306).

## Phase 3 - Single-point benchmark (227 DFT geometries, no relaxation)

Energy metric is the project's canonical relative energy,
`E_rel = (E(config) - E(phase_relaxed))/N`, the only energy metric comparable
across models (MACE absolute energies carry a model-dependent per-element offset).

### Three-way model comparison

| model | E_rel_MAE_meV_atom | E_rel_RMSE_meV_atom | E_rel_MAX_meV_atom | F_MAE_eV_A | S_MAE_GPa |
|---|---|---|---|---|---|
| base_MATPES_PBE_0 | 4.1429 | 7.4763 | 53.5123 | 0.0188 | 0.8642 |
| pilot25 | 1.1106 | 1.9749 | 15.5191 | 0.0044 | 0.3116 |
| combined227 | 0.9598 | 1.6103 | 9.7142 | 0.0012 | 0.2143 |
| combined227_seed812 | 1.0375 | 1.7653 | 10.3661 | 0.0013 | 0.2211 |
| combined227_seed813 | 1.0196 | 1.7211 | 10.1229 | 0.0013 | 0.2210 |

LoRA fine-tuning cuts energy MAE **4.3x** and force MAE **15.7x** relative to the
un-fine-tuned base model. combined227 improves on pilot25 in every column.

### Per phase

| phase | n | E_rel_MAE_meV_atom | E_rel_MAX_meV_atom | F_MAE_eV_A | S_MAE_GPa |
|---|---|---|---|---|---|
| Al3Ni | 65.0000 | 1.4206 | 7.6270 | 0.0027 | 0.2349 |
| Al3Ni2 | 38.0000 | 0.7396 | 3.9694 | 0.0010 | 0.2213 |
| Al3Ni5 | 42.0000 | 0.7429 | 2.8056 | 0.0012 | 0.2744 |
| AlNi | 41.0000 | 1.3207 | 9.7142 | 0.0002 | 0.2980 |
| AlNi3 | 41.0000 | 0.2945 | 0.8387 | 0.0002 | 0.0298 |

### Per deformation family

This is the aggregation that originally concealed the biaxial coverage gap.

| family | n | E_rel_MAE_meV_atom | E_rel_MAX_meV_atom | F_MAE_eV_A |
|---|---|---|---|---|
| relaxed | 5.0000 | 0.0000 | 0.0000 | 0.0001 |
| iso | 41.0000 | 1.8629 | 9.7142 | 0.0006 |
| uniaxial | 29.0000 | 0.4725 | 1.6927 | 0.0004 |
| biaxial | 32.0000 | 1.0108 | 2.4473 | 0.0007 |
| ortho | 33.0000 | 0.8902 | 3.0604 | 0.0007 |
| shear | 20.0000 | 0.2621 | 1.2633 | 0.0010 |
| shear_rattle | 24.0000 | 0.3030 | 2.3758 | 0.0025 |
| rattle | 20.0000 | 0.1491 | 0.3740 | 0.0028 |
| volume_rattle | 23.0000 | 2.1987 | 5.3407 | 0.0025 |

The weakest families are **volumetric** (`volume_rattle` 2.20, `iso` 1.86).
**Biaxial is now mid-pack at 1.01 vs a 0.96 global mean - the historical
biaxial gap is closed.**

### Multi-seed

Three combined-227 seeds (20260811/812/813, identical data and hyperparameters)
differ by **0.078 meV/atom** in overall MAE - far below the 0.43 meV/atom noise
floor. Seed-to-seed differences are noise, not signal.

## Phase 4 - Relaxation and lattice parameters

| phase | a_dft | a_mace | b_dft | b_mace | c_dft | c_mace | dV_over_V_pct | max_abs_dabc_A | PASS |
|---|---|---|---|---|---|---|---|---|---|
| Al3Ni | 4.8255 | 4.8160 | 6.6230 | 6.6067 | 7.3825 | 7.4194 | 0.0553 | 0.0370 | True |
| Al3Ni2 | 4.0449 | 4.0509 | 4.0449 | 4.0509 | 4.9079 | 4.8997 | 0.1317 | 0.0081 | True |
| AlNi | 2.8940 | 2.8947 | 2.8940 | 2.8947 | 2.8940 | 2.8947 | 0.0695 | 0.0007 | True |
| Al3Ni5 | 3.7623 | 3.7978 | 5.0118 | 5.0032 | 5.0118 | 5.0032 | 0.1990 | 0.0355 | True |
| AlNi3 | 3.5673 | 3.5673 | 3.5674 | 3.5674 | 3.5674 | 3.5674 | 0.0000 | 0.0000 | True |

All five phases pass both gates. The ready-to-paste model-card block is
`results/lattice_table_for_hf_card.md`.

**Al3Ni5 alpha angle: 96.478 -> 98.248 degrees (+1.77).** Outside the
pre-registered gates, which cover only a, b, c and V, so it is marked
`REPORTED, NOT GATED` rather than judged against an invented bar. It is a known
defect: the archive's LAMMPS relaxation gives 98.279 deg, agreeing with this
independent ASE run to 0.031 deg.

## Phase 5 - Equation of state

| phase | V0_dft_ref_A3 | V0_mace_fit_A3 | dV0_pct | B0_mace_GPa | B0_dft_GPa | dB0_GPa | fit_max_resid_meV_atom |
|---|---|---|---|---|---|---|---|
| Al3Ni | 235.9406 | 236.0382 | 0.0414 | 119.4429 | 114.0623 | 5.3806 | 0.0572 |
| Al3Ni2 | 69.5414 | 69.6061 | 0.0931 | 136.6923 | 132.7692 | 3.9231 | 0.0196 |
| AlNi | 24.2381 | 24.2714 | 0.1371 | 145.7813 | 159.1128 | -13.3315 | 0.0761 |
| Al3Ni5 | 93.8981 | 94.0830 | 0.1969 | 163.4910 | 168.6554 | -5.1644 | 0.1046 |
| AlNi3 | 45.3978 | 45.3920 | -0.0128 | 182.1376 | 181.5481 | 0.5895 | 0.0708 |

- **Same minimum:** V0 agrees to <= 0.20% in every phase.
- **Comparable curvature:** yes for 4/5. **AlNi is 8.4% too soft** (145.8 vs
  159.1 GPa) - the largest EOS discrepancy, consistent with AlNi being a weak
  phase in Phase 3 and with `iso` being the second-worst family.
- **No kinks:** Birch-Murnaghan residuals <= 0.11 meV/atom.

DFT overlay points are restricted to genuine isotropic scalings inside the same
0.90-1.10 V0 window as the MACE scan. An earlier version of this analysis
wrongly admitted the `volume_rattle` family (scaled cell, rattled positions),
which produced several energies at one volume and an unphysical B' of -1.35 for
Al3Ni5; that was an artefact of the analysis, not of the model.

## Phase 6 - Distortion scans and the strain-error relationship

All 15 scans (5 phases x uniaxial/biaxial/shear, +-4%) are smooth,
single-minimum and kink-free, with correct compression/expansion asymmetry.
Shear is exactly symmetric in +-epsilon, as lattice symmetry requires.

| \|linear strain\| | n | mean \|error\| meV/atom | max \|error\| meV/atom |
|---|---|---|---|
| 0-1% | 136 | 0.4371 | 3.0604 |
| 1-2% | 40 | 0.9476 | 2.4473 |
| 2-3% | 23 | 1.2662 | 3.5278 |
| 3-4% | 11 | 1.9689 | 4.6930 |
| >4% | 17 | 4.1024 | 9.7142 |

Error grows monotonically with strain magnitude - the single most useful
reliability relationship in this validation, and the basis of the Phase 14 tool.

**Historically weak regions.**

- *Al3Ni high expansion (+3.0 to +4.5%)* remains the weakest region: MAE 2.365,
  max 2.745 meV/atom, versus 1.421 for Al3Ni overall and 0.960 globally. Two of
  those five configurations exceed the 2.6183 bar **and are TRAIN members** - the
  model cannot fit its own training data there to within the acceptance bar.
  This is not a gate violation (the bar governs held-out confirmation configs)
  but it is the sharpest remaining defect.
- *Biaxial in all phases* is no longer a gap: 1.011 mean vs 0.960 all-family.
  Only AlNi biaxial stands out at 1.942, consistent with AlNi's soft EOS.

## Phase 7 - Formation energy (QE chemical potentials only)

| phase | x_Ni | Ef_dft_eV_atom | Ef_mace_eV_atom | dEf_meV_atom | sign_correct |
|---|---|---|---|---|---|
| Al3Ni | 0.25000 | -0.39673 | -0.39780 | -1.07195 | True |
| Al3Ni2 | 0.40000 | -0.59645 | -0.59724 | -0.78933 | True |
| AlNi | 0.50000 | -0.63840 | -0.63681 | 1.58690 | True |
| Al3Ni5 | 0.62500 | -0.54684 | -0.54658 | 0.26084 | True |
| AlNi3 | 0.75000 | -0.41658 | -0.41685 | -0.27234 | True |

**Gate 1** all five negative: PASS. **Gate 2** pairwise ranking: **10/10** agree - PASS.

Stability order is identical in DFT and MACE: AlNi < Al3Ni2 < Al3Ni5 < AlNi3 < Al3Ni.
The tightest pair (Al3Ni vs AlNi3) has a 19.9 meV/atom DFT gap against a
1.6 meV/atom worst-case error - a 12x margin, so the ranking is not marginal.

## Phase 8 - Elastic constants (REPORTED, NOT GATED)

| phase | C11 | C12 | C44 | K_VRH_GPa | G_VRH_GPa | E_VRH_GPa | nu | born_stable |
|---|---|---|---|---|---|---|---|---|
| Al3Ni | 165.89 | 105.32 | 58.61 | 119.93 | 51.71 | 135.64 | 0.31 | True |
| Al3Ni2 | 233.53 | 89.02 | 79.70 | 135.15 | 80.97 | 202.47 | 0.25 | True |
| AlNi | 169.84 | 132.04 | 108.68 | 144.64 | 55.12 | 146.72 | 0.33 | True |
| Al3Ni5 | 258.25 | 120.22 | 32.11 | 161.52 | 70.35 | 184.30 | 0.31 | True |
| AlNi3 | 242.61 | 149.76 | 130.67 | 180.71 | 86.36 | 223.48 | 0.29 | True |

All five phases are Born-stable. Two independent consistency checks pass:

1. **K(VRH) vs B0(EOS)** - unrelated routes to the bulk modulus - agree within
   2.0 GPa in every phase.
2. **ASE/MACE vs the archive's LAMMPS ML-IAP run on the same model** agrees to
   **<= 1.04 GPa on every entry** (<= 0.39 GPa apart from Al3Ni5's soft C44).

**Methodological note.** An initial run using `fmax = 0.01` for the internal
relaxation produced low-symmetry phases about 10 GPa too stiff. The signature was
that cubic AlNi and AlNi3, which have no internal degrees of freedom, matched the
archive exactly while 16-atom Al3Ni did not. Converged at `fmax = 0.001`; the
values above are the corrected ones.

**Al3Ni5 C44 = 32.1 GPa is anomalously soft**, roughly 3x softer than the same
phase's own C55/C66. Together with the alpha-angle drift (Phase 4) and the
archive's constrained-relaxation energy cost, this is a **third independent
observable of one and the same soft mode** in the yz/alpha direction - not three
separate defects.

## Phase 9 - Phonons

| phase | supercell | n_atoms_supercell | min_freq_THz | max_freq_THz | n_imaginary_modes | DYNAMICALLY_STABLE |
|---|---|---|---|---|---|---|
| Al3Ni | 2x2x2 | 128 | 0.2777 | 12.0101 | 0 | True |
| Al3Ni2 | 3x3x2 | 90 | 0.4150 | 11.7386 | 0 | True |
| AlNi | 4x4x4 | 128 | 0.5502 | 11.0775 | 0 | True |
| Al3Ni5 | 3x2x2 | 96 | 0.2956 | 11.9637 | 0 | True |
| AlNi3 | 3x3x3 | 108 | 0.4963 | 10.0131 | 0 | True |

**No imaginary modes in any phase.** With a Gamma-centred mesh and the acoustic
sum rule enforced, the three Gamma acoustic modes are exactly zero - a further
confirmation of translational invariance. All five phases are dynamically stable,
consistent with their experimental stability; no defect is indicated here.

## Phase 10 - Vacancy formation energies (MODEL PREDICTION - NO DFT GROUND TRUTH)

| phase | site | 2x2x2 | 3x2x2 | 3x3x2 | 3x3x3 | 4x3x3 | 4x4x3 | 4x4x4 | 5x5x5 |
|---|---|---|---|---|---|---|---|---|---|
| Al3Ni | Al | 1.1308 | 1.1257 | nan | nan | nan | nan | nan | nan |
| Al3Ni | Ni | 2.1772 | 2.1705 | nan | nan | nan | nan | nan | nan |
| Al3Ni2 | Al | nan | nan | 2.3496 | nan | nan | 2.3486 | nan | nan |
| Al3Ni2 | Ni | nan | nan | 1.7668 | nan | nan | 1.7621 | nan | nan |
| Al3Ni5 | Al | nan | 2.6305 | nan | nan | 2.6161 | nan | nan | nan |
| Al3Ni5 | Ni | nan | 1.5765 | nan | nan | 1.5750 | nan | nan | nan |
| AlNi | Al | nan | nan | nan | nan | nan | nan | 2.1485 | 2.1450 |
| AlNi | Ni | nan | nan | nan | nan | nan | nan | 0.9616 | 0.9608 |
| AlNi3 | Al | nan | nan | nan | 3.5088 | nan | nan | 3.5083 | nan |
| AlNi3 | Ni | nan | nan | nan | 1.4572 | nan | nan | 1.4551 | nan |

Supercell size convergence:

| phase | site | E_vac_small_eV | E_vac_large_eV | size_convergence_eV | converged_within_50meV |
|---|---|---|---|---|---|
| Al3Ni | Al | 1.1308 | 1.1257 | -0.0051 | True |
| Al3Ni | Ni | 2.1772 | 2.1705 | -0.0067 | True |
| Al3Ni2 | Al | 2.3496 | 2.3486 | -0.0010 | True |
| Al3Ni2 | Ni | 1.7668 | 1.7621 | -0.0047 | True |
| Al3Ni5 | Al | 2.6305 | 2.6161 | -0.0144 | True |
| Al3Ni5 | Ni | 1.5765 | 1.5750 | -0.0016 | True |
| AlNi | Al | 2.1485 | 2.1450 | -0.0035 | True |
| AlNi | Ni | 0.9616 | 0.9608 | -0.0008 | True |
| AlNi3 | Al | 3.5088 | 3.5083 | -0.0006 | True |
| AlNi3 | Ni | 1.4572 | 1.4551 | -0.0021 | True |

`E_vac(X) = E_defect - E_perfect + mu_X`, with mu_X the QE/PBE elemental
potential (same references as Phase 7). The reservoir choice shifts the absolute
value and is stated explicitly rather than left implicit.

**There is no DFT ground truth for these anywhere in the archive.** They are
model predictions and require DFT confirmation before any defect, diffusion or
creep study is built on them.

## Phase 11 - MD stability

Scope (agreed explicitly, bounded by a CPU-only machine): 5 phases x 4
temperatures NVT at 5 ps, plus NPT at 300 K and 900 K. **Trajectories are short,
which bounds the conclusions: this is a stability and drift screen, not a
converged transport or free-energy study.**

| phase | T_target_K | ensemble | T_mean_K | T_std_K | Epot_drift_meV_atom_per_ps | msd_final_A2 | n_escaped_gt_2A |
|---|---|---|---|---|---|---|---|
| Al3Ni | 300 | NVT | 305.821 | 22.370 | 0.284 | 0.019 | 0 |
| Al3Ni | 600 | NVT | 600.005 | 39.049 | -0.878 | 0.038 | 0 |
| Al3Ni | 900 | NVT | 899.426 | 69.002 | 1.992 | 0.065 | 0 |
| Al3Ni | 1200 | NVT | 1189.101 | 75.044 | 0.236 | 0.093 | 0 |
| Al3Ni2 | 300 | NVT | 305.111 | 24.314 | -0.039 | 0.015 | 0 |
| Al3Ni2 | 600 | NVT | 595.981 | 48.586 | -0.682 | 0.029 | 0 |
| Al3Ni2 | 900 | NVT | 915.231 | 74.173 | 0.333 | 0.047 | 0 |
| Al3Ni2 | 1200 | NVT | 1179.398 | 99.437 | 0.533 | 0.063 | 0 |
| AlNi | 300 | NVT | 292.591 | 21.170 | -0.026 | 0.014 | 0 |
| AlNi | 600 | NVT | 598.958 | 38.897 | 0.882 | 0.028 | 0 |
| AlNi | 900 | NVT | 901.224 | 65.708 | -1.152 | 0.049 | 0 |
| AlNi | 1200 | NVT | 1207.588 | 85.871 | -0.080 | 0.061 | 0 |
| Al3Ni5 | 300 | NVT | 293.068 | 24.543 | -0.085 | 0.013 | 0 |
| Al3Ni5 | 600 | NVT | 575.291 | 46.351 | 0.374 | 0.029 | 0 |
| Al3Ni5 | 900 | NVT | 910.345 | 75.931 | 0.702 | 0.047 | 0 |
| Al3Ni5 | 1200 | NVT | 1206.683 | 99.477 | 2.514 | 0.067 | 0 |
| AlNi3 | 300 | NVT | 300.030 | 22.334 | -0.164 | 0.010 | 0 |
| AlNi3 | 600 | NVT | 590.249 | 44.124 | 0.335 | 0.024 | 0 |
| AlNi3 | 900 | NVT | 916.509 | 73.780 | 2.026 | 0.037 | 0 |
| AlNi3 | 1200 | NVT | 1193.929 | 94.371 | -0.909 | 0.045 | 0 |
| Al3Ni | 300 | NPT | 300.010 | 14.792 | -0.076 | 0.022 | 0 |
| Al3Ni | 900 | NPT | 900.172 | 40.980 | 1.191 | 0.093 | 0 |
| Al3Ni2 | 300 | NPT | 299.862 | 18.704 | -0.114 | 0.015 | 0 |
| Al3Ni2 | 900 | NPT | 899.831 | 49.734 | 0.335 | 0.058 | 0 |
| AlNi | 300 | NPT | 299.916 | 12.481 | -0.019 | 0.017 | 0 |
| AlNi | 900 | NPT | 900.639 | 45.761 | 0.106 | 0.080 | 0 |
| Al3Ni5 | 300 | NPT | 299.871 | 17.995 | -0.003 | 0.020 | 0 |
| Al3Ni5 | 900 | NPT | 899.862 | 47.290 | 1.000 | 0.060 | 0 |
| AlNi3 | 300 | NPT | 300.008 | 16.831 | 0.027 | 0.015 | 0 |
| AlNi3 | 900 | NPT | 900.101 | 44.865 | -0.344 | 0.052 | 0 |

### Thermal expansion (from NPT)

| phase | T1_K | T2_K | alpha_volumetric_per_K | alpha_linear_per_K |
|---|---|---|---|---|
| Al3Ni | 300 | 900 | 4.844e-05 | 1.615e-05 |
| Al3Ni2 | 300 | 900 | 3.682e-05 | 1.227e-05 |
| AlNi | 300 | 900 | 4.728e-05 | 1.576e-05 |
| Al3Ni5 | 300 | 900 | 4.323e-05 | 1.441e-05 |
| AlNi3 | 300 | 900 | 4.167e-05 | 1.389e-05 |

## Phase 12 - LAMMPS cross-check

**VERIFIED**, on single-point energy and force agreement - the evidence Phase 12
actually calls for. Derived quantities such as elastic constants are reported
separately below and are *not* used as the primary evidence, because agreement in
a derived quantity does not demonstrate roundoff-level coupling.

From `configs/LAMMPS_STAGE_A_SINGLE_POINT_STATUS.txt` (MACE/ASE vs LAMMPS
`pair_style mliap unified`, same model):

| Structure | Energy difference | Max force difference |
|---|---|---|
| Al3Ni_relaxed (16 atoms) | 7.28e-12 eV (0.000000 meV/atom) | 1.16e-14 eV/A |
| cfg036_Al3Ni_rattle_large (16 atoms) | 3.64e-12 eV (0.000000 meV/atom) | 1.60e-14 eV/A |

That record's **ASE anchor was independently reproduced on this machine**
(Windows, torch 2.12, CPU) against the original (Linux, torch 2.8):

- `Al3Ni_relaxed`: archive -25138.19240948 eV, here -25138.19240948 eV, difference 3.96e-09 eV
- `cfg036_Al3Ni_rattle_large`: archive -25137.95768098 eV, here -25137.95768098 eV, difference 2.78e-09 eV

The coupling is therefore verified transitively at roundoff level: this machine's
ASE == the archive's ASE == the archive's LAMMPS.

*Corroboration (not primary evidence):* the elastic constants computed here in ASE
match the archive's LAMMPS Stage C run to <= 1.04 GPa across all five phases.

## Phase 13 - Out-of-distribution behaviour

### 13.1 Composition OOD - the dangerous failure mode is present

| System | MACE (eV/atom) | QE reference | Error |
|---|---|---|---|
| pure Al fcc (QE-relaxed a=4.038351) | -537.4127 | -537.4612 | **+48.4 meV/atom** |
| pure Ni fcc (QE-relaxed a=3.517938) | -4670.4609 | -4670.5735 | **+112.5 meV/atom** |

The model returns smooth, finite, symmetric, entirely confident values for pure
Al and pure Ni, with **no internal signal that it is out of range** - precisely
the silent-confident-garbage mode. This is why the Phase 14 tool gates on
composition before it computes anything.

It also **quantifies the documented linear-in-Ni-content bias** that makes QE
references mandatory. Using model elemental references would inject an error
rising from 64.5 meV/atom at x_Ni = 0.25 to 96.5 meV/atom at x_Ni = 0.75 - a
**64.1 meV/atom spread, about 80x the 0.80 meV/atom formation-energy MAE actually
achieved with QE mu**.

### 13.2 Configuration OOD - degradation is soft

Every probe stayed finite with no exceptions: isotropic volume 0.80-1.30 V0,
rattle up to sigma = 1.0 A, vacancy clusters up to n = 16, and an Al-Ni dimer
compressed to 0.3 A. Vacancy clusters give 2.23 eV for a single vacancy falling
to ~1.6-1.8 eV per vacancy at n = 8-16, i.e. physically sensible binding.

**Caveat:** the Al-Ni dimer at 0.3 A yields only ~570 eV of total repulsion where
true nuclear repulsion is keV-scale. **The model has no short-range repulsive
core: acceptable for thermal MD, unsafe for radiation damage or collision cascades.**

### 13.3 Distance-to-training-set descriptor - the specified metric does not work

| Formulation | Spearman rho vs \|error\| |
|---|---|
| 3-component equal-weight z-score (**as specified**) | **+0.068** |
| strain-Frobenius alone | +0.668 |
| \|volume deviation\| alone | +0.687 |
| shape-RMSD alone | -0.054 |
| **corrected: strain + volume, RMS-scaled from reference** | **+0.709** |

The specified descriptor is **not predictive**. Its shape/rattle term is
anti-correlated with error because the rattle family has the *largest* shape-RMSD
and the *smallest* error (0.149 meV/atom), so at equal weight it cancels the
genuine signal from strain and volume. Removing that term, and scaling by the
TRAIN RMS measured from the reference rather than mean-centring, recovers a
usable metric. The Phase 14 tool uses the corrected form.

**Blind spot, confirmed by construction rather than asserted:** the adopted metric
uses cell strain only, so configurations sharing a cell are *identical* under it -
rattle-only differences are completely invisible. **63 such matched-cell pairs exist in the dataset.** This is a stronger blind spot than the original design anticipated, and it is unfixed.

## Phase 14 - Screening tool

`results/screening_tool.py`, standalone, prints the verdict first and withholds
energetics entirely for UNRELIABLE inputs. Verified on all four paths:

| Input | Verdict | Behaviour |
|---|---|---|
| pure Ni fcc | UNRELIABLE | energetics withheld, cites the measured +112.5 meV/atom error |
| AlNi equilibrium | RELIABLE | d = 0.000, expected error ~0.22 meV/atom |
| AlNi +6% volume | CAUTION (thin density) | d = 4.049 vs TRAIN p90 = 2.191 |
| L1_2-Al3Ni (wrong prototype) | CAUTION (novel structure type) | refuses to quote a calibrated error |

It distinguishes **extrapolation** from **thin density** from **novel structure
type**, carries the descriptor blind-spot notice in its docstring, and warns
below 1.8 A minimum separation because of the missing short-range core.

## Phase 15 - Development applications

| application | quantity | value | unit | extra | supported_by | NOT_supported_by |
|---|---|---|---|---|---|---|
| Vacancy migration barrier, AlNi3 (Ni-site, NEB CI, 5 images) | migration barrier | 1.1683 | eV | hop 2.522 A; endpoint asymmetry -0.0000 eV | Phase 3 (forces, MAE 0.0012 eV/A), Phase 9 (dynamical stability), Phase 10 (vacancy energetics converged to <10 meV with supercell) | No DFT ground truth exists for any vacancy quantity in this project (Phase 10). The saddle-point geometry is further from the training manifold than any training configuration of this type. Treat the barrier as indicative only; confirm with DFT before any diffusion or creep claim. |
| Antiphase boundary energy, AlNi3 (001), 1/2<110> shift | APB energy | 197.5 | mJ/m^2 | gamma/gamma-prime proper is NOT computable: it requires pure Ni, which the composition gate rejects | Phase 3 (energetics on shear/shear_rattle families, MAE 0.26-0.30 meV/atom - the best-performing families), Phase 4 (AlNi3 relaxes exactly onto the DFT geometry) | No planar-defect configuration of any kind appears in the 227 training configurations. This is a NOVEL STRUCTURE TYPE by the Phase 14 criterion, so no calibrated error bar applies. The (111) APB, which dominates real gamma-prime slip, was not computed here. |
| Generalized stacking fault energy, AlNi3, (001) along 1/2<110> | unstable fault energy (curve maximum) | 1347.0 | mJ/m^2 | 11 points, 0 to b, maximum at f=0.50; full curve in gsfe_alni3_001_110.csv | Phase 3 shear families (lowest error of all families), Phase 8 (C44 = 130.7 GPa for AlNi3, cross-validated vs LAMMPS to 0.01 GPa) | No stacking-fault configuration appears in training. Rigid-shear geometries at large fault vector sit far outside the strain envelope where Phase 6 measured errors rising to 4.1 meV/atom mean. The technologically dominant (111) plane was not computed. |
| High-temperature structural probe, all 5 phases at 1200 K | phases remaining structurally intact | 5/5 | phases | derived from the Phase 11 NVT trajectories | Phase 11 (5 ps NVT, this run), Phase 9 (all phases dynamically stable at 0 K) | 5 ps is far too short to observe a genuine phase transformation or to converge any transport property. Absence of transformation here is NOT evidence of stability. |

## Phase 16 - Data-efficiency curve

Evaluation set is the reserved-20/19, verified held out from the TRAIN **and**
VALIDATION splits of every checkpoint generation. VALIDATION-18 is verified to be
the same 18 configurations in every generation, so both curves are like-for-like.

| N_DFT | n_train | res19_E_MAE | res19_E_RMSE | res19_E_MAX | res19_F_MAE | res19_S_MAE |
|---|---|---|---|---|---|---|
| 25.0000 | 15.0000 | 1.0044 | 1.5017 | 3.4193 | 0.0062 | 0.3020 |
| 100.0000 | 65.0000 | 0.7274 | 1.2093 | 3.0632 | 0.0030 | 0.2446 |
| 113.0000 | 75.0000 | 0.7903 | 1.4559 | 4.7866 | 0.0030 | 0.2679 |
| 127.0000 | 89.0000 | 0.7220 | 1.4240 | 5.2228 | 0.0026 | 0.2279 |
| 129.0000 | 91.0000 | 0.7099 | 1.3876 | 5.0047 | 0.0026 | 0.2246 |
| 211.0000 | 173.0000 | 0.6955 | 1.0805 | 2.8073 | 0.0019 | 0.1934 |
| 218.0000 | 180.0000 | 0.6632 | 1.0344 | 2.7112 | 0.0020 | 0.1878 |
| 220.0000 | 182.0000 | 0.5904 | 0.9247 | 2.3865 | 0.0020 | 0.1846 |
| 227.0000 | 189.0000 | 0.6114 | 0.9381 | 2.5232 | 0.0019 | 0.1898 |

### Anomaly: the 25-configuration pilot scores BEST of all nine on VALIDATION-18

`pilot25` gives val18 MAE **0.4738** and RMSE **0.6294** - better than every later,
larger checkpoint including combined-227 (0.6986 / 1.5343). This is not a typo and
it needs stating, because taken at face value it would say more data made the model
worse. Two things explain it, and neither rescues VALIDATION-18 as a clean measure:

1. **Partial contamination.** Five of the eighteen VALIDATION-18 members are the
   `*_rattle_003` configurations, which are exactly `pilot25`'s own validation set
   (`ni_al_pilot_val_5`), used for its early stopping. All fifteen of Dataset-100's
   validation-15 are also in VALIDATION-18. **VALIDATION-18 is a model-selection
   set for every checkpoint in the series**, not a held-out set for any of them.

2. **The mean is dominated by two configurations.** Broken down, combined-227 is
   far better than pilot25 almost everywhere on this set - on the five rattle_003
   members (0.032 vs 0.403) and at low strain (0.197 vs 0.354). Its worse *mean*
   comes entirely from the two high-strain Al3Ni members, where it is much worse:

   | config | strain | pilot25 | combined227 | seed812 | seed813 |
   |---|---|---|---|---|---|
   | cfg107_Al3Ni_volume_rattle_compression | 0.069 | **0.702** | 5.243 | 5.981 | 6.163 |
   | cfg115_Al3Ni_iso_expansion | 0.092 | **1.785** | 3.594 | 4.538 | 4.068 |

   The gap holds across all three seeds, so it is not seed noise. See limitation 3.

### The plateau claim: confirmed on its own set, refuted on a held-out set

On VALIDATION-18 the energy RMSE genuinely stalls (1.80 / 2.04 / 1.79 / 2.08 /
1.94 / 1.53 - no trend) while force and stress keep improving, exactly as
documented. But VALIDATION-18 is the early-stopping set: training optimises
against it, so it saturates first. On the never-trained reserved-19, **energy
RMSE keeps falling, 1.502 -> 0.938, a 38% reduction.**

**The plateau is an artefact of measuring on the model-selection set.**

### How much DFT does LoRA fine-tuning of MACE actually need for Ni-Al?

- ~100 configurations gets most of the way. 25 -> 100 is the large win
  (force MAE -52%).
- 100 -> 227, a 2.3x increase in DFT cost, buys only **-16% energy MAE** and
  **-37% force MAE**.
- 220 -> 227 changes reserved-19 MAE by **+0.021 meV/atom - about 20x below the
  0.43 meV/atom noise floor**, i.e. statistically indistinguishable. Those seven
  configurations targeted Al3Ni high-expansion, which reserved-19 does not probe.

## Phase 18 - The dilution hypothesis (REFUTED)

Dataset analysis only - no model was trained and no model evaluated; every
number below is a property of the datasets plus the Phase 3 evaluations.

**Hypothesis.** combined-227 loses to pilot25 on cfg107 because the high-strain
signal pilot25 carries in concentrated form is *diluted* across the 189-config
combined-227 TRAIN set. This is the leading candidate explanation for the
pilot25 anomaly reported in Phase 16.

**It fails on every axis it needs.** Al3Ni's share of TRAIN went *up*, not down:

| | pilot25 TRAIN | combined-227 TRAIN |
|---|---|---|
| Al3Ni configurations | 3 of 15 (20.0%) | 54 of 189 (28.6%) |
| Al3Ni compression configs | 1 | 21 |
| max \|strain\|, Al3Ni | 2.00% | 5.60% |

**The decisive test.** combined-227 holds a TRAIN configuration at *exactly*
cfg107's strain (-4.00%). If scarcity of data there were the cause, the model
should do markedly better on the one it trained on. It does not:

| configuration | split | strain | \|error\| meV/atom |
|---|---|---|---|
| `cfg101_Al3Ni_iso_compression` | TRAIN | -4.00% | 5.263 |
| `cfg107_Al3Ni_volume_rattle_compression` | VALIDATION | -4.00% | 5.243 |

Ratio held-out / trained-on = **0.996**. Training on that region buys nothing, so
scarcity of data there cannot be what is wrong. **Verdict: REFUTED** - not merely
unsupported. Full analysis in `results/DILUTION_HYPOTHESIS.md`.

## Corrections applied during validation

Two quantities were computed, found to be physically meaningless on inspection,
and recomputed. Both defects produced runs that exited successfully and printed
confident numbers; neither was caught by an exit code. The superseded outputs are
kept rather than deleted, and the before/after values below are read from those
archived files and the current ones - nothing here is transcribed by hand.

### Phase 11 - NPT barostat compressibility (units)

`scripts/phase11_md.py` passed `compressibility_au=5e-7` to ASE's
`NPTBerendsen`. That argument is documented in atomic units (A^3/eV); 5e-7 is
a bar^-1-scale number, ~2e6 too small. The Berendsen scaling factor was 1.0 to
within 1e-10, so **the cell never moved** - lattice constants changed by ~1e-7 A
over the full 5 ps. The compressibility is now set per phase to 1/B0 using the
Phase 5 bulk modulus, which also makes the barostat time constant equal `taup`
for every phase. Equilibration was repartitioned from 1 ps to 2.5 ps (= 5 tau)
at `taup` = 500 fs, removing a further ~9% systematic bias in alpha at no cost
in trajectory length. The 20 NVT trajectories were unaffected and not re-run.

| phase | alpha_linear before | alpha_linear after | ratio |
|---|---|---|---|
| Al3Ni | 1.456e-11 | 1.615e-05 | 1.11e+06 |
| Al3Ni2 | 1.369e-11 | 1.227e-05 | 8.97e+05 |
| AlNi | 1.907e-11 | 1.576e-05 | 8.27e+05 |
| Al3Ni5 | 1.882e-11 | 1.441e-05 | 7.66e+05 |
| AlNi3 | 2.001e-11 | 1.389e-05 | 6.94e+05 |

The superseded trajectories are in `results/md/_archive_npt_broken/`.

### Phase 15 - Fault-plane relaxation constraint (inverted)

`scripts/phase15_applications.py` constrained the APB and GSFE relaxations
with `FixedPlane(i, (0,0,1))` under a comment reading *"relax only
perpendicular to the fault plane"*. ASE's `FixedPlane` confines an atom **to**
the plane whose normal is that direction - it froze z and left the in-plane
coordinates free, the exact opposite of the stated intent. Every intermediate
shift therefore relaxed back to f=0 or forward to f=1 and the GSFE "curve" was
a step function, so its maximum was not a saddle-point energy at all.
`FixedLine(i, (0,0,1))` implements the intent and is now used.

| quantity | before | after | unit |
|---|---|---|---|
| APB energy | 202.3 | 197.5 | mJ/m^2 |
| unstable fault energy (curve maximum) | 203.5 | 1347.0 | mJ/m^2 |

Measured directly at f=0.5 on the same 96-atom slab: `FixedPlane` gave 0.3
mJ/m^2 with the block sliding -0.6369 A of its imposed +1.2612 A and zero
out-of-plane relaxation; `FixedLine` gave 1347.0 mJ/m^2 with the shift intact
and 0.0750 A of perpendicular relaxation. The corrected curve is continuous
with an interior maximum, and its f=1.0 endpoint reproduces the independently
computed APB energy exactly. The NEB barrier (15.1) and the high-temperature
probe (15.4) use no such constraint and are unchanged.

The superseded outputs are in
`results/applications/_archive_broken_constraint/`.

## Known limitations

1. **No unopened seal exists.** Nothing here is a blind test.
2. **Al3Ni high expansion (+3.0 to +4.5%) is the sharpest defect.** MAE 2.365
   meV/atom, and two TRAIN configurations exceed the 2.6183 acceptance bar - the
   model cannot fit its own training data there to within that bar.
3. **The round-285 densification (220 -> 227) has no demonstrated held-out benefit,**
   and on the available held-out measures it looks slightly worse:
   - It **raised** the reserved-19 maximum from **2.3865 to 2.5232 meV/atom**, and
     raised reserved-19 MAE from 0.590 to 0.611.
   - Reserved-19 **does not contain a single Al3Ni high-expansion configuration**, so
     it cannot register the improvement those 7 structures were added to produce.
     The region the round targeted was therefore never measured on a set that probes it.
   - The only evidence that the round worked is cfg297/cfg299, which were *designed*
     for that region and are now consumed.
   - On the two high-strain Al3Ni **VALIDATION** configurations the 25-configuration
     pilot model is markedly *better* than combined-227, consistently across all
     three seeds: cfg107 0.702 vs 5.243/5.981/6.163 meV/atom, cfg115 1.785 vs
     3.594/4.538/4.068. This is a genuine regression in the very region the extra
     data was meant to fix, and it is unexplained.
4. **Al3Ni5 has a genuine soft mode** in the yz/alpha direction: alpha drifts
   +1.77 deg on relaxation and C44 = 32.1 GPa is ~3x softer than its own C55/C66.
   Whether the true DFT minimum lies at 96.5 or 98.2 deg is **unresolved** - it
   would need a new DFT relaxation, which was out of scope.
5. **AlNi is ~8.4% too soft** in bulk modulus (145.8 vs 159.1 GPa).
6. **The specified distance descriptor is not predictive** (rho = +0.07). The
   adopted replacement is strain-Frobenius alone (rho = +0.668). It **cannot resolve
   rattle-only differences at all** - 63 matched-cell pairs exist.
7. **No short-range repulsive core.** Unsafe for cascades or radiation damage.
8. **Composition OOD fails silently.** Pure Al/Ni return confident wrong values with
   no internal warning; always gate on composition first.
9. **Vacancy energies have no DFT ground truth** and are model predictions only.
10. **Elastic constants and B0 were never pre-registered** and are reported, not gated.
11. **Phase 11 trajectories are short (5 ps)** where run at all - a stability screen,
    not converged thermodynamics or transport.
12. **Absolute energies are not validated** - only relative energies within a phase
    and formation energies against QE mu.

## Conditional verdict

**Phases actually run:** 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 2b.

**Gated and passed:** force MAE, relaxation lattice lengths and volume,
formation-energy sign, pairwise stability ranking (10/10), dynamical stability.

**Explicitly NOT a gate:** the reserved-19 maximum. See the note below.

**Reported, not gated:** elastic constants, bulk moduli, vacancy energies, the
Al3Ni5 alpha angle, thermal expansion.

### Fit for

- Relative energetics, forces and stresses of the five known Ni-Al phases within
  **x_Ni in [0.25, 0.75]**, at strains up to about **+-3%**, where measured error is
  ~0.4-1.3 meV/atom and force MAE ~0.001-0.003 eV/A.
- Lattice-parameter and equation-of-state prediction (V0 to <= 0.2%).
- Formation energies and phase-stability ranking **using QE chemical potentials**.
- Elastic constants for AlNi, AlNi3, Al3Ni, Al3Ni2 (cross-validated against LAMMPS).
- Phonon and dynamical-stability screening.

### Not fit for, without further DFT

- Any composition outside x_Ni in [0.25, 0.75], including the pure elements.
- Strains beyond about +-4%, where error rises to 4.1 meV/atom mean and 9.7 maximum.
- Al3Ni at high expansion (+3.5 to +4.5%) at the 2.6183 meV/atom accuracy level.
- Quantitative Al3Ni5 shear or alpha-angle energetics.
- Radiation damage, collision cascades, or any close-approach regime.
- Defect, diffusion or creep studies relying on vacancy energies, until those are
  confirmed by DFT.
- Novel structure prototypes, which the screening tool marks CAUTION by construction.

## RELEASE_TODO - what to publish to close the reproducibility gap

3 of the 13 validated checkpoints are published; **10 remain**. A checkpoint
counts as validated here only if it carries a SHA256 in
`model_dataset_integrity.json`, i.e. the validation actually loaded it. Every
dataset, split, config and status file they would be evaluated against is
**already** public and verified byte-identical, so nothing else needs uploading.

### Already published - verified byte-identical to the validated copies

Checked on 2026-09-03 against https://huggingface.co/asiri1/al3ni-mace. Each hash below was read from the published blob
and compared with the local SHA256 the validation recorded.

| File | SHA256 | matches validated local |
|---|---|---|
| `al3ni_combined227_lora_v1.model` | `e4fd54cc8a4a090f...` | yes |
| `al3ni_combined227_seed20260812_lora_v1.model` | `4328154a37f55c1b...` | yes |
| `al3ni_combined227_seed20260813_lora_v1.model` | `f676d87f8463a8ff...` | yes |

### Outstanding (10 files, about 120 MB)

| File | Restores |
|---|---|
| `al3ni_combined113_lora_v1.model` | N=113 data-efficiency point |
| `al3ni_combined127_lora_v1.model` | N=127 data-efficiency point |
| `al3ni_combined129_lora_v1.model` | N=129 data-efficiency point |
| `al3ni_combined211_lora_v1.model` | N=211 data-efficiency point |
| `al3ni_combined218_lora_v1.model` | N=218 data-efficiency point |
| `al3ni_combined220_lora_v1.model` | N=220 data-efficiency point; seed 20260811 of the Phase 19 set; the 2.3865 -> 2.5232 regression evidence in limitation 3 |
| `al3ni_combined220_seed20260812_lora_v1.model` | Phase 19: re-derivation of the 2.3865 combined-220 threshold |
| `al3ni_combined220_seed20260813_lora_v1.model` | Phase 19: re-derivation of the 2.3865 combined-220 threshold |
| `dataset100_matpes_pbe_lora_v1.model` | N=100 data-efficiency point |
| `pilot25_matpes_pbe_lora_v1.model` | N=25 data-efficiency point; the three-way comparison; the VALIDATION-18 anomaly breakdown; the Phase 18 dilution analysis |

These restore the data-efficiency curve and the combined-220 threshold
derivation - the results most likely to be independently publishable, since
they answer how much DFT data LoRA fine-tuning of MACE actually needs for
Ni-Al. `pilot25` is the most valuable single file, carrying three separate
analyses on its own. They are staged with a SHA256 manifest in
`work/upload_hf/`; four further checkpoints under `models/` carry no recorded
hash and were never loaded by any phase, so they are deliberately excluded.

### Documentation - no upload required

Add the `core.autocrlf=false` clone instruction to the public README
(`results/README_PROVENANCE_SNIPPET.md` is ready to paste). Without it, any Windows
user attempting to verify the release will see 32 spurious hash mismatches.

---

*Generated by `scripts/phase17_report.py` from the files in `results/`. No value in
this report was transcribed from project documentation.*
