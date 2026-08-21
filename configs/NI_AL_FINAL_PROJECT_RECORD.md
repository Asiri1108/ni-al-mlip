# Ni-Al Project — Final Project Record

Read-only aggregation, compiled 2026-08-19. Every figure below is cited to
a real file on disk in `/workspace/ni_al` (path in backticks next to the
value). Where a requested figure could not be independently verified from
a primary file on disk, it is marked **UNVERIFIED** rather than filled in
from memory or reconstructed from summary prose. This document does not
introduce any new computation, training, or MD — it is a synthesis of
existing status files, training logs, and result files, produced by five
parallel research passes over the project's on-disk record plus direct
verification of this session's own Stage 9/10 LAMMPS work.

Companion checksum file: `configs/NI_AL_FINAL_PROJECT_RECORD.md.sha256`.

---

## 1. TIMELINE

**Steps 5–10 (MACE-MP-0 zero-shot, atomic-vs-cell relaxation, MP DFT
comparison, EAM/LAMMPS benchmark)** — narratively precede Pilot-25 in the
project's own account. **No independently-dated raw-output file survives
for these specific numbers**; the only file containing them is
`configs/NI_AL_DATA_SHOWCASE.md` (mtime 2026-08-17 10:36:14 UTC), a later
compilation/showcase document, not contemporaneous raw output.
**Original run date: UNVERIFIED beyond "before 2026-08-10"** (narrative
order only — no separate timestamped script output was found).
- Step 5 (MACE-MP-0 zero-shot) — `configs/NI_AL_DATA_SHOWCASE.md` §1.
- Step 6 (atomic-only vs full-cell relaxation) — `configs/NI_AL_DATA_SHOWCASE.md` §2.
- Step 8 (MP DFT formation-energy comparison) — `configs/NI_AL_DATA_SHOWCASE.md` §3.
- Step 9–10 (EAM benchmark: Pun-Mishin 2009, Mishin 2004, Mishin 2002; LAMMPS execution) — `configs/NI_AL_DATA_SHOWCASE.md` §4–5.

**QE/PBE Pilot-25** — 2026-08-10 UTC (`configs/PILOT25_PROVENANCE.txt`,
"Date (UTC): 2026-08-10"). Canonical file
`data/processed/ni_al_pilot_dft_25.extxyz`, 25 configs. LoRA training:
`configs/PILOT25_LORA_TRAINING_STATUS.txt` (mtime 2026-08-11 07:57:26
UTC). Test evaluation: `configs/PILOT25_TEST_EVALUATION_STATUS.txt`
(mtime 2026-08-11 08:16:04 UTC).

**Dataset-100 creation** — `configs/DATASET100_ASSEMBLY_STATUS.txt`
(mtime 2026-08-13 09:12 UTC). 100 structures (18 AlNi, 19 Al3Ni2, 17
AlNi3, 22 Al3Ni5, 24 Al3Ni).

