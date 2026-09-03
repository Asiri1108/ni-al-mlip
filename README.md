# Ni-Al MLIP — a fine-tuned MACE potential for the Ni-Al system

A reproducible, physically credible machine-learning interatomic potential
(MLIP) for the five known Ni-Al intermetallic phases, built by LoRA
fine-tuning **MACE-MATPES-PBE-0** on Quantum ESPRESSO / PBE reference data
generated for this project.

The objective was never a low ML validation error on its own. It was a
potential that survives relaxation, equation of state, elastic constants,
phonons, molecular dynamics, LAMMPS deployment and an out-of-distribution
audit — plus an honest statement of where it stops working.

| | |
|---|---|
| **Production model** | `al3ni_combined227_lora_v1` (seed 20260811, LoRA rank 4) |
| **Base checkpoint** | `MACE-matpes-pbe-omat-ft.model` (`ACEsuit/mace-foundations`, release `mace_matpes_0`) |
| **Reference data** | 227 QE 7.6 / PBE configurations — TRAIN 189 / VALIDATION 18 / reserved 20 |
| **Phases** | AlNi (B2), Al3Ni (Pnma), Al3Ni2 (P-3m1), Al3Ni5 (Cmmm), AlNi3 (L1₂) |
| **Accuracy (227 geometries)** | relative-energy MAE **0.96 meV/atom**, force MAE **0.0012 eV/Å** |
| **vs. the un-fine-tuned base** | energy MAE **4.3×** better, force MAE **15.7×** better |
| **Status** | Complete. Independently validated 2026-09-03 (19 phases, separate hardware/OS/PyTorch). No unopened seal remains. |

---

## Model checkpoints

The trained checkpoints are **not** stored in this repository (`models/` is
gitignored). All 13 are on Hugging Face:

