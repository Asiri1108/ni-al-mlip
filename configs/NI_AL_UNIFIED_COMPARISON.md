# Ni-Al Unified Comparison Matrix

Compiled 2026-08-21. Closes the comparison matrix requested for this
session: six methods (three MACE variants, three NIST EAM/alloy potentials)
evaluated against a single QE/PBE reference computed fresh in this session
(STEP A/B/C below), on the full `combined-227` dataset, with the
reserved-20 held-out set reported separately. A second, independent
reference — Materials Project DFT, carried from Phase 1 (a separate
Windows-machine project, `inbox/`) — appears in one clearly separate
section as a free cross-check, never merged into the QE/PBE-referenced
numbers.

**Updated 2026-08-23** (two follow-up gaps closed, no new DFT): Section 7
applies Section 5's QE-referenced hybrid formation-energy correction to
MACE-MP-0 Small and MACE-MATPES-PBE-0 zero-shot as well as the fine-tuned
model, for a fair three-way comparison (finding: it does not transfer to
the zero-shot models — scale mismatch, see Section 7). Section 10 runs
LAMMPS Stage B structural relaxation for MACE-MATPES-PBE-0 zero-shot
against this project's own QE/PBE reference, giving a clean
single-DFT-reference structural before/after against the fine-tuned
model's existing Stage B result.

**Companion checksum file:** `configs/NI_AL_UNIFIED_COMPARISON.md.sha256`.

---

## 0. What is NEW vs CARRIED

Every number in Tables 1 and 2, and in Section 4 (formation energy /
volume), was computed in this session, this session's QE/PBE reference,
against `data/datasets/ni_al_combined227_dft.extxyz`. Nothing in those
tables is reused from any prior run.

The **only** carried numbers in this document are the 5 Materials-Project
formation energies in Section 6 (Free cross-check), sourced from
`inbox/ni_al_step8_final_report.txt` (Phase 1, Windows machine, MP API
retrieval version 2026.04.13) — used exclusively for the ranking-agreement
check in Section 6, never blended into Table 1/2's formation-energy column.

**QE/PBE and MP DFT answer different questions and are not
interchangeable.** QE/PBE here is this project's own raw, uncorrected PBE
total-energy calculation (Quantum ESPRESSO 7.6, locked production
settings). MP DFT is Materials Project's *processed*, mixing-scheme-corrected
summary value (`configs/NI_AL_DATA_SHOWCASE.md`'s own Phase-1-carried note;
confirmed again in `inbox/ni_al_step8_final_report.txt` Section 24:
"Materials Project values are processed DFT-derived reference data under
the Materials Project correction and mixing scheme, not experimental truth
and not raw uncorrected DFT total energies"). A formation energy computed
against one is not directly comparable in absolute terms to one computed
against the other — only relative structure (ranking, correlation) is
meaningfully cross-checked here, in Section 6, and even that check is
presented as a separate, clearly labeled comparison, not merged into
Table 1/2.

---

## 1. Elemental references (mu_Al, mu_Ni) — methodology and verification

### 1a. QE/PBE (this session, STEP B)

| | mu (eV/atom) | Settings | Relaxed a (Å) |
|---|---:|---|---:|
| Al | −537.46115182 | nspin=1, ecutwfc=90/ecutrho=720/MV/degauss=0.010, k-mesh 24×24×24 | 4.038351 |
| Ni | −4670.57345642 | nspin=2, start mag=0.60 μB (final 0.66 μB/cell), same ecut/smearing, k-mesh 22×22×22 (**locked**, `configs/NI_AL_DATA_SHOWCASE.md:153,164-166`) | 3.517938 |

Procedure: vc-relax, then an **independent final SCF** on the relaxed cell
(separate calculation, not the last vc-relax ionic step) — full log in
`configs/STEPB_ELEMENTAL_REFERENCES_STATUS.txt`.

### 1b. Pseudopotential identity check (requested verification)

| Pseudopotential | Elemental-reference run (this session) | Compound production runs | Match |
|---|---|---|---|
| Al.pbe-n-kjpaw_psl.1.0.0.UPF | `fd7b78921e6d0939095b681c328732668eaefd1dee6882fdbc03be463550cc97` | `fd7b78921e6d0939095b681c328732668eaefd1dee6882fdbc03be463550cc97` (pinned in `scripts/run_dataset100_gpu_chunk.sh`) | **IDENTICAL** |
| ni_pbe_v1.4.uspp.F.UPF | `f76b86ce60cde3d83dfcc8df79ba05478db573d158289f1b226919442d977d25` | `f76b86ce60cde3d83dfcc8df79ba05478db573d158289f1b226919442d977d25` (pinned in `scripts/run_dataset100_gpu_chunk.sh`) | **IDENTICAL** |

Both hashes verified byte-for-byte before STEP B ran (`configs/STEPB_ELEMENTAL_REFERENCES_STATUS.txt`); the elemental runs used the exact same two pseudopotential files as every compound production run in this project, not a re-downloaded or differently-versioned copy.

**Relaxation-convention check, partial:** the elemental references (Section
1a) used vc-relax + independent final SCF, verified directly from this
session's own QE input/output. The compound `relaxed` reference structures
(Pilot-25 origin, e.g. `AlNi_relaxed`) are labeled `config_type=relaxed` in
`data/datasets/ni_al_combined227_dft.extxyz`, but **no vc-relax QE input
file for these original Pilot-25 relaxed structures could be found on
disk** (searched `data/raw_dft/` and `configs/PILOT25_PROVENANCE.txt`) to
independently confirm they used the identical two-stage convention rather
than e.g. a single relax-only calculation. This is disclosed rather than
assumed: the compound side of every formation-energy number below is only
as verified as the `relaxed` config-type label itself.

### 1c. Elemental Al k-mesh — own convergence check (no prior record)

| Mesh | E (Ry) |
|---|---:|
| 20×20×20 | −39.5027416300 |
| 24×24×24 | −39.5026446100 |

dE = 1.320024 meV/atom, **above** the 0.5 meV/atom bar implied by Ni's own
adopted precedent (dE=0.488716 meV/atom at 22-vs-24, where the coarser mesh
was adopted) → **24×24×24 adopted** for Al, not assumed by analogy to Ni's
22×22×22.

### 1d. k-point spacing caveat (verified, with one correction)

The instruction to this step quoted k-point spacings of "Al 24³ ~0.065
Å⁻¹, Ni 22³ ~0.081, AlNi 16³ ~0.136" as a caveat to record verbatim. Before
recording it, the actual spacings were computed directly from each
calculation's own reciprocal cell (`|b_i| / N_i`, using ASE's
`cell.reciprocal()` on the exact primitive cells QE used):

