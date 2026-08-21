# Ni–Al MACE Project — Data Showcase

Every table below is a real, recorded result — not a description of a step. Where a
number is not available in the project's saved reports, that gap is stated explicitly
rather than filled in.

---

## 1. MACE-MP-0 zero-shot — raw response before any training (Step 5)

Pretrained MACE-MP-0 Small evaluated directly on the five Materials Project structures,
no relaxation, no fine-tuning.

| Phase | Atoms | E/atom (eV) | Max force (eV/Å) | σ_xx (eV/Å³) | V/atom (Å³) |
|---|---:|---:|---:|---:|---:|
| Al3Ni | 16 | −4.668482 | 0.212793 | −0.016042 | 14.2844 |
| Al3Ni2 | 5 | −5.156110 | 0.102594 | −0.023518 | 13.4870 |
| AlNi | 2 | −5.406841 | **4.89×10⁻⁸** | −0.029697 | 11.6933 |
| Al3Ni5 | 8 | −5.571010 | 0.160800 | −0.040424 | 11.2965 |
| AlNi3 | 4 | −5.709073 | **5.98×10⁻⁸** | −0.036642 | 10.9320 |

**Real signal, not just a sanity check:** AlNi and AlNi3 (both cubic, high-symmetry)
return forces at machine-precision zero — symmetry alone pins every atom. The other
three carry real forces up to 0.21 eV/Å, meaning their DFT geometry is not a stationary
point on the MACE surface. Every σ_xx is negative — MACE wants every cell to expand.
That single number correctly predicted the volume bias found three steps later.

---

## 2. MACE relaxation — atomic-only vs. full-cell (Step 6)

Two independent runs per phase, each from an unmodified copy of the original structure.
Convergence: force ≤ 0.01 eV/Å (both modes); stress ≤ 0.0006241509 eV/Å³ (full-cell only).

| Phase | Atomic-only status | Steps | ΔE (eV) | Full-cell status | Steps | ΔE (eV) | ΔV (%) |
|---|---|---:|---:|---|---:|---:|---:|
| Al3Ni | CONVERGED | 28 | −0.039747 | CONVERGED | 40 | −0.114532 | +2.740 |
| Al3Ni2 | CONVERGED | 10 | −0.001103 | CONVERGED | 33 | −0.018273 | +2.383 |
| AlNi | ALREADY_CONVERGED | 0 | 0 | CONVERGED | 5 | −0.008716 | +2.628 |
| Al3Ni5 | CONVERGED | 24 | −0.003624 | CONVERGED | 34 | −0.071205 | +3.280 |
| AlNi3 | ALREADY_CONVERGED | 0 | 0 | CONVERGED | 14 | −0.022480 | +2.894 |

**What the two modes isolate:** for every phase, |ΔE_full-cell| > |ΔE_atomic-only| — for
AlNi and AlNi3, infinitely so, since atomic motion did nothing at all. **MACE's
disagreement with DFT geometry is a cell-volume problem, not an internal-coordinate
problem.** For Al3Ni specifically, cell relaxation delivered −0.1145 eV against atomic
relaxation's −0.0397 eV — 74% of the available energy lowering was locked behind the
cell shape/volume, not atomic positions. Symmetry was preserved 5/5 in every relaxation.

---

## 3. MACE vs. Materials Project DFT — formation-energy accuracy (Step 8)

| Phase | MP DFT E_f (eV/atom) | MACE relaxed E_f (eV/atom) | Signed error | ΔV/atom |
|---|---:|---:|---:|---:|
| Al3Ni | −0.418776 | −0.460362 | −0.041587 | +2.740% |
| Al3Ni2 | −0.644217 | −0.641073 | +0.003143 | +2.383% |
| AlNi | −0.684901 | −0.690231 | −0.005330 | +2.628% |
| Al3Ni5 | −0.563251 | −0.606098 | −0.042847 | +3.280% |
| AlNi3 | −0.426420 | −0.488036 | −0.061616 | +2.894% |