**[huggingface.co/asiri1/al3ni-mace](https://huggingface.co/asiri1/al3ni-mace)**

The production model is `al3ni_combined227_lora_v1.model`. The other twelve
exist so that the data-efficiency curve and both acceptance thresholds
(2.6183 and 2.3865 meV/atom) can be re-derived rather than taken on trust.
Every one was verified byte-identical (on 2026-09-03, against the Hugging Face
blob hashes) to the copy the independent validation loaded — hashes in
[`validation/results/model_dataset_integrity.json`](validation/results/model_dataset_integrity.json),
publication record in
[`validation/results/published_models.json`](validation/results/published_models.json).

```
al3ni_combined227_lora_v1.model               sha256 e4fd54cc8a4a090fc9e32d6625269142824bfada8315433127b3aa3118c65cee
al3ni_combined227_seed20260812_lora_v1.model  sha256 4328154a37f55c1ba99c209e978ad76a0f36e5f3d8a41b25c107b27efefe17af
al3ni_combined227_seed20260813_lora_v1.model  sha256 f676d87f8463a8ffcd4fa7d6b81796b5d42b89602267109010316cbdb4c97e6a
```

The first hash also appears inside
`configs/AL3NI_ROUND285_FINAL_UNSEALING_RESULT.txt`, so the published model
can be confirmed to be the exact artifact named in the sealed confirmation
record. The base checkpoint is likewise pinned
(`MACE-matpes-pbe-omat-ft.model`, sha256 `e618ad58…`) in
`configs/pilot25_matpes_pbe_lora_v1_PROVENANCE.txt`.

This repository holds everything the checkpoints are evaluated *against* —
37 datasets and splits, 163 config and status files, 153 scripts — and every
one of those is byte-identical to the copy the validation used.

> The LAMMPS ML-IAP export (`*-mliap_lammps.pt`) is **not** published: it
> carries no independently recorded prior hash and no validation phase
> loaded it. Regenerate it with `scripts/export_lammps_mliap_model.py`.

---

## Before you use this model

Read the **[independent validation report](validation/results/VALIDATION_REPORT.md)**,
in particular its *"Fit for"* and *"Not fit for, without further DFT"*
sections. In short:

**Fit for**

- Relative energetics, forces and stresses of the five known Ni-Al phases
  within **x_Ni ∈ [0.25, 0.75]** at strains up to about **±3 %** (error
  ~0.4–1.3 meV/atom, force MAE ~0.001–0.003 eV/Å).
- Lattice parameters and equation of state (V₀ to ≤ 0.2 %).
- Formation energies and phase-stability ranking **using QE chemical
  potentials** (see the offset finding below).
- Elastic constants for AlNi, AlNi3, Al3Ni, Al3Ni2 (cross-checked against
  LAMMPS).
- Phonon and dynamical-stability screening.

**Not fit for, without further DFT**

- Any composition outside x_Ni ∈ [0.25, 0.75], **including the pure
  elements** — this fails *silently*, returning confident wrong numbers with
  nothing in the output to signal it. Always gate on composition first.
- Strains beyond about ±4 % (error rises to 4.1 meV/atom mean, 9.7 max).
- Al3Ni at high expansion (+3.5 to +4.5 %) at the 2.6183 meV/atom level.
- Quantitative Al3Ni5 shear or alpha-angle energetics.
- Radiation damage, collision cascades, or any close-approach regime — there
  is **no short-range repulsive core**.
- Defect, diffusion or creep studies relying on the vacancy energies, which
  have no DFT ground truth.
- Novel structure prototypes, which the screening tool marks CAUTION by
  construction.

---

## Repository layout

```
configs/      training configs (YAML), per-round design records, and the
              status files that are this project's authoritative record
data/
  datasets/   37 .extxyz datasets and splits + SHA-256 sidecars
  raw_dft/    immutable QE input/output for the diverse pilot
scripts/      153 scripts: dataset design, DFT extraction, gate/leakage
              audits, evaluation, LAMMPS stages, OVITO export
tools/        NIST EAM potentials, QE pseudopotentials
results/      38 result directories (evaluations, LAMMPS stages A–D3,
              coverage audits, unified comparison, OVITO bundle)
validation/   the independent 2026-09 validation: 27 scripts, every
              artefact they produced, and the report
inbox/        Phase-1 primary reports carried from the separate Windows
              machine (see "Two machines" below)
```

Not in the repository (gitignored): `models/`, `runs/`, `logs/`,
`checkpoints/`, `envs/`, `tools/lammps/`, `tools/qe_gpu/`, `data/processed/`,
and the bulk DFT working directories. Paths of the form `/workspace/ni_al/…`
inside status files and configs refer to the RunPod training volume, not to
this checkout.

### Two machines, three environments

Phase 1 (Steps 5–10: MACE-MP-0 zero-shot, atomic-vs-cell relaxation,
Materials Project DFT comparison, the EAM/LAMMPS benchmark) ran on a
separate Windows machine. Its primary reports are preserved verbatim under
[`inbox/`](inbox/) — including `inbox/README.md` and
`inbox/PROJECT_KNOWLEDGE.md`, which are *that machine's* documents, not this
repository's. `configs/NI_AL_DATA_SHOWCASE.md` is this project's later
compilation from that same source, not an independent computation.

Phase 2 (everything from Pilot-25 onwards) ran on a RunPod RTX 4090 volume.
Phase 3 (the independent validation) ran on a third machine, CPU-only.

---

## The scientific record

### 1. DFT reference

All labels come from **Quantum ESPRESSO 7.6, PBE**, GPU-accelerated
(sm_89), with settings locked before production:

- `ecutwfc = 90 Ry`, `ecutrho = 720 Ry`
- `Al.pbe-n-kjpaw_psl.1.0.0.UPF`, `ni_pbe_v1.4.uspp.F.UPF` (SHA-256 pinned,
  verified before every production run)
- Marzari-Vanderbilt smearing, `degauss = 0.010 Ry`
- `conv_thr = 1.0d-10`, `mixing_beta = 0.30`, Davidson diagonalization
- Labels parsed from `data-file-schema.xml` (not text-scraped from
  `qe.out`), Hartree→eV and Bohr→Å, with the stress sign flipped to the
  project's positive-tension ASE/extxyz convention

Full detail, including the k-mesh policy and the `nspin=2` decisions for
elemental Ni and AlNi3: `configs/project_knowledge.md` §2.

### 2. Dataset lineage — 25 → 227 configurations

The dataset was grown by a gate-driven remediation loop, not in one shot.
Each stage closed a specific, measured coverage gap:

```
Pilot-25 (25)          5 phases × 5 config types; fixed 15/5/5 split
  → Dataset-100 (100)  5-Pod QE GPU production, 75/75 configs, 0 failures
      ↳ holdout failure cfg043 (Al3Ni) diagnosed as extrapolation:
        TRAIN had no coverage past a strain ceiling
  → combined-113 (TRAIN 75 / VAL 18)  Al3Ni remediation v1 + round2
  → combined-127 (TRAIN 89)   round3: biaxial, shear_rattle and ortho
                              families were entirely untrained in most phases
  → combined-129 (TRAIN 91)   round4: last 2 fully-untrained gaps
  → combined-211 (TRAIN 173)  round300: full factorial gap-fill, 82 configs,
                              10 pods (the actual "~300 round")
  → combined-218 (TRAIN 180)  rounds 212/213/214: 4 of the 6 remaining
                              EXTRAPOLATION flags + AlNi's thin buckets
  → combined-220 (TRAIN 182)  round220: the last 2 EXTRAPOLATION flags.
                              Zero EXTRAPOLATION and zero Tier-1 buckets
                              project-wide, first time
  → combined-227 (TRAIN 189 / VAL 18 / reserved 20)
                              round285: densify Al3Ni high expansion
                              +3.0…+5.0 % — FINAL
```

Expansion was **deliberately stopped** at combined-220 on 2026-08-17:
VALIDATION RMSE had gone flat and noisy across 129 → 211 → 218 while TRAIN
grew 2.4×. No 300- or 500-structure round ever occurred. Round285 was added
afterwards only because a specific, diagnosed density gap justified it.

Every stage went through the four-gate redundancy / leakage / duplicate
process in `configs/EXPANSION_BATCH_DESIGN_POLICY.md`, with thresholds
re-derived fresh per phase and per round rather than carried over. Round285
found and fixed a gate-design error before it produced a bad result: gate (a)
cannot be a blanket TRAIN-vs-TRAIN reject when the round's whole purpose is
deliberate density.

Coverage-gap history and priority rankings: `results/full_coverage_audit_v1/`.

### 3. Training

LoRA rank 4, `lora_alpha = 1.0`, no multihead finetuning, estimated E0s,
float64 on CUDA, stress-aware weighted loss (E 1.0 / F 10.0 / S 1.0), EMA,
early stopping with patience 20 — the project-standard hyperparameters used
for every checkpoint in the series
(`configs/al3ni_combined227_lora_v1.yaml`).

Training environment: Python 3.12.3, torch 2.8.0+cu128, CUDA 12.8, MACE
0.3.16, ASE 3.29.0, RTX 4090 (`configs/mace_environment_freeze.txt`).

| Checkpoint | TRAIN | VAL RMSE_E (meV/atom) | VAL RMSE_F (meV/Å) | VAL RMSE_σ (meV/Å³) |
|---|---:|---:|---:|---:|
| dataset100 | 65 | 0.70 | 5.97 | 2.13 |
| combined-113 | 75 | 1.8 | 6.1 | 2.4 |
| combined-127 | 89 | 1.6 | 5.5 | 2.0 |
| combined-129 | 91 | 1.7 | 5.6 | 2.1 |
| combined-211 | 173 | 1.7 | 5.1 | 1.8 |
| combined-218 | 180 | 1.9 | 5.0 | 1.9 |
| combined-220 | 182 | 1.7 | 5.0 | 1.8 |
| **combined-227** | **189** | **1.4** | **4.7** | **1.8** |

### 4. The sealed-holdout protocol, and both unsealing events

Acceptance thresholds were **locked before** the corresponding measurement,
and sealed configurations were read exactly once.

**First seal — cfg109 / cfg110 (Al3Ni, s = 4.0 %): FAILED, 2026-08-17.**
Threshold 2.3865 meV/atom, derived from the 19 genuinely independent
reserved-20 members — excluding cfg043, which is design-contaminated: it is
the feedback probe that steered five remediation rounds. Measured
`|error|` = 3.767 and 3.732 meV/atom. Neither was merged into any split.

Two falsification checks ruled out the simpler explanations before any fix
was designed:

- **Seed variance** — combined-220 retrained twice with only the seed
  changed put the noise floor at ~0.43 meV/atom; the FAIL margin is ~3× that.
  (The single-seed threshold itself shifted 0.81 meV/atom across those seeds
  — a real fragility, recorded but not acted on, since a locked threshold is
  not revisable post hoc.)
- **Model capacity** — retrained at LoRA rank 8 and rank 16 with the seed
  fixed. Rank 8 was indistinguishable from noise; rank 16 made both configs
  measurably *worse*, beyond the noise floor. **Capacity hypothesis
  rejected.**

That pointed at a data-density gap rather than a model limit: Al3Ni high
expansion had only three TRAIN rungs across +2 … +5.6 % (s = 2.0, 3.0, 4.6 %),
with a 1.6-point hole exactly where cfg109/cfg110 sat.

**The round285 sealed pair took three attempts, two retired before any DFT
ran:**

1. cfg295 / cfg296 — retired. A reverse-leakage check the original design
   never computed — distance from the sealed pair to *all 15* TRAIN rungs,
   the 8 existing plus the 7 newly approved — found min distance 0.2421
   (cfg287 at +4.0 % to cfg295 at +3.75 %), below round285's own freshly
   derived 0.3269 threshold, and below the policy-cited 0.734644 as well
   (though that older number belongs to a much sparser regime and is not the
   right bar here). Root cause: a sealed interpolation point placed
   *inside* a 0.5-point-dense TRAIN grid is bound to sit ≤ 0.25 points from
   its nearest neighbour — density and seal isolation cannot coexist in the
   same interval.
2. cfg297 / cfg298 — cfg298 retired as descriptor-degenerate with cfg043
   (d_vol/d_strain ~1e-8/1e-9). A seal that clones the feedback probe
   inherits its design contamination. cfg043's exact strain was resolved
   from the frozen manifest and confirmed by geometry inversion: **3.5000 %**
   (an earlier informal "~3.56 %" note was never a computed value).
3. **cfg297 (s = 3.5 %) / cfg299 (s = 3.6 %)** — kept, DFT'd, sealed.

**Second seal — cfg297 / cfg299: PASSED, 2026-08-19.** The threshold was
re-derived to be robust to seed choice this time: the maximum of three seeds'
(20260811/812/813) own per-seed maxima over the reserved-19, **2.6183
meV/atom** — cross-seed spread 0.185, down from 0.808 for combined-220's
single-seed-derived bar, and the anchoring config cfg060 is now identical
across all three seeds instead of shifting identity. At the first-and-only
read: cfg297 `|error|` = 1.847, cfg299 `|error|` = 1.922 meV/atom — **both PASS,
OVERALL PASS, LAMMPS AUTHORISED**.

**No unopened seal remains.** Both were consumed before the independent
validation began. Nothing in this project may currently be described as a
blind test; any future blind claim requires a new seal built from scratch.

### 5. Unified comparison — six methods against one QE/PBE reference

`configs/NI_AL_UNIFIED_COMPARISON.md` (2026-08-21/23) closes a six-method
matrix against a QE/PBE reference computed fresh in that session (elemental
µ_Al/µ_Ni via vc-relax plus an independent final SCF, with elemental Al's
k-mesh independently convergence-tested rather than assumed, and elemental
Ni's `nspin=2` / 0.60 µB / 22×22×22 mesh reused exactly as originally
locked).

| Method | Rel-E MAE (meV/atom) | Rel-E max | Force MAE (eV/Å) | Formation-E MAE (meV/atom) | Volume MAE (%) |
|---|---:|---:|---:|---:|---:|
| MACE-MP-0 Small (zero-shot) | 3.344 | 22.740 | 0.05236 | 58.689 | 0.753 |
| MACE-MATPES-PBE-0 (zero-shot) | 4.143 | 53.512 | 0.03248 | 25.094 | 1.196 |
| **al3ni_combined227_lora_v1** | **0.960** | **9.714** | **0.00189** | 79.592 → **0.95** ¹ | **0.105** |
| Pun-Mishin 2009 (EAM) | 11.055 | 103.258 | 0.05267 | 93.660 | 3.573 |
| Mishin 2004 ipr2 (EAM) | 6.832 | 84.103 | 0.08174 | 105.294 | 1.190 |
| Mishin 2002 (EAM) | 7.280 | 59.770 | 0.11023 | 120.196 | 1.771 |

¹ see the formation-energy finding immediately below. n = 227 for the
relative-energy and force columns; n = 5 phases for formation energy and
volume. Each method uses its **own** elemental references for formation
energy, never another method's.

> **Two force conventions, one number each — not a contradiction.** This
> table's force MAE (0.00189 eV/Å) and the validation report's (0.0012 eV/Å)
> are two independent computations using different force-error conventions;
> they differ by a consistent ~1.6× on *every* model, so the improvement
> ratio over the base model is essentially the same either way (17.2× here,
> 15.7× there). The relative-energy figure is identical to four decimals in
> both (0.9598 meV/atom), which is the cross-check that they are measuring
> the same model on the same geometries. Sources:
> `results/unified_comparison_stepA_v1/mace_summary.csv` and
> `validation/results/VALIDATION_REPORT.md` Phase 3.

Materials Project DFT, carried from Phase 1, is used only as an independent
ranking cross-check and is kept in its own column — never merged into the
QE/PBE numbers.

### 6. The formation-energy offset — resolved

The fine-tuned model's raw pure-model formation-energy MAE (79.6 meV/atom)
initially looked *worse* than zero-shot MACE-MATPES-PBE-0 (25.1). It is not
a compound-description weakness.

The five per-phase signed errors are linear in x_Ni (R² = 0.9931, residual
std 0.96 meV/atom — at the project's own k-convergence noise floor), the
algebraic signature of **two wrong elemental references**, not five
independent compound errors. This was confirmed directly, not merely
inferred: evaluating the model on the actual QE-relaxed elemental Al/Ni
cells gives δ_Al = 48.44 and δ_Ni = 112.54 meV/atom, matching the fit's
46.13 / 112.39 to within a few meV. δ_Ni running ~2.4× δ_Al tracks the same
Ni-magnetism sensitivity raised repeatedly elsewhere in this project.

Pairing the model's own compound energies with **QE/PBE's own** µ_Al =
−537.46115182 and µ_Ni = −4670.57345642 eV/atom — justified because the
model is QE-calibrated and in-domain on compounds but was extrapolating on
isolated elements it never trained on — collapses the formation-energy MAE
from 79.6 to **0.95 meV/atom**, inside the noise floor. Phase-stability
ordering against QE/PBE was exact under *both* schemes (Spearman ρ = 1.0,
pairwise 10/10), so ranking was never disturbed; only absolute formation
energies were.

**Use guidance:**

- MD, forces, relative energies — validated, unchanged by this finding.
- Formation energy — valid to ~1 meV/atom **only when paired with QE/PBE's
  own elemental references**. Do *not* use the model's own elemental
  predictions; that pairing is exactly the 79.6 meV/atom failure mode. The
  pure-model numbers are kept on record but superseded as the recommended
  figure.
- **Clearest next improvement:** elemental Al and Ni were never in the
  fine-tuning set (only the five alloy phases were). Adding them would let
  the model supply its own accurate µ and remove the need for the hybrid.

### 7. LAMMPS deployment — Stages A through D-3

**Build.** An initial `mliap_python` build (PKG_PYTHON + PKG_ML-IAP, no
Kokkos) was a dead end: mace 0.3.16's ML-IAP ghost-atom feature exchange
(`forward_exchange` / `reverse_exchange`) is implemented only on LAMMPS's
Kokkos `MLIAPDataPy` variant — confirmed by grepping the LAMMPS source, not
assumed. Rebuilt with `PKG_KOKKOS` (CUDA, sm_89/Ada89), which is the active
build; commit, full cmake flags, nvcc/gcc versions and the `lmp` sha256 are
recorded in `configs/LAMMPS_MLIAP_KOKKOS_BUILD_STATUS.txt`. Both builds'
Python modules are installed in isolation (`pip install --target`, selected
via `PYTHONPATH`) so they coexist without clobbering each other.

**Export.** `scripts/export_lammps_mliap_model.py` deliberately bypasses
`mace_create_lammps_model --format mliap`'s forced e3nn→cuequivariance weight
conversion, which is broken for this checkpoint and is not needed by the
ML-IAP wrapper class.

| Stage | What | Result |
|---|---|---|
| **A** | Single-point LAMMPS vs. ASE/MACE (the critical export/units check) | **PASS at machine precision** — ~7e-12 eV energy, ~1.6e-14 eV/Å max force, on two structures |
| **B** | 5-phase relaxation vs. DFT | 5/5 relaxed; max volume/atom error **0.216 %** (Al3Ni5); symmetry preserved 5/5; LAMMPS vs. direct ASE/MACE agreed to 0.00000 % |
| **C** | Full Cij, moduli, Born stability, all 5 phases | **5/5 mechanically stable** (general eigenvalue test, plus cubic-specific for AlNi/AlNi3) |
| **D** | 300 K MD, 15 ps NVT + 15 ps NPT, primitive cells | **5/5 STABLE**, no flags |
| **D-2** | Supercell NPT (AlNi 128, AlNi3 108, Al3Ni2 135 atoms) | **3/3 STABLE**; thermal expansion +1.0…+1.4 % over 0→300 K |
| **D-3** | Trajectory dumps for 3 phases (AlNi 128, Al3Ni5 144, Al3Ni 128 atoms); partial RDF over all 5 | 151 frames each; **chemical order PRESERVED in all 5 phases** (the other two phases' RDFs come from their Stage D / D-2 endpoints) |

Stage A required four real fixes beyond the Kokkos rebuild — Kokkos-specific
LAMMPS/mace API calls and cmdargs, a missing `cupy` dependency, dropping
`lmp.finalize()` after a reproducible Kokkos/torch/cupy CUDA-teardown
segfault, and correctly slicing owned atoms out of Kokkos's ghost-padded
`extract_atom` arrays — all documented inline in
`scripts/lammps_stage_a_single_point.py`. Process isolation in Stages B and C
is load-bearing for the same reason: `lmp.finalize()` is unsafe, so each
phase must exit its own process rather than share one.

**Elastic constants (Stage C)** — finite-difference stress-strain at δ = 0.75 %,
all six Voigt modes, both signs, at each phase's own LAMMPS zero-stress cell:

| Phase | K (GPa) | G (GPa) | E (GPa) | ν | Reference comparison |
|---|---:|---:|---:|---:|---|
| AlNi (cubic) | 144.67 | 55.15 | 146.79 | 0.331 | C11 **−26.1 %** vs a DFT reference; C12 +5.9 %, C44 −6.1 % |
| Al3Ni (ortho) | 119.84 | 51.69 | 135.58 | 0.312 | **UNVALIDATED** — no DFT or literature reference exists |
| Al3Ni2 (hex) | 135.18 | 81.15 | 202.86 | 0.250 | **UNVALIDATED** |
| Al3Ni5 (Cmmm) | 161.61 | 70.32 | 184.24 | 0.310 | **UNVALIDATED**; C44 = 33.15 GPa, ~3× softer than its own C55/C66 |
| AlNi3 (cubic) | 180.81 | 86.45 | 223.69 | 0.294 | C11 +8.5 %, C12 +0.7 %, C44 +5.1 % vs an experimental mean |

**The Al3Ni5 soft mode is a genuine, twice-observed feature.** Stage B found
its alpha angle relaxing to 98.28° against DFT's 96.478°; a follow-up
diagnostic constrained it back and measured a real energy cost of
+0.873 meV/atom, about 2× the measured cross-seed noise floor. Stage C's
C44 = 33.15 GPa is the same yz/shear direction, independently and
quantitatively confirming it as a soft elastic mode rather than a one-off
energetic quirk. **Whether the true minimum lies at DFT's 96.478° or near the
model's 98.28° is unresolved** — settling it needs a new DFT relaxation. The
independent validation reproduced the displacement from a different code path
(ASE, 98.248°, agreeing with LAMMPS to 0.031°).

**Chemical order (Stage D-3 partial RDF, 0 K DFT vs. 300 K MD):** AlNi's
CN_AlNi holds at exactly 8.00 and AlNi3's at exactly 12.00, with
g_AlAl/g_NiNi identically 0.000000 at the 300 K first-shell distance — no
antisite population. All five phases: **no disordering signature**. This is a
check no earlier stage could have caught; energy, force, elastic and
positional-stability agreement are all insensitive to which species sits on
which sublattice.

A zero-shot Stage B was also run with the *un*-fine-tuned MACE-MATPES-PBE-0
for a like-for-like before/after
(`results/lammps_stage_b_matpes_pbe0_zeroshot/`). Stages C and D were not run
for the zero-shot model — out of scope; that set is 0 K relax-only.

### 8. OVITO structural bundle

`results/ovito_export/` — 102 files of real simulation output (nothing
synthetic or placeholder): DFT-relaxed cells (5), LAMMPS 0 K relaxed cells
fine-tuned (12) and zero-shot (10), MD endpoints (26), supercells for all
five phases (10), three 151-frame trajectories, and total plus partial RDFs.
Every `.data` file uses the project's fixed `ELEMENT_ORDER = ["Al","Ni"]`
convention (type 1 = Al, type 2 = Ni); the `.extxyz` conversions carry real
chemical symbols. Full inventory, including which DFT/LAMMPS pairs are
atom-count-comparable and which are supercells that are not:
[`results/ovito_export/README.md`](results/ovito_export/README.md).

### 9. Independent validation (2026-09-03)

[**validation/results/VALIDATION_REPORT.md**](validation/results/VALIDATION_REPORT.md)
— 19 phases run on **separate hardware, OS and PyTorch version** (Python
3.13.7, torch 2.12.1+cpu, Windows 11, CPU-only) against checkpoints and
datasets verified byte-identical to the published ones. Every number in it
was recomputed from the model and DFT files on disk; none was transcribed
from project documentation. The scripts and every artefact they produced are
in [`validation/`](validation/).

Coverage: dataset and checkpoint integrity, a 227-geometry single-point
benchmark, relaxation and lattice parameters, equation of state, distortion
scans, formation energy, elastic constants, phonons, vacancy energetics,
20 NVT + 10 NPT MD trajectories, a LAMMPS cross-check, an
out-of-distribution audit, a screening tool, development applications (NEB
vacancy barrier, APB, GSFE, high-T probe), and a nine-checkpoint
data-efficiency curve.

**Gated and passed:** force MAE (0.0012 against a < 0.05 eV/Å bar),
relaxation lattice lengths and volume, formation-energy sign, pairwise
stability ranking 10/10, dynamical stability 5/5.
**Reported, not gated:** elastic constants, bulk moduli, vacancy energies,
the Al3Ni5 alpha angle, thermal expansion.

Three of its findings cut against the project's own earlier account and are
worth pulling out:

- **How much DFT does LoRA fine-tuning of MACE actually need for Ni-Al?**
  About 100 configurations gets most of the way; 25 → 100 is the large win
  (force MAE −52 %). Going 100 → 227, a 2.3× increase in DFT cost, buys only
  −16 % energy MAE and −37 % force MAE.
- **The "plateau" was an artefact of measuring on the model-selection set.**
  On VALIDATION-18 energy RMSE genuinely stalls — but VALIDATION-18 is the
  early-stopping set for every checkpoint in the series, so it saturates
  first. On the never-trained reserved-19, energy RMSE keeps falling,
  1.502 → 0.938, a 38 % reduction.
- **The reserved-19 comparison is circular and is not a gate.** The 2.6183
  bar *is* the maximum over those same 19 points across three seeds, so
  observing that seed 20260811 sits under it is true by construction. It
  proves the derivation reproduces exactly — a real integrity result — but it
  tests nothing. The only genuine held-out test of that threshold was
  cfg297/cfg299, and those seals are consumed.

The validation also **corrected two of its own defects in the open**, both of
which had produced runs that exited successfully and printed confident
numbers: an `NPTBerendsen` `compressibility_au` passed as a bar⁻¹-scale value
where ASE documents atomic units, Å³/eV (~2×10⁶ too small — the cell never
moved and thermal expansion came out six orders of magnitude low), and a
`FixedPlane` constraint used with exactly inverted meaning, which collapsed
the GSFE curve into a step function. The superseded outputs are archived
rather than deleted, each with a README recording the defect and the
evidence.

---

## Known limitations and open issues

From the validation report and `configs/project_knowledge.md` §8:

1. **No unopened seal exists.** Nothing currently reported is a blind test.
2. **Al3Ni high expansion (+3.0 to +4.5 %) is the sharpest defect** — MAE
   2.365 meV/atom, and two TRAIN configurations exceed the 2.6183 bar: the
   model cannot fit its own training data there to within that bar.
3. **Round-285 (220 → 227) has no demonstrated held-out benefit**, and on the
   available held-out measures it looks slightly worse. It *raised* the
   reserved-19 maximum from 2.3865 to 2.5232 meV/atom. Reserved-19 contains
   no Al3Ni high-expansion configuration at all, so it cannot register the
   improvement those seven structures were added to produce. On the two
   high-strain Al3Ni VALIDATION configurations the 25-configuration pilot
   model is markedly *better* than combined-227, consistently across all
   three seeds (cfg107: 0.702 vs 5.243/5.981/6.163; cfg115: 1.785 vs
   3.594/4.538/4.068 meV/atom). **This is a genuine regression in the very
   region the extra data was meant to fix, and it is unexplained.**
4. **Al3Ni5 has a genuine soft mode** in the yz/alpha direction; whether the
   true DFT minimum is at 96.5° or 98.2° is unresolved.
5. **AlNi is ~8.4 % too soft** in bulk modulus (145.8 vs 159.1 GPa), and its
   **C11 is −26.1 %** against a DFT-literature reference (−14.6 % against a
   recalled, not freshly verified, experimental one). AlNi is one of only two
   phases with any elastic reference at all, so this is the project's one
   directly checkable elastic discrepancy — and it is large and unexplained.
6. **Three of five phases have no elastic reference at all** (Al3Ni, Al3Ni2,
   Al3Ni5). Born stability and internal consistency were checked;
   quantitative accuracy was not.
7. **The specified distance-to-training-set descriptor is not predictive**
   (ρ = +0.07). The adopted replacement, strain-Frobenius alone (ρ = +0.668),
   cannot resolve rattle-only differences at all — 63 matched-cell pairs
   exist.
8. **Composition OOD fails silently.** Always gate on composition first.
9. **Vacancy energies have no DFT ground truth** and are model predictions
   only.
10. **Thermal expansion is a two-point estimate, not a fitted CTE**, and all
    three Stage D-2 phases remain effectively unvalidated against literature:
    AlNi's "verified" reference is a NiAl-Mo composite average over the wrong
    temperature range, AlNi3's is recalled but not session-verified (primary
    source bot-blocked), and Al3Ni2 has no reference at all. Only the
    plausibility of the magnitude is established.
11. **MD trajectories are short** (5–15 ps) — a stability screen, not
    converged thermodynamics or transport.
12. **Absolute energies are not validated** — only relative energies within a
    phase, and formation energies against QE µ.

---

## Verifying this release

### The CRLF trap — read this first on Windows

Artifacts here are line-ending sensitive: the `.extxyz` datasets and the
`configs/*` status files are hashed and cross-referenced by SHA-256
throughout the project, and several of those hashes are pinned inside status
files as integrity records.

**Clone with `core.autocrlf` disabled**, or every text artifact's hash will
differ from the recorded value:

```bash
git -c core.autocrlf=false clone https://github.com/Asiri1108/ni-al-mlip.git
git -c core.autocrlf=false clone https://github.com/Asiri1108/NiAl_MACE.git
```

This is not hypothetical. The independent validation's first hash comparison
reported **32 of 43 artifacts as DIFFERENT** — all 32 false positives caused
by git's autocrlf rewrite on checkout, which adds one byte per line to every
text file. The tell is unmistakable once you look for it: the checked-out
`data/datasets/ni_al_combined227_dft.extxyz` comes out exactly **2,266 bytes**
larger than the recorded size, precisely its line count (227 × 2 header lines
+ 1,812 atom lines).

To confirm a correct checkout:

```bash
sha256sum data/datasets/ni_al_combined227_dft.extxyz
# expected: 9051860ae83dea782d9e5e49e4bf68f992103eed703ad81ca1ded5ea98db29eb
```

That value is also recorded in `configs/AL3NI_COMBINED227_MERGE_STATUS.txt`,
together with the TRAIN(189) and VALIDATION(18) split hashes.

### On reproducibility

Retraining from `configs/al3ni_combined227_lora_v1.yaml` is **not** expected
to regenerate the published model bitwise. The config sets a seed but no
determinism controls, training runs on CUDA, and the toolchain (Python
3.12.3, torch 2.8.0+cu128, CUDA 12.8, RTX 4090) is pinned by documentation
rather than by a container. This is normal for GPU training and is not a
defect.

The reproducibility claim that *is* supported is **statistical**: three
independent seeds (20260811/812/813) trained on identical data and
hyperparameters agree to **0.078 meV/atom** in overall error, well inside the
measured 0.43 meV/atom seed-noise floor. All three checkpoints are published,
so you can recompute this yourself — and with it the 2.6183 meV/atom
acceptance threshold, which is the maximum of the three seeds' reserved-19
maxima (2.5232 / 2.4333 / 2.6183).

---

## Documentation map

Start here, then go deeper as needed.

| Document | What it is |
|---|---|
| **this README** | the whole project in one place |
| [`validation/results/VALIDATION_REPORT.md`](validation/results/VALIDATION_REPORT.md) | **the independent 19-phase validation — the authoritative statement of what this model can and cannot do** |
| [`validation/README.md`](validation/README.md) | how the validation was run, and its two self-corrections |
| [`configs/project_knowledge.md`](configs/project_knowledge.md) | the working technical record: DFT methodology, dataset lineage, gate methodology, sealed-label policy, training approach, open issues |
| [`configs/NI_AL_FINAL_PROJECT_RECORD.md`](configs/NI_AL_FINAL_PROJECT_RECORD.md) | dated timeline and every results table, each cited to a file on disk, with unverifiable figures marked **UNVERIFIED** rather than filled in |
| [`configs/NI_AL_UNIFIED_COMPARISON.md`](configs/NI_AL_UNIFIED_COMPARISON.md) | the six-method comparison matrix and the formation-energy offset analysis in full |
| [`configs/NI_AL_DATA_SHOWCASE.md`](configs/NI_AL_DATA_SHOWCASE.md) | this project's compilation of the Phase-1 (Windows machine) results |
| [`configs/EXPANSION_BATCH_DESIGN_POLICY.md`](configs/EXPANSION_BATCH_DESIGN_POLICY.md) | the four-gate design policy every expansion round had to pass |
| [`validation/results/DILUTION_HYPOTHESIS.md`](validation/results/DILUTION_HYPOTHESIS.md) | the dilution hypothesis, tested and refuted |
| [`validation/results/PROVENANCE_DIFF.md`](validation/results/PROVENANCE_DIFF.md) | what the archive records vs. what was measured |
| [`results/ovito_export/README.md`](results/ovito_export/README.md) | the structural and trajectory bundle inventory |
| `configs/ROUND*_*.md`, `configs/*_STATUS.txt` | per-round design records and per-stage status files — the primary sources everything above cites |
| [`inbox/`](inbox/) | Phase-1 primary reports from the separate Windows machine |

**Superseded documents.** Four root-level files were folded into this README
and removed; they remain in git history at commit `ca30c6d` and earlier.

- `PROJECT_STATUS.md` — a 2026-08-10 snapshot stating that foundation-model
  training had not started. True then, long superseded.
  `configs/RESUME_AUDIT.txt` and `configs/SAFE_TERMINATION_CHECK.txt` cite it
  in exactly that historical sense.
- `GITHUB_README_EDITS.md` — a to-do list of README fixes, all now applied
  (the dead `models/…` paths now point at Hugging Face).
- `README_PROVENANCE_SNIPPET.md` — a ready-to-paste block, now the
  "Verifying this release" section above. The copy under
  `validation/results/` is kept, since the validation report and its scripts
  reference it by that path.
- `VALIDATION_REPORT.md` (root) — a stale duplicate that still listed ten
  checkpoints as unpublished, which is no longer true. The current copy is
  `validation/results/VALIDATION_REPORT.md`.

---

## Safety and directory policy

- Treat `data/raw_dft` as **immutable** source data.
- Reproducible scripts in `scripts/`, configurations and the authoritative
  status record in `configs/`, canonical processed data in `data/processed/`
  (not tracked), split datasets in `data/datasets/`.
- Runs, logs, checkpoints and models live only in their dedicated
  directories, all gitignored.
- Superseded results are **archived with a written record of the defect**,
  never silently deleted.
- Never store credentials in this project.