| Component | Mesh | Computed spacing (Å⁻¹) | Quoted in the instruction |
|---|---|---:|---:|
| Al (primitive fcc, a=4.038351 Å) | 24³ | **0.1123** | ~0.065 |
| Ni (primitive fcc, a=3.517938 Å) | 22³ | **0.1406** | ~0.081 |
| AlNi (simple-cubic B2, a=2.894008 Å) | 16³ | **0.1357** | ~0.136 |

AlNi matches the quoted value almost exactly. Al and Ni do not — each is
off by a factor of ~1.73 (≈√3), consistent with computing the spacing from
the *conventional* cubic cell's reciprocal lattice (2π/a_conv) rather than
the actual *primitive* fcc cell QE solved (which has a smaller real-space
cell and correspondingly larger, non-orthogonal reciprocal vectors). AlNi's
B2 cell has no primitive/conventional distinction (simple cubic), which is
why only that one component's quoted value was already correct. **The
verified spacings (0.1123, 0.1406, 0.1357 Å⁻¹) are used below, not the
quoted ones.**

**Combined k-convergence uncertainty.** Each component was independently
converged to its own sub-1.4-meV/atom bar (Al: 1.320, Ni: 0.489, AlNi:
0.743 meV/atom — the last per `configs/NI_AL_DATA_SHOWCASE.md:154`), but
these residual errors do not cancel in the E_f = E_compound − n_Al·mu_Al −
n_Ni·mu_Ni subtraction, since each term comes from a differently-converged
mesh. Combining in quadrature: √(1.320² + 0.489² + 0.743²) ≈ **1.6
meV/atom**; a linear worst-case sum gives ≈2.6 meV/atom. **Formation
energies below carry a combined k-convergence uncertainty of roughly 1–2
meV/atom** — the instruction's own estimate holds up under an explicit
calculation, not just as an assertion. Formation-energy MAE values below
that are within ~2 meV/atom of each other should not be treated as
meV-exact rankings.

---

## 2. Table 1 — Master comparison, ALL-227