**Aggregate (n=5):** MAE = 0.030905 eV/atom · RMSE = 0.038471 · mean signed = −0.029647
(systematic over-binding) · **exact ranking agreement, Spearman ≈ 1.0, 10/10 pairwise** ·
mean volume error +2.785% · symmetry preserved 5/5.

Two distinct, separable error signatures: a uniform ~2.8% cell over-expansion (same
direction on every phase — correctable), and a composition-dependent residual that grows
toward Ni-rich phases (−0.042 at x_Ni=0.25 → −0.062 at x_Ni=0.75) — flagged as possibly
magnetic in origin, since MACE has no explicit spin input and Ni is ferromagnetic in DFT.

---

## 4. Classical potentials benchmark — Pun-Mishin, Mishin 2004, Mishin 2002 (Step 9–10)

Three NIST EAM/alloy potentials, selected and SHA256-fingerprinted before use:

| Potential | Role | Cutoff (Å) | Fitting focus |
|---|---|---:|---|
| Pun–Mishin 2009 | Primary | 6.2872 | General binary Ni–Al + ab initio intermetallic energies |
| Mishin 2004 (ipr2) | Secondary | 6.7249 | γ/γ′ (Ni₃Al) |
| Mishin 2002 | Historical | 5.9541 | B2-NiAl; documented pure-element weakness |

**Formation energies, all five methods, same seven structures, same convergence
criteria (eV/atom):**

| Phase | MP DFT | MACE | Pun–Mishin 09 | Mishin 04 | Mishin 02 |
|---|---:|---:|---:|---:|---:|
| Al3Ni | −0.418776 | **−0.460362** | −0.242708 | −0.243823 | −0.267036 |
| Al3Ni2 | −0.644217 | **−0.641073** | −0.362929 | −0.352211 | −0.370819 |
| AlNi | −0.684901 | **−0.690231** | −0.605871 | −0.590420 | −0.533491 |
| Al3Ni5 | −0.563251 | −0.606098 | **−0.540870** | −0.512888 | −0.435295 |
| AlNi3 | −0.426420 | −0.488036 | −0.453978 | **−0.447720** | −0.383452 |

*(bold = closest to DFT for that phase)*

| Method | MAE (eV/atom) | RMSE | Ranking exact | Pairwise | Volume MAE |
|---|---:|---:|---|---:|---:|
| **MACE-MP-0** | **0.030905** | **0.038471** | **True** | **10/10** | 2.785% |
| Pun–Mishin 2009 | 0.117265 | 0.153381 | False | 8/10 | **1.858%** |
| Mishin 2004 (ipr2) | 0.126620 | 0.159870 | False | 8/10 | 2.676% |
| Mishin 2002 | 0.149494 | 0.166682 | False | 8/10 | 1.638% |

**MACE beats the best EAM by 3.8× on energetics and is the only method with correct
phase ordering — but is not universally better.** Pun–Mishin 2009 has smaller *volume*
error, and in the Ni-rich corner specifically it out-performs MACE (0.025 vs 0.052
eV/atom, a 2.1× MACE loss). MACE's real advantage is transferability: worst-regime error
0.052 vs. the EAMs' 0.21–0.23 in their weak spots (Al-rich phases neither was fitted to).

---

## 5. LAMMPS execution — the benchmark engine (Step 10)

| Item | Value |
|---|---|
| Calculation matrix | 3 potentials × 7 structures × 3 states = **63 states, 0 failures** |
| Convergence check | independent of LAMMPS' own exit flag: force ≤ 0.01 eV/Å, \|pressure\| ≤ 999.999988 bar |
| Runtime (Pun-Mishin) | 2.71 s / 21 states |
| Runtime (Mishin 2004) | 2.66 s / 21 states |
| Runtime (Mishin 2002) | 2.79 s / 21 states |
| MACE full-cell (7 structures, CPU) | ~117.5 s total, for context only — not a precise speed ratio |