**cfg043 discovery** — 2026-08-13T09:59:08 UTC
(`configs/DATASET100_REGRESSION_ANALYSIS_STATUS.txt`, "Generated UTC:
2026-08-13T09:59:08.102825+00:00"; "Dominant configuration:
cfg043_Al3Ni_volume_rattle_expansion").

**Remediation v1 (cfg101–110) design** — 2026-08-13T10:12:27 UTC
(`configs/AL3NI_REMEDIATION_DESIGN_STATUS.txt`).

**combined-113 merge** — mtime 2026-08-15 14:04:08 UTC
(`configs/AL3NI_COMBINED113_MERGE_STATUS.txt`).

**round3 batch design** — mtime 2026-08-15 15:05:15 UTC
(`configs/ROUND3_BATCH_DESIGN_STATUS.md`).

**combined-127 merge** — mtime 2026-08-16 09:39:48 UTC
(`configs/AL3NI_COMBINED127_MERGE_STATUS.txt`).

**round4 (biaxial) design** — mtime 2026-08-16 10:21:29 UTC
(`configs/ROUND4_BIAXIAL_DESIGN_STATUS.md`).

**combined-129 merge** — mtime 2026-08-16 10:51:07 UTC
(`configs/AL3NI_COMBINED129_MERGE_STATUS.txt`).

**round300 design** — mtime 2026-08-16 11:35:47 UTC
(`configs/ROUND300_DESIGN_STATUS.md`).

**combined-211 merge** — mtime 2026-08-16 17:02:09 UTC
(`configs/AL3NI_COMBINED211_MERGE_STATUS.txt`).

**round212/213/214 design** — round212 mtime 2026-08-16 18:24:48 UTC
(`configs/ROUND212_CLOSE_FINAL4_DESIGN_STATUS.md`); round213 mtime
2026-08-16 18:20:08 UTC (`configs/ROUND213_AL3NI2_ALNI_DESIGN_STATUS.md`);
round214 pod status files 2026-08-16 18:51–18:58 UTC
(`configs/ROUND214_POD_{A,B,C}_STATUS.txt`).

**combined-218 merge** — mtime 2026-08-16 19:12:14 UTC
(`configs/AL3NI_COMBINED218_MERGE_STATUS.txt`).

**round220 design** — mtime 2026-08-17 14:29:32 UTC
(`configs/ROUND220_CLOSE_LAST2_DESIGN_STATUS.md`).

**combined-220 merge** — mtime 2026-08-17 14:32:23 UTC
(`configs/AL3NI_COMBINED220_MERGE_STATUS.txt`).

**Unsealing #1 (cfg109/cfg110) — FAIL** — 2026-08-17T15:18:57.931683 UTC
(`configs/AL3NI_FINAL_UNSEALING_RESULT.txt`). Both configs exceeded the
2.3865 meV/atom threshold (cfg109: 3.767116, cfg110: 3.732003 meV/atom).

**round285 (high-expansion densify) design** — mtime 2026-08-18 14:28:05
UTC (`configs/ROUND285_HIGH_EXPANSION_DENSIFY_DESIGN_STATUS.md`).

**combined-227 merge** — mtime 2026-08-18 17:12:25 UTC
(`configs/AL3NI_COMBINED227_MERGE_STATUS.txt`).

**Unsealing #2 (cfg297/cfg299) — PASS** — 2026-08-19T08:22:16.496488 UTC
(`configs/AL3NI_ROUND285_FINAL_UNSEALING_RESULT.txt`). Both configs
passed the 2.6183 meV/atom threshold (cfg297: 1.846570, cfg299: 1.922083
meV/atom). "LAMMPS AUTHORISED: YES."

**Stage 9 LAMMPS** — 2026-08-19, sequential same-day: Stage A 09:50:55 UTC
(`configs/LAMMPS_STAGE_A_SINGLE_POINT_STATUS.txt`) → Stage B 10:04:46 UTC
(`configs/LAMMPS_STAGE_B_RELAXATION_STATUS.txt`) → Stage C 10:40:29 UTC
(`configs/LAMMPS_STAGE_C_ELASTIC_STATUS.txt`) → Stage D 14:48:32 UTC
(`configs/LAMMPS_STAGE_D_MD_STABILITY_STATUS.txt`) → Stage D-2 15:58:11
UTC (`configs/LAMMPS_STAGE_D2_SUPERCELL_MD_STATUS.txt`) → Stage D-3
(trajectory + chemical-order runs, same day, results under
`results/lammps_stage_d3/` and `results/ovito_export/rdf/partial/`).

**Stage 10 OVITO export** — 2026-08-19 19:40:05 UTC (`results/ovito_export/README.md`
mtime); bundle `results/ovito_export.tar.gz` (899,661 bytes).

---

## 2. RESULTS TABLE

### 2a. Zero-shot baselines

Provenance note applying to 2a and 2b, **updated 2026-08-21**: the original
version of this note (below, preserved for the record) treated the absence
of raw script output on this RunPod volume as meaning these numbers were
unverifiable. That absence has since been explained and independently
corroborated: Steps 5–10 were executed on a **separate Windows machine**
(`D:\Materials_Research\NiAl_MACE`, per `inbox/PROJECT_KNOWLEDGE.md:187`
and the Windows CMD invocations — `cd /d D:\Materials_Research\NiAl_MACE`,
`.venv\Scripts\activate.bat` — throughout `inbox/README.md`), not on this
volume. That machine's primary reports have now been uploaded to `inbox/`
(`inbox/PROJECT_KNOWLEDGE.md`, `inbox/ni_al_step10_final_report.txt`,
`inbox/ni_al_lammps_benchmark_report.txt`, `inbox/ni_al_step8_final_report.txt`,
`inbox/ni_al_mace_vs_mp_dft_report.txt`, `inbox/ni_al_mace_zero_shot.txt`) and
constitute the primary raw-output record for 2a/2b; `configs/NI_AL_DATA_SHOWCASE.md`
is this project's own later compilation from that same source, not an
independent computation.

**Independent corroboration (2026-08-21):** the three EAM potential files
named in `inbox/ni_al_step10_final_report.txt` §5 were freshly re-downloaded
from the NIST Interatomic Potentials Repository into `tools/eam_potentials/`
and their SHA-256 hashes computed directly from the downloaded bytes:

| File | Computed here (2026-08-21) | `inbox/ni_al_step10_final_report.txt` §5 |
|---|---|---|
| Mishin-Ni-Al-2009.eam.alloy | `e0c4b32c...aa4f2915...f8e2f582b` | `e0c4b32c...aa4f2915...f8e2f582b` — **match** |
| NiAl_Mishin_2004.eam.alloy | `15712c13...529a5611` | `15712c13...529a5611` — **match** |
| NiAl02.eam.alloy | `68de13eb...ba767b3b` | `68de13eb...ba767b3b` — **match** |

All three match exactly, including the Pun-Mishin 2009 hash's `aa4f2915`
substring — a value a fabricated record could not reproduce, since it
requires actually hashing that specific real file. This corrects an earlier
transcribed variant of that same hash (`...aa4e2915...`, a single-character
transcription slip) that had been in circulation during this session's own
discussion; the verified, file-matching value is `...aa4f2915...`, per both
the freshly-downloaded file and `inbox/ni_al_step10_final_report.txt`. That
transcription slip was not found written down anywhere on disk in this
repository (including in this document, prior to this edit) — only spoken in
conversation — so no further on-disk correction beyond this note was needed.

The fabrication concern this note originally raised is accordingly
**retracted**. Original note, preserved verbatim below:

> Provenance note applying to 2a and 2b: after exhaustive search (grep for
> "zero-shot", "MP-0", "MATPES", "EAM", "Pun-Mishin", "formation_energ",
> "eam_alloy" across `scripts/`, `configs/`, `results/`, `logs/`, `data/`),
> the **sole on-disk source** for every number in 2a/2b is
> `configs/NI_AL_DATA_SHOWCASE.md` (18,193 bytes, mtime 2026-08-17 10:36).
> No separate raw script output (JSON/CSV/status.txt) backing these Step
> 5–10 tables exists anywhere in the repo. Treat every figure below as
> sourced to that one document, not to an independently-verifiable
> computation log.

**MACE-MP-0 (Small) vs Materials Project DFT** — `configs/NI_AL_DATA_SHOWCASE.md` §1, §3:

| Phase | MP DFT E_f (eV/atom) | MACE-MP-0 relaxed E_f (eV/atom) | Signed error | ΔV/atom |
|---|---:|---:|---:|---:|
| Al3Ni | −0.418776 | −0.460362 | −0.041587 | +2.740% |
| Al3Ni2 | −0.644217 | −0.641073 | +0.003143 | +2.383% |
| AlNi | −0.684901 | −0.690231 | −0.005330 | +2.628% |
| Al3Ni5 | −0.563251 | −0.606098 | −0.042847 | +3.280% |
| AlNi3 | −0.426420 | −0.488036 | −0.061616 | +2.894% |

Aggregate (n=5), `configs/NI_AL_DATA_SHOWCASE.md` §3: **MAE = 0.030905
eV/atom, RMSE = 0.038471 eV/atom**, mean signed error = −0.029647
eV/atom, **ranking agreement: exact, Spearman ≈ 1.0, 10/10 pairwise**,
mean volume error +2.785%, symmetry preserved 5/5.

**MACE-MATPES-PBE-0 vs QE (this project's own DFT)** — `configs/NI_AL_DATA_SHOWCASE.md` §7:

| Metric | Value |
|---|---:|
| Relative-energy MAE | 4.023 meV/atom |
| Relative-energy RMSE | 6.634 meV/atom |
| Max relative-energy error | 21.228 meV/atom (`AlNi_iso_m02`, compression) |
| Mean force MAE | 0.015641 eV/Å |
| Mean force RMSE | 0.023627 eV/Å |
| Mean stress MAE | 0.871511 GPa |

Force MAE per phase, `configs/NI_AL_DATA_SHOWCASE.md` §7:

| Phase | Force MAE (eV/Å) |
|---|---:|
| AlNi | 0.000441 |
| AlNi3 | 0.000879 |
| Al3Ni5 | 0.006676 |
| Al3Ni2 | 0.015993 |
| Al3Ni | 0.054216 |

### 2b. EAM comparison — all 4 methods (+ DFT reference)

Potentials used, `configs/NI_AL_DATA_SHOWCASE.md` §4:

| Potential | Role | Cutoff (Å) | Fitting focus |
|---|---|---:|---|
| Pun–Mishin 2009 | Primary | 6.2872 | General binary Ni–Al + ab initio intermetallic energies |
| Mishin 2004 (ipr2) | Secondary | 6.7249 | γ/γ′ (Ni₃Al) |
| Mishin 2002 | Historical | 5.9541 | B2-NiAl; documented pure-element weakness |

Individual potential-file SHA256 fingerprints are stated in the source to
have been recorded ("SHA256-fingerprinted before use") but the fingerprint
values themselves are **UNVERIFIED — not found on disk**.

Per-phase formation energies, all 5 methods (bold = closest to DFT),
`configs/NI_AL_DATA_SHOWCASE.md` §4:

| Phase | MP DFT | MACE-MP-0 | Pun–Mishin 09 | Mishin 04 | Mishin 02 |
|---|---:|---:|---:|---:|---:|
| Al3Ni | −0.418776 | **−0.460362** | −0.242708 | −0.243823 | −0.267036 |
| Al3Ni2 | −0.644217 | **−0.641073** | −0.362929 | −0.352211 | −0.370819 |
| AlNi | −0.684901 | **−0.690231** | −0.605871 | −0.590420 | −0.533491 |
| Al3Ni5 | −0.563251 | −0.606098 | **−0.540870** | −0.512888 | −0.435295 |
| AlNi3 | −0.426420 | −0.488036 | −0.453978 | **−0.447720** | −0.383452 |

MAE / RMSE / ranking / volume error, `configs/NI_AL_DATA_SHOWCASE.md` §4:

| Method | MAE (eV/atom) | RMSE | Ranking exact | Pairwise | Volume MAE |
|---|---:|---:|---|---:|---:|
| MACE-MP-0 | 0.030905 | 0.038471 | True | 10/10 | 2.785% |
| Pun–Mishin 2009 | 0.117265 | 0.153381 | False | 8/10 | 1.858% |
| Mishin 2004 (ipr2) | 0.126620 | 0.159870 | False | 8/10 | 2.676% |
| Mishin 2002 | 0.149494 | 0.166682 | False | 8/10 | 1.638% |

Runtime (LAMMPS benchmark engine), `configs/NI_AL_DATA_SHOWCASE.md` §5:

| Item | Value |
|---|---:|
| Calculation matrix | 3 potentials × 7 structures × 3 states = 63 states, 0 failures |
| Runtime, Pun-Mishin | 2.71 s / 21 states |
| Runtime, Mishin 2004 | 2.66 s / 21 states |
| Runtime, Mishin 2002 | 2.79 s / 21 states |
| MACE full-cell (7 structures, CPU) | ~117.5 s total (context only, not a precise per-state ratio — stated as such in the source) |

Per-phase EAM runtime breakdown: **UNVERIFIED — not found on disk** (only
the 21-state aggregate per potential is recorded). Identity of the "other
2" of the "seven structures" (only 5 phases are tabulated in §4):
**UNVERIFIED — not identified anywhere in the source file.**

### 2c. Training progression

Checkpoints with no dedicated `*_MACE_TRAINING_STATUS.txt` (combined-220,
combined-227) sourced directly from the raw training log's final
"Error-table on TRAIN and VALID" printout.

| Checkpoint | TRAIN count | VALIDATION RMSE_E (meV/atom) | VALIDATION RMSE_F (meV/Å) | VALIDATION RMSE_stress (meV/Å³) | Source |
|---|---|---|---|---|---|
| dataset100 | 65 | 0.70 | 5.97 | 2.13 | `configs/DATASET100_MACE_TRAINING_STATUS.txt` |
| combined-113 | 75 | 1.8 | 6.1 (rel 3.29%) | 2.4 | `configs/AL3NI_COMBINED113_MACE_TRAINING_STATUS.txt` |
| combined-127 | 89 | 1.6 | 5.5 (rel 2.99%) | 2.0 | `configs/AL3NI_COMBINED127_MACE_TRAINING_STATUS.txt` |
| combined-129 | 91 | 1.7 | 5.6 (rel 3.01%) | 2.1 | `configs/AL3NI_COMBINED129_MACE_TRAINING_STATUS.txt` |
| combined-211 | 173 | 1.7 | 5.1 (rel 2.76%) | 1.8 | `configs/AL3NI_COMBINED211_MACE_TRAINING_STATUS.txt` |
| combined-218 | 180 | 1.9 | 5.0 (rel 2.72%) | 1.9 | `configs/AL3NI_COMBINED218_MACE_TRAINING_STATUS.txt` |
| combined-220 | 182 | 1.7 | 5.0 | 1.8 | TRAIN: `configs/AL3NI_COMBINED220_MERGE_STATUS.txt`; RMSE: `logs/al3ni_combined220_lora_v1/al3ni_combined220_lora_v1_run-20260811.log` |
| combined-227 | 189 | 1.4 | 4.7 (rel 2.55%) | 1.8 | TRAIN: `configs/AL3NI_COMBINED227_MERGE_STATUS.txt`; RMSE: `logs/al3ni_combined227_lora_v1/al3ni_combined227_lora_v1_run-20260811.log` |

### 2d. Probe trajectory (cfg043, cfg115)

Both configs are Al3Ni phase (cfg043_Al3Ni_volume_rattle_expansion,
cfg115_Al3Ni_iso_expansion). Same DFT relative-energy reference at every
checkpoint: cfg043 = 53.383058 meV/atom, cfg115 = 111.229904 meV/atom
(`configs/AL3NI_INTERIM_GATE_STATUS.txt`).

| Checkpoint | cfg043 error (meV/atom) | cfg115 error (meV/atom) | Source |
|---|---|---|---|
| dataset100 (pre-remediation) | 6.598511 | 12.348161 | `configs/AL3NI_INTERIM_GATE_STATUS.txt` |
| combined-113 | 2.875043 | 6.138443 | `configs/AL3NI_INTERIM_GATE_STATUS.txt` |
| combined-127 | 2.152616 | 4.641493 | `configs/AL3NI_INTERIM_GATE_127_STATUS.txt` |
| combined-129 | 2.364592 | 5.294666 | `configs/AL3NI_INTERIM_GATE_129_STATUS.txt` |
| combined-211 | 2.046136 | 4.532842 | `configs/AL3NI_INTERIM_GATE_211_STATUS.txt` |
| combined-218 | 2.680752 | 5.458900 | `configs/AL3NI_INTERIM_GATE_218_STATUS.txt` |
| combined-220 | 3.0402 | 5.8912 | `configs/COMBINED220_RESERVED_EVALUATION_STATUS.txt` |
| combined-227 | **UNVERIFIED** — excluded from the round285 threshold basis as design-contaminated (`configs/ROUND285_SEALED_ACCEPTANCE_CRITERION.txt`), no dedicated evaluation file found with its individual error at this checkpoint | **UNVERIFIED** — same reason | — |

Net trajectory dataset100→combined-113: cfg043 6.598511→2.875043
(−3.72, ~56% reduction, `configs/AL3NI_INTERIM_GATE_STATUS.txt`), then
non-monotonic across 127/129/211/218 (2.15→2.36→2.05→2.68); cfg115
12.35→6.14 (~50% reduction) then similarly non-monotonic (4.64→5.29→4.53→5.46).

### 2e. Seed variance study

Source: `scripts/evaluate_seed_variance_combined220.py`,
`results/seed_variance_combined220_v1/console.log`. Three retrains of
combined-220 (identical data/hyperparameters — LoRA rank 4, lr 0.001, 100
epochs/patience 20 — seed varied only): 20260811 (original), 20260812,
20260813.

| Config | seed811 | seed812 | seed813 | spread (max−min) | std (pop) |
|---|---|---|---|---|---|
| cfg109_Al3Ni_iso_expansion | 3.7671 | 3.3371 | 3.5517 | **0.4300** | 0.1755 |
| cfg110_Al3Ni_volume_rattle_expansion | 3.7320 | 3.2972 | 3.5107 | **0.4348** | 0.1775 |
| cfg043_Al3Ni_volume_rattle_expansion | 3.0402 | 2.6286 | 2.8155 | 0.4115 | 0.1682 |

**Measured noise floor: 0.43 meV/atom** (cfg109/cfg110 spread) —
`results/seed_variance_combined220_v1/console.log`.

Reserved-20 aggregate per seed, same source:

| Seed | RMSE | MAE | MAX | MAX config |
|---|---|---|---|---|
| 20260811 | 1.1289 | 0.7129 | 3.0402 | cfg043_Al3Ni_volume_rattle_expansion |
| 20260812 | 1.2631 | 0.7843 | 3.0802 | cfg075_Al3Ni2_volume_rattle_expansion |
| 20260813 | 1.0854 | 0.7205 | 2.8155 | cfg043_Al3Ni_volume_rattle_expansion |

Reserved-20 MAX spread across seeds: **0.2647 meV/atom** (std=0.1165);
RMSE spread **0.1777** (std=0.0756). "MAX held by same config across all
3 seeds: False" — anchoring config changed identity (cfg043→cfg075→cfg043)
— `results/seed_variance_combined220_v1/console.log`.

Failure-margin context (threshold 2.3865 meV/atom): cfg109/cfg110 FAIL at
all 3 seeds, margins +1.3806/+0.9506/+1.1652 (cfg109) and
+1.3455/+0.9107/+1.1242 (cfg110) — failure margin exceeds the noise floor
at every seed, same source.

Separate note: the round285 threshold derivation
(`configs/ROUND285_SEALED_ACCEPTANCE_CRITERION.txt`, combined-227) reports
its own reserved-19 (excl. cfg043) cross-seed max spread of **0.808
meV/atom** with the anchoring config staying identical (cfg060) across
all 3 seeds — see 2g below.

### 2f. Capacity study

Source: `scripts/evaluate_capacity_test_combined220.py`,
`results/capacity_test_combined220_v1/console.log`. LoRA rank 4/8/16,
seed fixed at 20260811 except rank4's own 3-seed set (reused from 2e).

| Config | rank4_811 | rank4_812 | rank4_813 | rank8_811 | rank16_811 |
|---|---|---|---|---|---|
| cfg109_Al3Ni_iso_expansion | 3.7671 | 3.3371 | 3.5517 | 3.9974 | **4.6961** |
| cfg110_Al3Ni_volume_rattle_expansion | 3.7320 | 3.2972 | 3.5107 | 3.9445 | **4.6484** |
| cfg043_Al3Ni_volume_rattle_expansion | 3.0402 | 2.6286 | 2.8155 | 3.1800 | 3.7114 |

Reserved-20 aggregate by checkpoint, same source:

| Checkpoint | RMSE | MAE | MAX |
|---|---|---|---|
| rank4_seed811 | 1.1289 | 0.7129 | 3.0402 |
| rank4_seed812 | 1.2631 | 0.7843 | 3.0802 |
| rank4_seed813 | 1.0854 | 0.7205 | 2.8155 |
| rank8_seed811 | 1.3028 | 0.8108 | 3.1800 |
| rank16_seed811 | **1.4442** | **0.8740** | **3.7114** |

Noise-floor-gated comparison (baseline rank4_seed811, floor = 2e's
per-config spread): cfg109 rank8 delta=+0.2302 (within noise, floor
0.43); rank16 delta=+0.9290 (**beyond noise**). cfg110 rank8
delta=+0.2125 (within noise, floor 0.4348); rank16 delta=+0.9164
(**beyond noise**) — `results/capacity_test_combined220_v1/console.log`.

**Conclusion (measured, exact):** rank16 worse than rank4 by **+0.9290
meV/atom (cfg109)** and **+0.9164 meV/atom (cfg110)**, both beyond the
0.43 meV/atom noise floor. Rank8 not distinguishable from rank4 within
noise. Direction inconsistent with a capacity-ceiling hypothesis
(bigger rank made held-out error worse) — consistent with mild
overfitting at fixed data size.

### 2g. Both unsealing events

**Event 1 — cfg109/cfg110: FAIL**

Threshold: **2.3865 meV/atom** (per-config, both must pass) —
`configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`.

Derivation: max |relative-energy error| among the **19 genuinely
independent** members of the Dataset-100 TEST+BLIND_HOLDOUT reserved-20,
evaluated on frozen `al3ni_combined220_lora_v1` (fresh 0/20 leakage
recheck against combined-220's TRAIN-182/VALIDATION-18). Anchoring value
belongs to cfg060_Al3Ni5_volume_rattle_expansion (BLIND_HOLDOUT) —
`results/combined220_reserved_evaluation_v1/combined220_reserved_per_config.csv`,
`configs/COMBINED220_RESERVED_EVALUATION_STATUS.txt`.

cfg043 exclusion: genuine BLIND_HOLDOUT member
(`data/datasets/ni_al_dataset100_blind_holdout_manifest.csv` row 83) but
excluded from threshold-setting as design-contaminated — hard-coded as
`REF_IDS[0]` in every `scripts/evaluate_al3ni_interim_gate_*.py`, driven
down every remediation round (6.60→2.88→2.15 meV/atom). Sensitivity:
with cfg043, n=20, max=3.0402 (cfg043); without, n=19, max=**2.3865**
(cfg060) — `configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`. An
earlier same-day lock at 3.0402 (including cfg043) was caught and fixed
before any unsealing occurred (same file).

Actual result (2026-08-17T15:18:57Z) — `configs/AL3NI_FINAL_UNSEALING_RESULT.txt`:

| Config | DFT rel. E (meV/atom) | Pred rel. E (meV/atom) | \|error\| | vs 2.3865 |
|---|---|---|---|---|
| cfg109_Al3Ni_iso_expansion | 66.130933 | 69.898049 | **3.767116** | FAIL (+1.3806) |
| cfg110_Al3Ni_volume_rattle_expansion | 67.719835 | 71.451838 | **3.732003** | FAIL (+1.3455) |

**OVERALL: FAIL.** Model sha256 (precondition-verified in the result
file) = `1c39751f9b0cc5cb3ecd0687e1d2fb5c6ee9f174256654a90b3e66d79f2dc6ee`.

**Event 2 — cfg297/cfg299: PASS**

Threshold: **2.6183 meV/atom** (per-config, both must pass) —
`configs/ROUND285_SEALED_ACCEPTANCE_CRITERION.txt`.

Derivation: cross-seed MAX of each seed's own max over the reserved-19
(cfg043 excluded), on combined-227 (TRAIN 189/VALIDATION 18), seeds
20260811/812/813 (n=19 × n=3):

| Seed | max (meV/atom) | anchoring config |
|---|---|---|
| 20260811 | 2.5232 | cfg060_Al3Ni5_volume_rattle_expansion |
| 20260812 | 2.4333 | cfg060_Al3Ni5_volume_rattle_expansion |
| 20260813 | **2.6183** | cfg060_Al3Ni5_volume_rattle_expansion |

Cross-seed spread 0.1850 meV/atom, anchoring config identical (cfg060)
across all 3 seeds — `configs/ROUND285_SEALED_ACCEPTANCE_CRITERION.txt`.
Exclusions: cfg043 (contaminated), cfg109/cfg110 (consumed 2026-08-17,
round285's optimization target), cfg115 (VALIDATION-role). cfg297/cfg299
themselves: not read, not evaluated, not referenced anywhere in the
derivation.

Actual result (2026-08-19T08:22:16Z) —
`configs/AL3NI_ROUND285_FINAL_UNSEALING_RESULT.txt`, 4 preconditions
re-verified in-script before any sealed label was read:

| Config | DFT rel. E (meV/atom) | Pred rel. E (meV/atom) | \|error\| | vs 2.6183 |
|---|---|---|---|---|
| cfg297_Al3Ni_iso_expansion | 51.463567 | 53.310138 | **1.846570** | PASS |
| cfg299_Al3Ni_volume_rattle_expansion | 55.180725 | 57.102808 | **1.922083** | PASS |

**OVERALL: PASS. LAMMPS AUTHORISED: YES.** Model (seed 20260811) sha256
= `e4fd54cc8a4a090fc9e32d6625269142824bfada8315433127b3aa3118c65cee`
(first pin, no prior independent record). Acceptance-criterion file
sha256 = `7e4fc32a8efa49c0a3a322b2165ed62dde36ca56098c5f6d41af2ebaf949600e`
(verified vs. sidecar `configs/ROUND285_SEALED_ACCEPTANCE_CRITERION.txt.sha256`).

### 2h. Stage 9 — LAMMPS/MACE deployment validation (this session, 2026-08-19)

Model under test: `al3ni_combined227_lora_v1` (the PASSing model from
2g). Build: Kokkos/CUDA LAMMPS (`tools/lammps/install/mliap_kokkos`),
Python mliappy interface — confirmed empirically this session that a
bare `lmp -in <script>` fails with "ValueError: No unified model loaded"
on `pair_style mliap unified EXISTS`, so every run below used the Python
driver path (`configs/LAMMPS_MLIAP_KOKKOS_BUILD_STATUS.txt`).

**Stage A — single-point agreement**, `configs/LAMMPS_STAGE_A_SINGLE_POINT_STATUS.txt`:

| Structure | Energy diff (eV) | meV/atom | Max force diff (eV/Å) |
|---|---:|---:|---:|
| Al3Ni_relaxed (16 atoms) | 7.27596e-12 | 0.000000 | 1.16495e-14 |
| cfg036_Al3Ni_rattle_large (16 atoms) | 3.63798e-12 | 0.000000 | 1.59872e-14 |

**OVERALL: PASS** (machine precision).

**Stage B — relaxation vs DFT, all 5 phases**, `configs/LAMMPS_STAGE_B_RELAXATION_STATUS.txt`:

| Phase | LAMMPS vs DFT vol/atom % err | max \|lattice %\| | Symmetry match | Convergence (fmax, eV/Å) |
|---|---:|---:|---|---:|
| AlNi | +0.1491% | 0.0497% | Y (Pm-3m #221) | 1.965e-09 |
| Al3Ni | +0.0407% | 0.5994% | Y (Pnma #62) | 2.157e-09 |
| Al3Ni2 | +0.1179% | 0.2087% | Y (P-3m1 #164) | 5.321e-10 |
| Al3Ni5 | +0.2159% | 1.8664% (alpha +1.87%) | Y (Cmmm #65) | 2.480e-09 |
| AlNi3 | +0.0037% | 0.0036% | Y (Pm-3m #221) | 7.345e-11 |

Max volume/atom error over all 5 phases: **0.2159% (Al3Ni5)**. Symmetry
preserved 5/5. Al3Ni5's alpha diagnostic (98.279° LAMMPS vs 96.478° DFT,
+0.873 meV/atom cost when constrained) is in
`configs/LAMMPS_STAGE_B_AL3NI5_ALPHA_DIAGNOSTIC.txt`.

**Stage C — full Cij + moduli + Born stability, all 5 phases**,
`configs/LAMMPS_STAGE_C_ELASTIC_STATUS.txt` (finite-difference
stress-strain, δ=0.75%, all 6 Voigt modes, both signs, at each phase's
own LAMMPS zero-stress cell):

| Phase | C11/C44 (or diag) | Born-stable (general) | K (GPa) | G (GPa) | E (GPa) | ν | A^U |
|---|---|---|---:|---:|---:|---:|---:|
| AlNi (cubic) | C11=169.91 C12=132.05 C44=108.68 | Y | 144.67 | 55.15 | 146.79 | 0.3309 | 4.6990 |
| Al3Ni (orthorhombic) | shear diag 58.58/71.94/52.53 | Y | 119.84 | 51.69 | 135.58 | 0.3115 | 0.3782 |
| Al3Ni2 (hexagonal) | shear diag 79.84/79.84/72.50 | Y | 135.18 | 81.15 | 202.86 | 0.2499 | 0.1127 |
| Al3Ni5 (Cmmm) | shear diag **33.15**/102.30/98.05 | Y | 161.61 | 70.32 | 184.24 | 0.3100 | 2.8761 |
| AlNi3 (cubic) | C11=242.89 C12=149.77 C44=130.68 | Y | 180.81 | 86.45 | 223.69 | 0.2938 | 1.3955 |

Born-stable (general, all eigenvalues > 0): **5/5**. Literature
comparison (AlNi, AlNi3 only — the only 2 with any reference):
- AlNi vs DFT-literature (C11=229.8, C12=124.7, C44=115.7): **C11 −26.06%**, C12 +5.90%, C44 −6.07%.
- AlNi3 vs experimental mean (C11=223.9, C12=148.8, C44=124.35): C11 +8.48%, C12 +0.65%, C44 +5.09%.

Al3Ni5's C44=33.15 GPa is ~3× softer than its own C55/C66 (98–102 GPa)
and softer than every other phase's shear constants — same physical
direction as the Stage B alpha displacement, two independent
observables. Al3Ni, Al3Ni2, Al3Ni5: **no elastic reference exists**
(DFT or literature) — model predictions only.

**Stage D — MD stability, all 5 phases, primitive cells**,
`configs/LAMMPS_STAGE_D_MD_STABILITY_STATUS.txt` (300 K, 1 fs, 15 ps NVT
then 15 ps NPT, full triclinic barostat):

| Phase | NPT T back-70% (K) | overall alpha drift (deg) | max\|beta drift\| | max\|gamma drift\| | vol drift (NPT) | Verdict |
|---|---|---:|---:|---:|---:|---|
| AlNi | 323.0±288.5 | −0.4323 | 6.5098 | 8.1937 | +4.62% | STABLE |
| Al3Ni | 297.3±64.4 | +1.5701 | 2.1140 | 3.3491 | +0.70% | STABLE |
| Al3Ni2 | 303.4±117.5 | −3.2395 | 3.9097 | 2.9709 | −1.06% | STABLE |
| Al3Ni5 | 308.4±93.7 | −1.2691 | 2.0372 | 2.1456 | +2.51% | STABLE |
| AlNi3 | 326.3±163.7 | +2.4746 | 4.0219 | 5.9434 | +1.40% | STABLE |

All 5: **STABLE**, no flags. AlNi/AlNi3/Al3Ni2's large T std here (2–4
degrees of freedom effects for 2/4/5-atom primitive cells) is a
statistical artifact, not instability — resolved by Stage D-2/D-3
supercells below.

**Stage D-2 — supercell MD, thermal expansion, MSD**, `configs/LAMMPS_STAGE_D2_SUPERCELL_MD_STATUS.txt`
(single-stage 15 ps NPT, 300 K; formally covers **AlNi, AlNi3, Al3Ni2** only):

| Phase | Atoms | T back-70% (K) | Thermal expansion 0K→300K | Linear CTE (model) | max\|α,β,γ drift\| | MSD Al / Ni final (Å²) | Verdict |
|---|---|---|---:|---:|---|---|---|
| AlNi | 128 | 301.3±23.2 | +1.381% | 15.341e-6/K | 0.89/0.74/0.56 deg | 0.0123 / 0.0191 | STABLE |
| AlNi3 | 108 | 302.7±25.3 | +1.137% | 12.634e-6/K | 0.69/0.58/0.65 deg | 0.0189 / 0.0120 | STABLE |
| Al3Ni2 | 135 | 299.9±21.6 | +1.004% | UNVALIDATED (no reference) | 0.97/0.66/0.65 deg | 0.0167 / 0.0148 | STABLE |

AlNi CTE vs literature: −4.1% vs a NiAl-Mo composite value (16.0e-6/K,
live-verified but not a valid pure-crystal comparison — RT-800°C
composite average), +18.0% vs a recalled/unverified pure-B2 value
(13.0e-6/K). AlNi3 CTE vs a recalled/unverified Ni3Al value (12.5e-6/K):
+1.1%. **Al3Ni5 and Al3Ni were NOT run through this exact protocol** —
they were later given supercells via Stage D-3 (trajectory dumps), which
did not include a `compute msd` or a back-70%-time-averaged CTE
derivation in this same format. Their formal thermal-expansion-
coefficient and MSD figures in Stage D-2's precise sense are
**UNVERIFIED — not computed in this format for these 2 phases** (see
Section 5 note); only their endpoint cellpar/temperature and partial-RDF
derived numbers below exist.

**Stage D-3 — trajectories + chemical order (partial RDF)**,
`results/lammps_stage_d3/*_summary.json`,
`results/ovito_export/rdf/partial/partial_rdf_shell_report.json`,
`results/ovito_export/README.md`. Trajectories: AlNi (128 atoms), Al3Ni5
(144 atoms, 3×3×2 supercell), Al3Ni (128 atoms, 2×2×2 supercell) — 151
frames each, 15 ps NPT/300 K/1 fs, dump every 100 steps, element-named +
unwrapped coordinates.

Partial-RDF first-shell coordination numbers (CN_ab = average b-neighbors
per a-atom), 0 K DFT vs 300 K MD, all 5 phases —
`results/ovito_export/rdf/partial/partial_rdf_shell_report.json`:

| Phase | Structure | CN_AlAl (0K→300K) | CN_AlNi (0K→300K) | CN_NiNi (0K→300K) | Chemical-order verdict |
|---|---|---|---|---|---|
| AlNi | B2 | 6.00→6.00 | **8.00→8.00** (textbook exact) | 6.00→6.00 | **PRESERVED** — g_AlAl/g_NiNi exactly 0.000000 at the 300K first-shell distance (2.525 Å), no antisite |
| AlNi3 | L1₂ | 6.00→6.00 | **12.00→12.00** (textbook exact; CN_NiAl derives to 4.0) | 8.00→8.00 | **PRESERVED** — g_AlAl exactly 0.000000 at 2.525 Å at 300K |
| Al3Ni | Pnma | 6.667→7.771 | 2.667→2.677 | 2.00→1.375 | **PRESERVED** — CN_AlNi (most diagnostic) essentially unchanged, +0.4% |
| Al3Ni2 | P-3m1 | 6.00→6.00 | 3.333→5.321 | 3.00→2.185 | **PRESERVED** — peak positions unchanged; CN shift attributed to shell-boundary integration widening under thermal broadening |
| Al3Ni5 | Cmmm | 2.667→2.111 | **9.333→9.333** (identical to 3 dp) | 6.40→6.756 | **PRESERVED** — best-behaved of the 3 lower-symmetry phases |

**No antisite/disordering signature detected in any of the 5 phases.**
This is a check no earlier stage of the project would have caught (energy/
force agreement, elastic constants, and MD positional stability are all
insensitive to which species sits on which sublattice).

**Stage 10 — OVITO export bundle**, `results/ovito_export.tar.gz`
(899,661 bytes, 92 files on disk under `results/ovito_export/`): dft/ (5),
lammps_0K/ (12, mixed primitive/supercell), md_endpoints/ (26), supercells/
(10, all 5 phases), trajectories/ (3, 151 frames each), rdf/ (5 total +
30 partial), README.md, manifest.json. Full detail:
`results/ovito_export/README.md`.

---

## 3. METHODOLOGY

### The 4-gate design policy

Codified in `configs/EXPANSION_BATCH_DESIGN_POLICY.md`, written after
five consecutive failed/retracted design rounds in the Al3Ni expansion
branch, all traced to the same root cause: "a threshold was either
invented outright, or was correctly derived but then applied outside the
regime it was derived for."

- **Gate (a) — Redundancy (vs existing TRAIN).** Threshold = 5th
  percentile of intra-phase pairwise descriptor distance among existing
  frozen members, recomputed every round/phase. Original Al3Ni value:
  0.794907 (5th percentile of 171 pairwise distances among 19
  Dataset-100 Al3Ni configs — `configs/SESSION_STATE_AL3NI_EXPANSION_DESIGN.md`
  §3). Re-derived for combined-220 as 0.7628
  (`configs/ROUND285_HIGH_EXPANSION_DENSIFY_DESIGN_STATUS.md`).
- **Gate (b) — Leakage (vs sealed holdouts).** Threshold = minimum
  pairwise descriptor distance already accepted between frozen TRAIN and
  HOLDOUT. Original: 0.734644 (min of 52 TRAIN↔HOLDOUT distances,
  minimum pair cfg029↔cfg043 — `configs/SESSION_STATE_AL3NI_EXPANSION_DESIGN.md`
  §3). Only geometry may be read from sealed points while this gate
  runs. Re-derived for combined-220 as 0.3269 against the live RESERVED
  population.
- **Gate (c) — Role-based (matched-strain family pairs).** A
  matched-strain pair (e.g. `iso_expansion` vs `volume_rattle_expansion`
  at the same strain) must share role — the descriptor collapses to a
  rattle-only perturbation and cannot certify independence for such
  pairs. Gate (a)'s threshold applies only to different-role,
  different-strain pairs; same-role/same-strain TRAIN-vs-TRAIN proximity
  is "an efficiency advisory only — informative, never a rejection
  reason" (`configs/EXPANSION_BATCH_DESIGN_POLICY.md`).
- **Gate (d) — TRAIN-vs-VALIDATION placement.** Added to fix the cfg115
  extrapolation failure (Section 4 item 3). Ceiling = loosest nearest-
  TRAIN distance the frozen split already accepted for a VALIDATION
  point (0.628835, from cfg039/cfg040). Floor = matched-strain
  degeneracy scale (0.297055, from cfg111↔cfg112/cfg113↔cfg114). Not the
  gate (a) threshold — "VALIDATION wants to be in-distribution ...
  applying gate (a)'s threshold here was the error in design round 4/5"
  (`configs/SESSION_STATE_AL3NI_EXPANSION_DESIGN.md` §5).

### The descriptor blind spot

Per-config descriptor = {sorted 120-length minimum-image pairwise
distance vector (shape), volume/atom, Green-Lagrange strain tensor},
combined via a z-scored Euclidean distance
(`configs/SESSION_STATE_AL3NI_EXPANSION_DESIGN.md` §3). For a matched-strain
pair, `d_vol` and `d_strain` are exactly zero by construction, so the
descriptor measures only rattle-induced shape perturbation against a
scale calibrated for much larger strain-driven differences — "cannot
resolve rattle-only differences" (same file §4). Produced two documented
false-positive incidents: cfg106/cfg108 (Section 4 item 2) and cfg298 vs
cfg043 (Section 4 item 5).

### The round-size pattern (cfg043/cfg115 probe deltas)

| Round | Size | cfg043 delta | cfg115 delta | Source |
|---|---|---|---|---|
| v1+round2 → combined-113 | 13 configs | 6.60→2.88 (−3.72, ~56%) | — | `configs/project_knowledge.md` |
| round3 → combined-127 | 14 configs | 2.88→2.15 | — | `configs/AL3NI_INTERIM_GATE_127_STATUS.txt` |
| round4 → combined-129 | **2 configs** | **2.15→2.36 (+0.21, regressed)** | **4.64→5.29 (+0.65, regressed)** | `configs/project_knowledge.md` |
| round300 → combined-211 | **82 configs** | **−0.21 (improved)** | **−0.65 (improved)** | `configs/project_knowledge.md` |

Round4 (2 configs, unrelated phases) regressed both probes; round300 (82
configs) reversed both deltas by the identical magnitude in the opposite
direction. Reported as-is per the project's "no-threshold interim-gate
policy, not spun either way."

### Pre-registration discipline

The final acceptance threshold
(`configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`, 2.3865 meV/atom)
was derived and locked from the reserved-20 evaluation **before** the
single designated unsealing event ran — "the threshold is explicitly
locked, not to be revised post hoc." Gate designs are required "frozen
for DFT submission" before any DFT is spent
(`configs/EXPANSION_BATCH_DESIGN_POLICY.md`); cfg109/cfg110 were declared
to unseal "exactly once ... against the final model" before the roadmap
began (`configs/SESSION_STATE_AL3NI_EXPANSION_DESIGN.md` §9). Same
discipline repeated for round285/cfg297/cfg299 (2g above).

---

## 4. ERRORS CAUGHT AND CORRECTED

1. **Invented 2× multiplier.** The "2× redundancy" leakage threshold
   (2 × 0.794907 = 1.5898) and a "2× benchmark" bracket-quality flag were
   both invented, with no basis in the frozen split's own data —
   explicitly listed under "RETRACTED — do not reintroduce"
   (`configs/SESSION_STATE_AL3NI_EXPANSION_DESIGN.md` §3;
   `configs/EXPANSION_BATCH_DESIGN_POLICY.md`).

2. **Descriptor blind spot → cfg106/cfg108 false duplicates.** First-round
   REDUNDANT flags were measurement artifacts: vs nearest Dataset-100
   neighbors, `d_shape=0.0155/0.0222, d_vol=0.0000, d_strain=0.0000` —
   below threshold only because the descriptor is blind to rattle-only
   perturbation (`configs/SESSION_STATE_AL3NI_EXPANSION_DESIGN.md` §4).

3. **Validation point outside envelope.** cfg115 (VALIDATION) was placed
   at +6.30%, above the TRAIN ceiling of +5.60%, because its original
   interior placement (+5.10%) failed gate (c) against 3 surrounding
   TRAIN points (0.6972/0.7005/0.7919, all below 0.794907), and was moved
   past the ceiling "to force a pass" — an extrapolation point
   (`configs/SESSION_STATE_AL3NI_EXPANSION_DESIGN.md` §7). Fixed by
   deriving gate (d) and relocating cfg115 to +5.30% (interior, d=0.4188).

4. **Reverse-leakage miss on cfg295/cfg296.** The original round285
   script "only checked the sealed pair against the RESERVED population
   and a tight duplicate epsilon, never against the newly-approved TRAIN
   candidates at leakage scale." A dedicated reverse-leakage check found
   min distance 0.242091 (cfg287 @ +4.0%) — below both the stale 0.734644
   and round285's own fresh 0.3269 threshold. Root cause: "a sealed
   interpolation point cannot be both inside a densified region and
   isolated from it" (`data/al3ni_remediation_v1/round285_sealed_retirement_log.txt`).
   Both retired before any DFT was spent, replaced by cfg297/cfg298.

5. **cfg298 descriptor-clone of the feedback probe.** cfg298 was found
   descriptor-degenerate with cfg043 (`d_vol=3.14e-08, d_strain=1.19e-09`)
   — a true descriptor collapse. Because cfg043 is the feedback probe
   that steered 5+ remediation rounds, "a seal that is a clone of the
   feedback probe inherits its indirect design contamination and cannot
   serve as an independent test." Replaced by cfg299 (s=3.6%), verified
   non-degenerate against cfg043/cfg109/cfg110/cfg115/cfg297
   simultaneously (`configs/ROUND285_SEALED_PAIR_REVISION2_STATUS.md`).

6. **Single-seed threshold fragility.** The seed-variance study (2e)
   found the threshold itself "shifts ~0.81 meV/atom and changes which
   config anchors it across the same 3 seeds — a real fragility, noted,
   not acted on." The FAIL margin was confirmed robust to this (~3× the
   0.43 meV/atom floor), and the fragility was disclosed rather than
   used to justify a post-hoc revision.

7. **cfg043 strain "3.56%" vs true 3.5000%.** "An earlier pass ... referred
   to cfg043 as sitting at 's~3.56%' ... cfg043's true strain is 3.5000%,
   not 3.56%" (`configs/ROUND285_HIGH_EXPANSION_DENSIFY_DESIGN_STATUS.md`).
   Confirmed two ways: the frozen dataset100 manifest's
   `requested_strain=0.035`, and independently by inverting the
   DFT-relaxed cell's Green-Lagrange trace.

8. **Gate (a) misapplied as blanket TRAIN-vs-TRAIN rejection.** Round285's
   initial implementation "was initially implemented as a blanket
   TRAIN-vs-TRAIN reject (copied verbatim from round220's script), which
   rejected all 10 grid candidates." Re-reading gate (c) confirmed this
   was wrong. Fixed by making gate (a) advisory-only for same-role
   comparisons and moving true-duplicate detection to gate (c) with a
   calibrated epsilon (1e-3 — true duplicate ~1e-7, closest legitimate
   different-strain neighbor ~0.097, closest legitimate matched-strain
   pair ~0.28).

---

## 5. OPEN ISSUES

The 7 items currently recorded as open limitations in
`configs/project_knowledge.md` Section 8, quoted from that file, each
with what would close it:

1. **Stage D-2 thermal expansion is a crude two-point estimate, not a
   measured CTE.** Each phase's linear CTE was derived from exactly two
   points (0 K relaxed cell, 15 ps/300 K NPT volume/atom average), not a
   temperature sweep fit to a curve. **To close:** run NPT at several
   temperatures (e.g. 100/200/300/400 K) and fit a real CTE curve.

2. **AlNi's "verified" literature CTE is not a valid comparison.** The
   live-search-verified number (16.0e-6/K) is a NiAl-Mo eutectic
   composite average over RT-800°C, not pure single-crystal B2 NiAl over
   0-300 K. The alternative (13.0e-6/K) is recalled, not session-verified
   (source paywalled/bot-blocked). **To close:** obtain the Miracle 1993
   review or an equivalent primary source for pure B2 NiAl's CTE.

3. **AlNi3's +1.1% literature agreement rests on an unverified recalled
   value.** The reference (12.5e-6/K) is recalled domain knowledge; the
   one on-topic primary source (1989 IOPscience paper) was blocked by an
   anti-bot redirect. **To close:** retrieve that paper or another primary
   Ni3Al CTE measurement.

4. **Net: all 3 Stage D-2 phases remain effectively unvalidated against
   literature on thermal expansion.** AlNi's comparison is to the wrong
   kind of reference, AlNi3's to an unverified recalled number, Al3Ni2 has
   no reference at all. Only physical plausibility of the magnitude
   (1.0–1.4% volumetric, 12–15e-6/K linear) is established. **To close:**
   items 1–3 above, applied consistently.

5. **Al3Ni5 alpha displacement.** This model's own energy minimum sits at
   alpha=98.28° vs. DFT's 96.478°, costing +0.873 meV/atom when
   constrained back — a real PES feature, independently corroborated by
   Stage C's soft C44=33.15 GPa (same physical direction). Whether
   alpha~98.3° is closer to or further from the TRUE (DFT) minimum than
   96.5° is NOT established. **To close:** a new DFT relaxation or
   single-point at the shifted geometry.

6. **AlNi C11 −26% gap.** Remains unexplained and unresolved. AlNi is one
   of only 2 phases (with AlNi3) with any literature elastic reference at
   all, so this is the project's one directly-checkable elastic-constant
   discrepancy, and it is large. **To close:** targeted investigation
   (additional DFT elastic-constant calculation, or literature
   re-verification of the 229.8/124.7/115.7 GPa reference itself).

7. **3 of 5 phases have zero elastic-constant reference.** Al3Ni, Al3Ni2,
   Al3Ni5's Stage C Cij values are model predictions only — no DFT or
   literature comparison exists. Born-stability and internal consistency
   were checked; quantitative accuracy was not. **To close:** a dedicated
   DFT elastic-constant calculation (e.g. finite-difference stress-strain
   under QE) for at least one of these three as an external check.

---

## 6. ARTIFACT INDEX

**Final model — authoritative:**
`models/al3ni_combined227_lora_v1/al3ni_combined227_lora_v1.model`
sha256 (recomputed this pass) =
`e4fd54cc8a4a090fc9e32d6625269142824bfada8315433127b3aa3118c65cee` —
**matches** the value independently pinned in
`configs/AL3NI_ROUND285_FINAL_UNSEALING_RESULT.txt`.
LAMMPS ML-IAP export:
`models/al3ni_combined227_lora_v1/al3ni_combined227_lora_v1.model-mliap_lammps.pt`,
sha256 (recomputed) =
`f35ca76f51d92e420f50bafb08ec860dbb2f8ffbeccccb394b66afca7a4bf464`
(recomputed only — no independently-recorded prior hash exists to
cross-check against).

**Final dataset — authoritative:**
`data/datasets/ni_al_combined227_dft.extxyz` (413,278 bytes), sha256
(recomputed) =
`9051860ae83dea782d9e5e49e4bf68f992103eed703ad81ca1ded5ea98db29eb` —
**matches** `configs/AL3NI_COMBINED227_MERGE_STATUS.txt`.
TRAIN 189: `data/datasets/ni_al_combined227_train_189.extxyz`, sha256
(recomputed) =
`41e4baf136bb430d39101acc3f3939c4390645fb355c509dd2b8e3ea310fe3f4` —
matches. VALIDATION 18:
`data/datasets/ni_al_combined227_validation_18.extxyz`, sha256
(recomputed) =
`079459f075a871d830249e713bdd11c0343774ff651689c94421a0b357c22aff` —
matches.

**Locked acceptance threshold — authoritative (two, do not conflate):**
- `configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt` — governs
  cfg109/cfg110 (2.3865 meV/atom, FAILED, historical).
- `configs/ROUND285_SEALED_ACCEPTANCE_CRITERION.txt` (sidecar
  `.sha256`) — governs cfg297/cfg299 (2.6183 meV/atom, PASSED). **This is
  the currently-live threshold.**

**LAMMPS deployment validation status — authoritative:**
`configs/project_knowledge.md` §8 is the synthesized record; primary
sources are `configs/LAMMPS_STAGE_{A_SINGLE_POINT,B_RELAXATION,C_ELASTIC,
D_MD_STABILITY,D2_SUPERCELL_MD}_STATUS.txt` plus
`configs/LAMMPS_STAGE_B_AL3NI5_ALPHA_DIAGNOSTIC.txt` and
`configs/LAMMPS_MLIAP_{,KOKKOS_}BUILD_STATUS.txt`. Stage D-3 (trajectories
+ chemical order) has no dedicated STATUS.txt of its own — its
authoritative source is `results/ovito_export/README.md` plus
`results/ovito_export/rdf/partial/partial_rdf_shell_report.json`.

**OVITO export bundle:** `results/ovito_export.tar.gz` (899,661 bytes),
built from `results/ovito_export/` (dft/, lammps_0K/, md_endpoints/,
supercells/, trajectories/, rdf/, rdf/partial/, README.md, manifest.json).

**configs/ directory — full enumeration by category** (grouped by role;
per-pod DFT-completion logs referenced collectively, not individually
content-verified beyond existence/mtime — sizes 76–1133 bytes each,
uniform format):
- *Pilot-25*: `PILOT25_PROVENANCE.txt`, `PILOT25_LORA_TRAINING_STATUS.txt`,
  `PILOT25_TEST_EVALUATION_STATUS.txt`, `PILOT25_FINAL_ARTIFACTS_MANIFEST.txt`,
  `pilot25_matpes_pbe_lora_v1_PROVENANCE.txt`, `pilot25_{mpa,matpes_pbe}_lora_v1.yaml`.
- *GPU/QE infra*: `GPU_QE_VALIDATION_STATUS.txt`,
  `GPU_TIMING_BENCHMARK_{STATUS,CHECKPOINT}.txt`, `mace_environment_freeze.txt`,
  `SAFE_TERMINATION_CHECK.txt`.
- *Dataset-100*: `DATASET100_{ASSEMBLY,SPLIT,DFT_VALIDATION,MACE_TRAINING,
  REGRESSION_ANALYSIS,FINAL_EVALUATION}_STATUS.txt`,
  `DATASET100_EXPANSION_PREPARATION.txt`, `DATASET100_GPU_{5POD,10CHUNK}_*`,
  `dataset100_matpes_pbe_lora_v1.yaml`.
- *Remediation v1 / round2*: `AL3NI_REMEDIATION_{DESIGN,DFT,DFT_VALIDATION,
  QE_COMPATIBILITY}_STATUS.txt`, `AL3NI_V1_101_108_ASSEMBLY_STATUS.txt`,
  `AL3NI_ROUND2_{ASSEMBLY,DFT_VALIDATION}_STATUS.txt`,
  `AL3NI_STAGE4_SPLIT_STRATEGY_REPORT.md`.
- *combined-113/127/129 + round3/round4*:
  `AL3NI_COMBINED{113,127,129}_{MERGE,MACE_TRAINING}_STATUS.txt`,
  `AL3NI_INTERIM_GATE_{,127_,129_}STATUS.txt`, `ROUND3_BATCH_DESIGN_STATUS.md`,
  `ROUND4_BIAXIAL_{DESIGN_STATUS,DFT_STATUS}`, `al3ni_combined{113,127,129}_lora_v1.yaml`,
  `POD_0{1..9}_STATUS.txt`.
- *round300 / combined-211*: `ROUND300_{DESIGN_STATUS,SCOPE,POD_PLAN}`,
  `ROUND300_POD_0{1..10}_STATUS.txt`,
  `AL3NI_COMBINED211_{MERGE,MACE_TRAINING}_STATUS.txt`,
  `AL3NI_INTERIM_GATE_211_STATUS.txt`, `COMBINED211_RESERVED_EVALUATION_STATUS.txt`,
  `al3ni_combined211_lora_v1.yaml`.
- *round212/213/214 / combined-218*: `ROUND212_CLOSE_FINAL4_DESIGN_STATUS.md`,
  `ROUND213_AL3NI2_ALNI_DESIGN_STATUS.md`, `ROUND214_POD_{A,B,C}_STATUS.txt`,
  `AL3NI_COMBINED218_{MERGE,MACE_TRAINING}_STATUS.txt`,
  `AL3NI_INTERIM_GATE_218_STATUS.txt`, `al3ni_combined218_lora_v1.yaml`.
- *round220 / combined-220 / unsealing #1*:
  `ROUND220_{CLOSE_LAST2_DESIGN_STATUS,FINAL_BATCH_STATUS}`,
  `AL3NI_COMBINED220_MERGE_STATUS.txt`, `COMBINED220_RESERVED_EVALUATION_STATUS.txt`,
  `AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`, `AL3NI_FINAL_UNSEALING_RESULT.txt`,
  `al3ni_combined220_{,rank8_,rank16_,seed20260812_,seed20260813_}lora_v1.yaml`.
- *round285 / combined-227 / unsealing #2*: `ROUND285_{POD_0{1,2,3}_STATUS,
  HIGH_EXPANSION_DENSIFY_DESIGN_STATUS,SEALED_PAIR_REVISION{,2}_STATUS,
  SUCCESS_CRITERIA,SEALED_ACCEPTANCE_CRITERION{,.sha256}}`,
  `AL3NI_COMBINED227_MERGE_STATUS.txt`,
  `AL3NI_ROUND285_{FINAL_UNSEALING_RESULT,SEALED_CONFIRMATION_POLICY}.txt`,
  `al3ni_combined227_{,seed20260812_,seed20260813_}lora_v1.yaml`.
- *LAMMPS Stage 9*: the 5 STATUS files above plus
  `LAMMPS_STAGE_B_AL3NI5_ALPHA_DIAGNOSTIC.txt`,
  `LAMMPS_MLIAP_{,KOKKOS_}BUILD_STATUS.txt`.
- *Cross-cutting / policy / narrative*: `project_knowledge.md` (61,850+
  bytes — the running technical narrative, most current single source),
  `EXPANSION_BATCH_DESIGN_POLICY.md`, `CROSS_PHASE_DRIFT_WATCHLIST.md`,
  `SESSION_STATE_AL3NI_EXPANSION_DESIGN.md` (+ `.sha256` sidecar),
  `NI_AL_DATA_SHOWCASE.md`, `RESUME_AUDIT.txt`, `VSCODE_SYNC_PLAN.txt`.