Relative-energy metric per `scripts/evaluate_dataset100_final.py`'s
convention (cancels each method's own energy-zero via its own prediction
on that phase's relaxed structure — no elemental references needed).
Formation energy and volume error use Section 1's QE/PBE mu_Al/mu_Ni and
each method's OWN elemental references (Section 3), never mixed across
methods.

| Method | Rel-E MAE (meV/atom) | Rel-E RMSE | Rel-E max | Force MAE (eV/Å) | Formation-E MAE (meV/atom) | Volume error (MAE, %) |
|---|---:|---:|---:|---:|---:|---:|
| **QE/PBE (reference)** | 0 | 0 | 0 | 0 | 0 | 0 |
| MACE-MP-0 Small (zero-shot) | 3.344 | 4.831 | 22.740 | 0.05236 | 58.689 | 0.753 |
| MACE-MATPES-PBE-0 (zero-shot) | 4.143 | 7.476 | 53.512 | 0.03248 | 25.094 | 1.196 |
| **al3ni_combined227_lora_v1** (fine-tuned) | **0.960** | **1.610** | **9.714** | **0.00189** | 79.592 | **0.105** |
| Pun-Mishin 2009 (EAM) | 11.055 | 19.389 | 103.258 | 0.05267 | 93.660 | 3.573 |
| Mishin 2004 ipr2 (EAM) | 6.832 | 12.226 | 84.103 | 0.08174 | 105.294 | 1.190 |
| Mishin 2002 (EAM) | 7.280 | 12.965 | 59.770 | 0.11023 | 120.196 | 1.771 |

All entries NEW (this session). n=227 for relative-energy/force columns;
n=5 phases for formation-energy/volume columns (see Section 4 for the
per-phase breakdown — formation energy and volume are inherently
phase-equilibrium properties, not per-config, so they are not split by
reserved-20 in Table 2 below).

**SUPERSEDED finding — resolved, see Section 5.** The fine-tuned model's
pure-model formation-energy MAE (79.592 meV/atom, *worse* than the
zero-shot MACE-MATPES-PBE-0's 25.094) looked at first like a genuine
compound-description weakness. It is not: Section 5 shows it is a pure,
near-perfectly-linear offset from two bad elemental mu values (the model
never saw isolated Al or Ni in training), confirmed independently by direct
evaluation, and it collapses to 0.95 meV/atom — noise-floor level — the
moment the model's compound energies are paired with QE/PBE's own mu
instead of the model's own. **Section 5 is the primary, current
characterization of this model's formation-energy behavior; the pure-model
numbers in Table 1/Section 4 are kept for the record but superseded as
"the" formation-energy result.** Relative energy (Table 1's first three
columns) was never affected either way — it never touches the elemental
references.

---

## 3. Elemental references per method (Section 2's formation-energy column, expanded)

Each method's mu_Al/mu_Ni come from that method's OWN relaxed elemental
equilibrium — never DFT's elemental geometry, and never another method's
mu — per the "matching relaxation state" rule. For MACE: full lattice
constant scan + quadratic fit (1 degree of freedom for a 1-atom fcc cell)
using that model itself. For EAM: identical scan methodology via LAMMPS
`eam/alloy` single-point evaluations.

| Method | mu_Al (eV/atom) | mu_Ni (eV/atom) |
|---|---:|---:|
| QE/PBE | −537.461152 | −4670.573456 |
| MACE-MP-0 Small | −3.709229 | −5.731663 |
| MACE-MATPES-PBE-0 | −3.731607 | −5.473765 |
| al3ni_combined227_lora_v1 | −537.416247 | −4670.460498 |
| Pun-Mishin 2009 | −3.359983 | −4.449450 |
| Mishin 2004 ipr2 | −3.359677 | −4.449450 |
| Mishin 2002 | −3.361691 | −4.499128 |

Cross-validation: MACE-MP-0 Small's mu_Al/mu_Ni here (−3.709229 /
−5.731663) match Phase 1's independently-computed values (`inbox/ni_al_step8_final_report.txt`
Section 7: mu_Al_MACE=−3.709587940, mu_Ni_MACE=−5.732347320) to within
0.0006 eV/atom, despite a completely different session, machine, and
optimizer — strong evidence both pipelines are computing the same real
quantity correctly. EAM elemental cohesive energies (Pun-Mishin: 3.360 eV
Al / 4.449 eV Ni; comparable for the others) are also close to the known
experimental cohesive energies (Al≈3.39 eV, Ni≈4.44 eV/atom), an
independent physical sanity check.

---

## 4. Per-phase formation energy and volume (all methods, QE/PBE reference)

| Phase | QE/PBE E_f (eV/atom) | QE/PBE V/atom (Å³) | MACE-MP-0 E_f | MATPES-PBE-0 E_f | Fine-tuned E_f | Pun-Mishin E_f | Mishin04 E_f | Mishin02 E_f |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AlNi | −0.638401 | 12.1191 | −0.690754 | −0.671940 | −0.715758 | −0.606154 | −0.590857 | −0.534838 |
| Al3Ni2 | −0.596451 | 13.9083 | −0.641565 | −0.586222 | −0.669456 | −0.363159 | −0.352625 | −0.371994 |
| Al3Ni5 | −0.546838 | 11.7373 | −0.606675 | −0.575830 | −0.634976 | −0.535760 | −0.495893 | −0.434003 |
| AlNi3 | −0.416580 | 11.3495 | −0.488638 | −0.458249 | −0.512797 | −0.454395 | −0.448213 | −0.385229 |
| Al3Ni | −0.396726 | 14.7463 | −0.460810 | −0.407767 | −0.459968 | −0.242858 | −0.244203 | −0.267952 |