Roughly two orders of magnitude cheaper than MACE at this scale. Irrelevant for static
single-point work; becomes the entire engineering trade-off at MD production scale,
where that per-step cost multiplies across millions of timesteps.

**This full four-way comparison — not the zero-shot MACE number alone — is what
justified building an independent DFT dataset rather than declaring the question closed.**

---

## 6. Turning this environment into a DFT data factory

Before any training data could be generated, the electronic-structure settings
themselves had to be established and fixed project-wide through a convergence campaign:
k-point density, smearing width, and magnetic state, tested independently per element
and per phase before being locked in.

**What is documented as the adopted, production-fixed result of that campaign:**

| Setting | Value | Scope |
|---|---|---|
| `ecutwfc` | 90 Ry | all phases |
| `ecutrho` | 720 Ry | all phases |
| Smearing | Marzari–Vanderbilt | all phases (metallic system) |
| `degauss` | 0.010 Ry | all phases |
| `nspin` | **2** (spin-polarized, starting magnetization on Ni) | **AlNi3 only** |
| `nspin` | 1 (non-spin) | Al3Ni, Al3Ni2, AlNi, Al3Ni5 |

**K-point convergence — completed and numerically documented, not just planned:**

| System | Final comparison | ΔE (meV/atom) | ΔP (kbar) | ΔM_tot (μB) | ΔM_abs (μB) | Adopted mesh |
|---|---|---:|---:|---:|---:|---|
| Ni | 22×22×22 vs 24×24×24 | 0.488716 | 0.730 | 0 | 0.010 | **22×22×22** |
| AlNi | 16×16×16 vs 20×20×20 | 0.742803 | 0.34 | 0 | 0 | **16×16×16** (F_max ≈ 1.34×10⁻⁶ eV/Å) |

For Ni, the sequence went 20×20×20 → 24×24×24 as the final bracket, with 22×22×22 run
as an intermediate mesh once `degauss` was fixed at 0.010 Ry — re-tested rather than
assumed, because `degauss` and k-point density are coupled, not independent variables:
changing one requires re-confirming convergence against the other.

**Spin/magnetism — also completed and documented, with two decisions that must not be
conflated:**

*Elemental Ni* was tested non-spin (`nspin=1`) against spin-polarized (`nspin=2`) with
starting moments swept at 0.2, 0.6, 1.0, and 1.5 μB — established as spin-polarized,
`nspin=2`, initial moment 0.6 μB/Ni.

*AlNi* (the compound) received its own independent test: `nspin=1` vs. `nspin=2` with
the same moment sweep. Every spin-polarized AlNi run converged to M_tot = 0, M_abs = 0,
with an energy difference from the non-spin case of only 0.037824 meV/atom. AlNi was
therefore assigned `nspin=1`, no starting magnetization.

*AlNi3 is a separate compound and received its own separate decision* — not
interchangeable with the AlNi result above. What the project's later methodology
established as a firm rule is that **spin treatment is part of each phase's own
definition, decided per phase, and must be preserved explicitly whenever new QE inputs
are generated** — it is not a default to be reconstructed or assumed by analogy from a
different phase. That rule is precisely why AlNi3's `nspin=2` setting, though decided
correctly at this stage, had to be manually re-discovered before a later expansion
round when it was found missing from the machine-readable batch-design manifests —
catching what would otherwise have silently produced wrong AlNi3 physics.

---

## 7. First real DFT baseline on the five approved compounds

With settings locked, MACE (now `MACE-MATPES-PBE-0`, switched from MP-0 Small because it
sits closer to the project's own PBE surface) was re-evaluated zero-shot — from scratch,
not reusing the old MP-0 numbers — on the new QE-generated structures.

| Metric | Value |
|---|---:|
| Relative-energy MAE | 4.023 meV/atom |
| Relative-energy RMSE | 6.634 meV/atom |
| Max relative-energy error | **21.228 meV/atom** (`AlNi_iso_m02`, compression) |
| Mean force MAE | 0.015641 eV/Å |
| Mean force RMSE | 0.023627 eV/Å |
| Mean stress MAE | 0.871511 GPa |

**Force MAE by phase — the first sign of what would matter for months:**

| Phase | Force MAE (eV/Å) |
|---|---:|
| AlNi | 0.000441 |
| AlNi3 | 0.000879 |
| Al3Ni5 | 0.006676 |
| Al3Ni2 | 0.015993 |
| **Al3Ni** | **0.054216** — weakest phase, by a wide margin |

This single early number correctly flagged Al3Ni as the phase needing the most future
attention — months before `cfg043` (an Al3Ni structure) became the project's central
case study. Stress error was worst on AlNi (~1.844 GPa) and on the compression family
specifically (`iso_m02`, ~1.49 GPa) — direct guidance for what the next dataset needed
more of: volume/strain coverage, with particular care around Al3Ni.

---

## 8. Building the first real training set — Pilot-25

Per phase, four systematic perturbations of the relaxed structure:

| Family | What it does |
|---|---|
| `iso_m02` | isotropic compression, cell scaled to 98% |
| `iso_p02` | isotropic expansion, cell scaled to 102% |
| `rattle_003` | random atomic displacement, σ ≈ 0.03 Å |
| `shear015_rattle002` | shear ≈ 0.015 combined with rattle σ ≈ 0.02 Å |

**5 phases × 4 families = 20 perturbed structures + 5 relaxed references = 25
configurations**, each with real QE-computed energy, forces, and stress — the project's
first genuine force-training dataset (`ni_al_pilot_dft_25.extxyz`), independently
re-validated by reading it back after writing (`VALID DATASET: 25/25`).

**Split, designed explicitly against near-duplicate leakage:**

| Split | Families | Count |
|---|---|---:|
| TRAIN | relaxed + iso_m02 + iso_p02 | 15 |
| VALIDATION | rattle_003 | 5 |
| TEST | shear015_rattle002 | 5 |

---

## 9. Expansion, and the failure that changed the methodology

Pilot-25 grew to **Dataset-100** (~100 configs, families widened to uniaxial, biaxial,
orthorhombic, shear_rattle, volume_rattle). Fine-tuning improved most metrics — except
one: `cfg043` (Al3Ni, `volume_rattle_expansion`) came back `REVIEW REQUIRED`.

**How new configurations get added, concretely, once a weak point is found:**

1. Locate exactly where the failing point sits relative to the training data's range on
   the relevant physical axis (here: volume/strain).
2. Diagnose *why* it fails — this is where the project's first diagnosis was wrong.
3. Design new DFT structures that fix the *actual* mechanism, not the apparent one.
4. Run each candidate through four independent gates before any DFT compute is spent.

**Why `cfg043` failed — and why the first answer was wrong:**

> First diagnosis: "coverage gap" — assumed the fix was more nearby points.
> Correct diagnosis, reached only after checking where the point actually sat: `cfg043`
> was at **+3.5% isotropic strain**, above the training data's own ceiling of **+3.0%**.
> It wasn't a hole inside the data — it was **extrapolation**, a region never shown to
> the model at all. A hole is fixed with points *inside* it; an edge is fixed with points
> that *bracket* it from both sides.

Two structures even further out — `cfg109` (+4.0%) and `cfg110` (+4.0%, with rattle) —
were immediately sealed as a final confirmation holdout: never trained on, never
evaluated, to be opened exactly once, right before the final LAMMPS-readiness decision.

---

## 10. The four gates — what each one actually catches, with real examples

Every new batch of structures must clear four independent, data-derived checks *before*
a single DFT calculation is launched.

| Gate | Question | Real example of it catching something |
|---|---|---|
| **(a) Redundancy** | Too similar to existing TRAIN data? | Threshold = 5th percentile of real pairwise distances (0.7949) — recomputed per phase, never reused blindly |
| **(b) Leakage** | Too close to a sealed/holdout point? | An invented "2× redundancy" threshold (1.5898) was proven baseless and replaced with the dataset's own accepted minimum train↔holdout distance (**0.734644** — the `cfg029↔cfg043` pair itself) |
| **(c) Role consistency** | Can near-duplicate variants split across train/validation? | The geometry descriptor was found mathematically **blind** to rattle-only differences (`d_vol=0`, `d_strain=0` by construction) — two "duplicate" rejections (`cfg106`, `cfg108`) were later confirmed as measurement artifacts, not real duplication |
| **(d) Validation placement** | Is validation representative, not an outlier? | A proposed validation point was found sitting *outside* the training envelope — the exact same extrapolation mistake as `cfg043` — caught and repositioned before any DFT was spent |

**Every validator was itself tested before being trusted:** four independently corrupted
copies of a real output (truncated file, NaN force, infinite energy, wrong array shape)
were run through the checker — all four were correctly flagged FAILED. A script that
always says "valid" is worthless without proof it can say "invalid."

---

## 11. Results after the gate-driven remediation

**On the exact configuration that started the whole cycle:**

| Config | Original model | After round 1 | After round 3 |
|---|---:|---:|---:|
| `cfg043` (the failure) | 6.60 meV/atom | 2.88 meV/atom (−56%) | 2.15 meV/atom (−67% total) |
| `cfg115` (new validation point) | 12.35 meV/atom | 6.14 meV/atom (−50%) | 4.64 meV/atom (−62% total) |

**Regression check on the untouched parts of the dataset (discipline, not just
progress):** aggregate energy RMSE on the original 15 Dataset-100 validation configs
improved slightly (0.4476 → 0.4163 meV/atom), but two configurations in phases the
remediation never touched degraded measurably — `cfg098` (AlNi3, 0.057 → 0.474 meV/atom,
~8×) and `cfg056` (Al3Ni5, 0.926 → 1.135) — logged as a cross-phase drift watchlist
rather than dismissed, since a low average can hide a real localized problem.

**A systemic gap found by applying the same diagnostic project-wide:** running the
`cfg043`-style extrapolation check on *every* phase and *every* strain family — not just
Al3Ni — found that **biaxial deformation had zero training representation in all five
phases**. Measured error on those points averaged 1.33 meV/atom, ~8.3× the well-covered
baseline of 0.16 — confirming a real gap, not a protected generalization test.

**Where the dataset stands after closing it:**

| Milestone | Structures | Coverage state |
|---|---:|---|
| Pilot-25 | 25 | first working pipeline |
| Dataset-100 | ~100 | `cfg043` failure discovered |
| Remediation round 1 | ~115 | Al3Ni expansion axis fixed |
| Round 3 + Round 300 | ~218 | **zero open "zero-coverage" flags project-wide, first time** |

Phase balance tightened from a 15–27 spread per phase to a tight 30–45 band. Six minor
extrapolation flags remain open — all in low-magnitude shear/rattle families, a
structural limit (no small-magnitude candidate there can add information without
becoming redundant), not a design oversight.

---

## 12. Why this is scientific rigor, not just a bigger dataset

- **Every threshold used above is derived from the data at hand, never invented and
  never reused verbatim** — the `2×` multiplier that had to be caught and replaced is the
  clearest example on record.
- **The descriptor's own blind spot was found and proven**, not assumed — `d_vol` and
  `d_strain` are exactly zero for matched-strain rattle pairs by mathematical
  construction, which is why two "duplicates" were false positives.
- **The sealed holdout (`cfg109`, `cfg110`) has never been read** — not once, through
  every round described above — geometry only, never energy, forces, or stress, and its
  pass/fail threshold will be fixed *before* it is finally opened, not after.
- **A regression check runs after every merge**, not just a check of the intended fix —
  which is exactly what caught the AlNi3/Al3Ni5 cross-phase drift while it was still
  small enough to log and monitor rather than a hidden problem discovered too late.