All NEW (this session). Compound relaxation: full cell+position relax
(ASE `FrechetCellFilter`+BFGS for MACE; LAMMPS `fix box/relax aniso` +
`minimize` for EAM) starting from the DFT-relaxed geometry, using each
method itself — never a static evaluation on DFT's frozen geometry, so
volume error (Table 1) is a real, non-trivial number for every method.

---

## 5. Fine-tuned model formation-energy MAE: resolved (PRIMARY finding, this session)

**This section supersedes the "worst formation-energy MAE" framing
originally attached to the fine-tuned model's 79.592 meV/atom number
(Section 2/4). It is the current, primary characterization.** All NEW
(this session), pure recomputation from numbers already in this document
plus one small direct-verification single-point evaluation (no new
relaxation, no new DFT).

**1. Not scatter — a near-perfect linear offset in x_Ni.** The five
pure-model signed errors (fine-tuned − QE/PBE, meV/atom: Al3Ni −63.242,
Al3Ni2 −73.005, AlNi −77.357, Al3Ni5 −88.138, AlNi3 −96.218) fit
`error = intercept + slope * x_Ni` with:

| slope (meV/atom per unit x_Ni) | intercept (meV/atom) | R² | residual std (meV/atom) |
|---:|---:|---:|---:|
| −66.25 | −46.13 | **0.9931** | **0.96** (population) / 1.07 (sample) |

The residual std (0.96 meV/atom) sits right at the ~1–2 meV/atom
k-convergence noise floor established in Section 1d — the linear model
explains essentially all of the variance. This is the exact algebraic
signature of two wrong elemental references (`error = -delta_Al -
x_Ni*(delta_Ni - delta_Al)`), not a per-compound description failure: a
genuine compound-by-compound weakness would not produce R²=0.99 against
composition alone.

**2. Mechanism confirmed independently, not just inferred.** The fit
implies delta_Al=+46.13 meV/atom, delta_Ni=+112.39 meV/atom (model mu minus
QE mu). Two independent direct checks agree closely:

| Method | delta_Al (meV/atom) | delta_Ni (meV/atom) |
|---|---:|---:|
| From the linear fit | 46.13 | 112.39 |
| Model evaluated AT the QE-relaxed elemental cells (new single-point, STEP B geometry) | 48.44 | 112.54 |
| Model's own relaxed elemental equilibrium (Section 3) | 44.90 | 112.96 |

All three cluster within ~3.5 meV/atom (Al) and ~0.6 meV/atom (Ni) of each
other. **delta_Ni is ~2.4x delta_Al** — consistent with elemental Ni being
the harder reference (magnetic, `nspin=2`, per the Ni-specific convergence
decision in Section 1a/1c) and echoes the Ni magnetism caveat raised three
separate times across this project: Phase 1's own Section 22 ("Ni magnetic
limitation" — MACE structural relaxation has no explicit spin control),
this project's elemental-Ni convergence campaign needing its own separate
`nspin=2` decision (Section 1a), and AlNi3 later independently requiring
`nspin=2` (`configs/NI_AL_DATA_SHOWCASE.md` Section 6) where the other four
phases did not.

**3. QE-referenced hybrid — model compound energies + QE/PBE's own mu.**
Reasoning: the fine-tuned model is in-domain and QE-calibrated on
compounds (that is what it was fine-tuned on) but extrapolating on
isolated elements it never saw in training; pairing its compound energies
with QE/PBE's mu_Al/mu_Ni (STEP B: −537.46115182 / −4670.57345642
eV/atom) puts both terms of the formation-energy subtraction on the same
reference scale, which is more internally consistent, not less.

| Phase | Hybrid E_f (eV/atom) | QE/PBE E_f | Signed error (meV/atom) | Pure-model signed error (meV/atom) |
|---|---:|---:|---:|---:|
| AlNi | −0.636826 | −0.638401 | +1.57 | −77.36 |
| Al3Ni2 | −0.597330 | −0.596451 | −0.88 | −73.01 |
| Al3Ni5 | −0.547537 | −0.546838 | −0.70 | −88.14 |
| AlNi3 | −0.416852 | −0.416580 | −0.27 | −96.22 |
| Al3Ni | −0.398050 | −0.396726 | −1.32 | −63.24 |

**Hybrid MAE: 0.95 meV/atom** (mean signed −0.32, std 1.01) — down from
**79.592 meV/atom**, landing inside the k-convergence noise floor.

**4. Ordering, both schemes: Spearman ρ = 1.0 (exact), pairwise 10/10.**
Unchanged from the pure-model case — the offset was never large enough
relative to the phase-to-phase spread to disturb ranking, and the hybrid
correction confirms it explicitly.

**Revised use guidance for `al3ni_combined227_lora_v1` (replaces the
earlier framing):**
- Validated for MD, forces, and relative energies — **unchanged** from
  Table 1/2 (relative energy never touches the elemental references, so
  this finding does not affect it either way).
- **Also now valid for formation energies, to ~1 meV/atom** — but only
  when the model's compound energies are paired with **QE/PBE's own
  elemental references** (STEP B: mu_Al=−537.46115182 eV/atom,
  mu_Ni=−4670.57345642 eV/atom). **Do not use the model's own elemental
  predictions** (pure-model mu, Section 3) for formation-energy work — that
  is exactly the 79.6 meV/atom failure mode.
- **Root cause:** elemental Al and Ni were never in the fine-tuning
  training set (it trained only on the five alloy phases). This is
  recorded as **the single clearest improvement for any future training
  round** — adding isolated Al/Ni reference structures to the training set
  would let the model supply its own accurate mu and remove the need for
  the QE-referenced hybrid pairing entirely.

Full numeric record: `results/unified_comparison_formation_energy_v1/finetuned_hybrid_qe_referenced.json`.

**Pure-model numbers are kept, not deleted** (Table 1's formation-energy
column and Section 4's per-phase table, both above) — they remain the
correct description of what the model produces on its own, and are the
right thing to report if someone asks "what does this model alone say,"
just not the recommended number for formation-energy use.

---

## 6. Free cross-check — Phase 1's Materials Project DFT reference (CARRIED, separate question)

Phase 1 (Windows machine, `inbox/ni_al_step8_final_report.txt`) computed
formation energies for the same 5 phases against **Materials Project's**
processed DFT reference, using MACE-MP-0 Small only. Those 5 MP DFT values
are carried here verbatim, in their own column, for a ranking cross-check
only:

| Phase | MP DFT E_f (eV/atom) — CARRIED, Phase 1 | QE/PBE E_f (eV/atom) — NEW, this session |
|---|---:|---:|
| AlNi | −0.684901 | −0.638401 |
| Al3Ni2 | −0.644217 | −0.596451 |
| Al3Ni5 | −0.563251 | −0.546838 |
| AlNi3 | −0.426420 | −0.416580 |
| Al3Ni | −0.418776 | −0.396726 |

**Ordering is fully preserved between the two references.** Both rank the
five phases identically, most-to-least stable: AlNi > Al3Ni2 > Al3Ni5 >
AlNi3 > Al3Ni. Spearman ρ = 1.0 (exact), Pearson r = 0.9962, pairwise
ordering agreement 10/10 — computed directly (`scipy.stats.spearmanr`/
`pearsonr`), not assumed from the instruction's framing. Since the ordering
does not differ, there is no reconciliation question to raise: MP's
correction/mixing scheme and this session's raw PBE numbers disagree in
absolute magnitude (MP values are systematically ~0.02–0.05 eV/atom more
negative — MP's correction scheme, not a QE error, since Section 1b/1d
already account for the k-convergence budget on the QE side) but agree
completely on which phases are more or less stable relative to each other.

This column is a cross-check, not an input to Table 1/2 — no number above
mixes MP DFT and QE/PBE references.

---

## 7. Fairness fix — QE-referenced hybrid applied to ALL THREE MACE models (2026-08-23)

**Motivation.** Section 5's hybrid correction (model compound energies + QE's
own mu_Al/mu_Ni) was originally applied only to the fine-tuned model, taking
its formation-energy MAE from 79.592 to 0.95 meV/atom, while the two
zero-shot MACE models were left at their uncorrected pure-model MAE (58.689
MP-0 Small, 25.094 MATPES-PBE-0) — a biased comparison, since all three
models share the same "never saw isolated Al/Ni in training" property. This
section applies the identical hybrid procedure to all three and reports the
result, including the cases where it fails.

**Method (identical to Section 5, same QE mu):** for each phase, `Hybrid E_f
= E_compound(model) / n_atoms − (n_Al·mu_Al_QE + n_Ni·mu_Ni_QE) / n_atoms`,
using each model's own relaxed compound energies (already in
`results/unified_comparison_formation_energy_v1/mace_formation_energy.json`)
and QE/PBE's mu_Al=−537.46115182, mu_Ni=−4670.57345642 eV/atom (Section 1a).
No new DFT, no new model evaluation — pure recomputation.

| Method | Pure-model E_f MAE (meV/atom) | Hybrid E_f MAE (meV/atom) | delta_Al (meV/atom) | delta_Ni (meV/atom) |
|---|---:|---:|---:|---:|
| MACE-MP-0 Small (zero-shot) | 58.689 | **2,619,894** | +533,751.9 | +4,664,841.8 |
| MACE-MATPES-PBE-0 (zero-shot) | 25.094 | **2,620,050** | +533,729.5 | +4,665,099.7 |
| **al3ni_combined227_lora_v1** (fine-tuned) | 79.592 | **0.950** | +44.9 | +113.0 |

delta_Al/delta_Ni = model's own mu minus QE's own mu (Section 3 elemental
references), in meV/atom.

**Correction (2026-08-23): this is a scale mismatch, not a zero-shot model
failure.** Pairing either zero-shot model's raw compound total energy with
QE/PBE's mu blows the formation energy up to ~2,600 eV/atom — but this is
not evidence those models are wrong or that the hybrid math misbehaves for
them; it is the same **energy-zero mismatch** this project has documented
since the move to per-atom QE totals (Section 3's own mu table already
shows it side by side: QE mu_Al=−537.461 eV/atom vs MACE mu_Al≈−3.7
eV/atom, QE mu_Ni=−4670.573 vs MACE mu_Ni≈−5.5 to −5.7 — different codes,
different pseudopotential/core-electron conventions, hence different
absolute energy zeros; e.g. a compound total energy of "−5209 eV" (QE,
all-electron-equivalent core included) and "−10 eV" (MACE, its own
foundation-training zero) describe the *same physical structure*, and only
*relative* energies — differences within one method's own zero — are
meaningfully comparable across the two). Verified directly: delta_Al for
MP-0 = QE's mu_Al (−537.461152) minus **Phase 1's independently-recorded**
MACE-MP-0 mu_Al (−3.709588, Section 3's cross-validation row) =
**533.7516 eV/atom**, matching this section's own −3.709229-based
533.7519 eV/atom to 0.0003 eV — the same offset, computed twice,
independently, from two different sessions' zero-shot elemental
evaluations. delta_Al/delta_Ni are not errors in MP-0 or MATPES-PBE-0; they
are literally each model's energy zero minus QE's energy zero, restated in
meV/atom.

**Why the fine-tuned model's offset is small while the zero-shot models'
are not.** The fine-tuned model's compound predictions were trained
directly against this project's own QE total energies, so its energy zero
was pulled onto QE's scale by construction — its ~45/113 meV/atom
delta_Al/delta_Ni is a genuinely small *residual* miscalibration (Section
5's "never saw isolated Al/Ni" story), not a zero mismatch. MACE-MP-0 Small
and MACE-MATPES-PBE-0 were never trained on this project's QE energies at
all, so their multi-hundred-thousand-meV/atom deltas are simply their own,
untouched, foundation-training energy zeros — expected, not anomalous, and
nearly identical to each other (~534,000/~4,665,000 meV/atom for both)
because neither has any reason to be anywhere near QE's zero in the first
place.

**Conclusion — the original Section 5 framing stands, reframed rather than
weakened.** The fine-tuned model's 0.95 meV/atom hybrid number is not an
artifact of asymmetric treatment: the "fair," identical procedure applied
to its zero-shot counterparts does not produce comparably small numbers for
them, because the hybrid trick presupposes a compound energy already on
QE's absolute scale — a precondition only fine-tuning-on-QE-data
satisfies, not a defect discovered in the zero-shot models. **Pure-model
E_f (Table 1/Section 4) remains the only apples-to-apples formation-energy
comparison across all three MACE models side by side; the QE-referenced
hybrid number is valid, and meaningful, for the fine-tuned model only.**
Table 1/Section 4's pure-model MAE column (58.689 / 25.094 / 79.592) is
confirmed as the correct basis for cross-model formation-energy comparison.

Full numeric record: `results/unified_comparison_formation_energy_v1/macemp0_hybrid_qe_referenced.json`,
`results/unified_comparison_formation_energy_v1/mace_matpes_pbe0_hybrid_qe_referenced.json`
(fine-tuned unchanged: `finetuned_hybrid_qe_referenced.json`, Section 5).

**Addition — the substantive finding this fairness check surfaces: an
elemental-coverage trade-off from fine-tuning, not a compound-description
weakness.** MACE-MATPES-PBE-0's pure-model formation-energy MAE (25.094
meV/atom) beats the fine-tuned model's (79.592) even though the fine-tuned
model is **4.3x better on relative energy** (0.960 vs 4.143 meV/atom,
Table 1) and **17.2x better on forces** (0.00189 vs 0.03248 eV/Å, Table 1)
— the opposite ranking from every other metric in this document. The
reason is coverage, not capability: **MatPES, MACE-MATPES-PBE-0's
foundation training set, includes elemental Al and Ni structures**, so its
mu_Al/mu_Ni (Section 3) are genuine in-domain predictions, not
extrapolation. Fine-tuning, by contrast, narrowed the model to this
project's `combined-227` dataset — five Ni-Al compound phases only, no
isolated Al or Ni (Section 5's root cause) — so the fine-tuned model's
elemental predictions are **pure extrapolation outside its fine-tuning
distribution**, even though MACE-MATPES-PBE-0 (its own starting checkpoint)
had that exact information available before fine-tuning narrowed it away.
Fine-tuning traded elemental-reference coverage for compound-description
and force accuracy — a measured, specific accuracy/coverage trade-off, not
a general regression. **Concrete remedy, unchanged from Section 5 but now
motivated by a second, independent line of evidence:** add elemental Al and
Ni structures to any future training round — the QE data already exists
from this session's own STEP B (Section 1a: mu_Al=−537.46115182 eV/atom at
its relaxed a=4.038351 Å, mu_Ni=−4670.57345642 eV/atom at a=3.517938 Å),
so this requires no new DFT, only adding those two already-computed
structures to the training set.

**Volume-error sign difference between the two zero-shot foundation
models.** MACE-MP-0 Small **over-expands** relative to its DFT reference
(mean volume error +2.785%, vs Materials Project DFT —
`configs/NI_AL_DATA_SHOWCASE.md`, `configs/NI_AL_FINAL_PROJECT_RECORD.md`),
while MACE-MATPES-PBE-0 **under-contracts** (all 5 phases negative, mean
−1.195%, vs this project's own QE/PBE — Section 10). The two zero-shot
foundation models show opposite structural bias — one systematically too
large, the other systematically too small — though this is reported as a
qualitative sign observation only: the two percentages are measured against
different DFT references (Materials Project vs QE/PBE, Section 0's
carried-vs-new distinction) and are not on a common absolute footing with
each other, only internally consistent within each own comparison.

---

## 8. Table 2 — Reserved-20 held-out subset only

Restricted to the 20 configs in `data/datasets/ni_al_dataset100_test_manifest.csv`
(5) + `ni_al_dataset100_blind_holdout_manifest.csv` (15) — never trained on
by `al3ni_combined227_lora_v1`. Formation energy and volume error are
phase-equilibrium properties (Section 4), not per-config, so they have no
meaningful reserved-20-only version and are omitted from this table rather
than silently reused from Table 1.

| Method | Rel-E MAE (meV/atom) | Rel-E RMSE | Rel-E max | Force MAE (eV/Å) |
|---|---:|---:|---:|---:|
| **QE/PBE (reference)** | 0 | 0 | 0 | 0 |
| MACE-MP-0 Small (zero-shot) | 2.802 | 3.992 | 13.361 | 0.05565 |
| MACE-MATPES-PBE-0 (zero-shot) | 2.161 | 3.648 | 11.599 | 0.03224 |
| **al3ni_combined227_lora_v1** (fine-tuned) | **0.672** | **1.001** | **2.523** | **0.00293** |
| Pun-Mishin 2009 (EAM) | 8.820 | 15.590 | 50.591 | 0.05490 |
| Mishin 2004 ipr2 (EAM) | 4.449 | 6.811 | 17.365 | 0.09040 |
| Mishin 2002 (EAM) | 5.269 | 8.594 | 21.746 | 0.11446 |

All entries NEW (this session), n=20.

---

## 9. Sources and artifacts

- STEP A (relative energy, all methods): `results/unified_comparison_stepA_v1/{eam,mace}_{per_config,summary}.csv`, `logs/unified_comparison_stepA_v1/`
- STEP B (QE/PBE elemental references): `results/unified_comparison_stepB_v1/stepB_elemental_references.json`, `configs/STEPB_ELEMENTAL_REFERENCES_STATUS.txt`
- Formation energy / volume (all methods): `results/unified_comparison_formation_energy_v1/{mace,eam}_formation_energy.json`, `qe_pbe_reference_formation_energy.json`, `formation_energy_summary.json`
- EAM potentials, verified: `tools/eam_potentials/` (hashes and structural validation in the session record; see `configs/NI_AL_FINAL_PROJECT_RECORD.md`'s 2026-08-21 update)
- LAMMPS build used for EAM: `tools/lammps/install/manybody_eam/` (PKG_MANYBODY, added this session — neither prior build had `eam/alloy`)
- Scripts: `scripts/eval_eam_relative_energy_combined227.py`, `scripts/eval_mace_relative_energy_combined227.py`, `scripts/run_stepB_elemental_references.py`, `scripts/eval_mace_formation_energy_combined227.py`, `scripts/eval_eam_formation_energy_combined227.py`

**Methods that failed to evaluate: none.** All 6 methods produced
relative-energy, force, formation-energy, and volume numbers for all 227
structures / 5 phases without error.

- Fairness-fix hybrid results (Section 7): `results/unified_comparison_formation_energy_v1/macemp0_hybrid_qe_referenced.json`, `mace_matpes_pbe0_hybrid_qe_referenced.json`
- Zero-shot Stage B (Section 10): `results/lammps_stage_b_matpes_pbe0_zeroshot/{phase}_lammps.json`, `logs/lammps_stage_b_matpes_pbe0_zeroshot/`, `configs/LAMMPS_STAGE_B_MATPES_PBE0_ZEROSHOT_STATUS.txt`, `models/mace_matpes_pbe_0_zeroshot-mliap_lammps.pt`
- Scripts (2026-08-23 additions): `scripts/lammps_stage_b_relax_phase_matpes0_zeroshot.py`, `scripts/lammps_stage_b_run_all_matpes0_zeroshot.py`, `scripts/lammps_stage_b_report_matpes0_zeroshot.py`

---

## 10. Zero-shot MACE-MATPES-PBE-0 LAMMPS Stage B — single-reference before/after (2026-08-23)

**Closes the caveat noted at the top of this document's Section 0 history:**
the fine-tuned model's LAMMPS Stage B structural validation
(`configs/LAMMPS_STAGE_B_RELAXATION_STATUS.txt`, Section 8's own predecessor
work) was run against this project's QE/PBE relaxed cells, while the only
zero-shot structural number on record before this section (MACE-MP-0's
+2.785% mean volume error, `configs/NI_AL_DATA_SHOWCASE.md`,
`configs/NI_AL_FINAL_PROJECT_RECORD.md`) was computed against **Materials
Project's** DFT reference — two different DFT references, not a clean
before/after. This section runs the identical LAMMPS Stage B procedure
(`fix box/relax tri` + `minimize`, mliap unified, Kokkos build, starting
from the DFT-relaxed geometry) for MACE-MATPES-PBE-0 zero-shot against
**this project's own QE/PBE relaxed cells** — the same reference the
fine-tuned model was checked against — giving a genuine single-reference
before/after. **Stage C and Stage D were deliberately not run for this
zero-shot model — out of scope for this task.**

Model: the exact MACE-MATPES-PBE-0 foundation checkpoint used as the
fine-tuning starting point (`runs/pilot25_matpes_pbe_lora_v1/downloads/mace/MACEmatpespbeomatftmodel`,
already independently labeled "exact zero-shot MACE-MATPES-PBE-0" by
`scripts/evaluate_pilot25_test_v1.py`), exported to LAMMPS ML-IAP unified
format via `scripts/export_lammps_mliap_model.py`'s method (head="default",
lowercase — this foundation checkpoint's own head name, vs the fine-tuned
model's "Default") → `models/mace_matpes_pbe_0_zeroshot-mliap_lammps.pt`.

| Phase | QE/PBE V/atom (Å³) | Zero-shot LAMMPS V/atom (Å³) | Volume error (%) | Max |lattice %| | Symmetry preserved |
|---|---:|---:|---:|---:|:---:|
| AlNi | 12.11907 | 11.79590 | **−2.6666%** | 0.8969% | Y |
| Al3Ni | 14.74629 | 14.59819 | −1.0043% | 1.5707% | Y |
| Al3Ni2 | 13.90827 | 13.80283 | −0.7581% | 0.6240% | Y |
| Al3Ni5 | 11.73726 | 11.59978 | −1.1713% | 4.0371% | Y |
| AlNi3 | 11.34945 | 11.30688 | −0.3751% | 0.1264% | Y |

**Max |volume/atom error|: 2.6666% (AlNi). Symmetry preserved: 5/5. Phases
completed: 5/5.** Full log: `configs/LAMMPS_STAGE_B_MATPES_PBE0_ZEROSHOT_STATUS.txt`.

**Cross-check against the existing ASE-based number.** The mean of this
table's 5 volume errors is 1.195%, matching Table 1's independently-computed
MACE-MATPES-PBE-0 zero-shot "Volume error (MAE, %)" of **1.196%** (ASE
`FrechetCellFilter`+BFGS relax, Section 4) to within rounding — two
different relaxation codepaths (LAMMPS mliap unified vs plain ASE/MACE) on
the same model agree, the same cross-check Stage B already established for
the fine-tuned model (`LAMMPS_STAGE_B_RELAXATION_STATUS.txt`'s "LAMMPS vs
ASE/MACE" lines).

**Clean single-reference before/after (the point of this section):**

| | Max volume/atom error vs QE/PBE | Symmetry preserved |
|---|---:|---|
| MACE-MATPES-PBE-0 (zero-shot, this section) | **2.6666%** | 5/5 |
| al3ni_combined227_lora_v1 (fine-tuned, recorded) | **0.2159%** | 5/5 |

Fine-tuning improves the worst-phase structural volume error by **~12.3x**
(2.6666% → 0.2159%) against the identical DFT reference on both sides — the
prior +2.78%-vs-0.216% comparison (Section 0 caveat) mixed two DFT
references and is superseded by this table for structural before/after
purposes; it remains valid as a MACE-MP-0-vs-Materials-Project statement,
just not as a same-reference zero-shot-vs-fine-tuned comparison. Both
zero-shot models preserve symmetry in all 5 phases either way (5/5), so
fine-tuning's structural gain here is in volume/lattice accuracy, not in
avoiding a symmetry break.
