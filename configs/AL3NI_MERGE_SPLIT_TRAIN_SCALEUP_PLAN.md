# Al3Ni Merge -> Split -> Train -> 300-Round Scale-Up: Staged Plan

Written to outline the work before executing any of it, per explicit request.
**Nothing in this plan has been executed yet.** Each stage below will produce
its own report when run; `configs/project_knowledge.md` will be created in
Stage 1 and updated after every subsequent stage.

## Grounding facts (gathered before writing this plan, not invented)

**Current assembled/labeled structure count: 105** (Dataset-100's 100 +
round2's 5). **cfg101-cfg108 (8 more) are DFT-complete and validated
(10/10 VALID incl. cfg109/110, `AL3NI_REMEDIATION_DFT_VALIDATION_STATUS.txt`)
but have never been extracted into a labeled extxyz** — confirmed by
searching the entire `data/` tree; only raw `qe.out` + manifests exist for
them. That extraction is the same kind of step already done for round2 this
session (`extract_dataset75.py`-style XML->extxyz), just not yet applied to
cfg101-108.

**Roles were already decided at design time**, not something to re-derive:
- Dataset-100: TRAIN 65, VALIDATION 15, TEST+BLIND_HOLDOUT 20 (unchanged,
  untouched, no new additions planned to this control group)
- v1 remediation (cfg101-110): TRAIN 6 (cfg101-106), VALIDATION 2
  (cfg107-108), CONFIRMATION_HOLDOUT 2 (cfg109-110, **sealed**)
- round2 (cfg111-115): TRAIN 4 (cfg111-114), VALIDATION 1 (cfg115)

So the merged split, once cfg101-108 are assembled, is: **TRAIN 75 (=65+6+4),
VALIDATION 18 (=15+2+1), TEST+BLIND_HOLDOUT 20 (unchanged), SEALED 2. Total
115.** This is presented for confirmation in Stage 4, not decided unilaterally
— see "Open question" below.

**Training time estimate (real, not projected):** the existing Dataset-100
MACE run (`dataset100_matpes_pbe_lora_v1`) took **339 seconds wall-clock**
for 100 epochs on 65 TRAIN / 15 VALIDATION structures — LoRA fine-tune of
the `mace-matpes-pbe-0` foundation model, single GPU, peak 1.8 GB VRAM,
batch size 2. Going to 75 TRAIN / 18 VALIDATION adds ~15% more batches per
epoch; expect **~380-400 seconds**, not hours. This is not the bottleneck
anywhere in this plan.

**DFT time estimate (real, from this session + historical benchmark data):**
Al3Ni-family (16-atom) single-point SCF takes **~11 min (non-rattle) to
~24-26 min (rattle)** per structure with this project's QE setup — confirmed
both by this session's 5 round2 runs and the historical Dataset-100
phase-benchmark (`GPU_TIMING_BENCHMARK_PLAN.txt`: Al3Ni phase ~572s/config,
close to the ~660s/config average observed this session). **Correction
(2026-08-16):** this file previously claimed the QE binary "is not actually
using GPU offload in practice," based on misreading the `"Serial
multi-threaded version, running on 8 processor cores"` banner (MPI/OpenMP
topology only). GPU offload IS active — see the separate `"GPU
acceleration is ACTIVE"` status line in every `qe.out`, and the already-
recorded utilization telemetry in `configs/GPU_QE_VALIDATION_STATUS.txt`/
`configs/GPU_TIMING_BENCHMARK_STATUS.txt`. The above per-structure timings
already reflect genuine GPU-accelerated runs, not a CPU-only baseline —
no further offload headroom to unlock by "fixing" anything here.

**300-round sizing and pod partitioning: deferred.** Per clarification,
this is an advanced/later stage, not part of the current merge -> split ->
train pass. The per-structure DFT timing numbers above (~11-26 min/structure)
are recorded here now only because they were gathered as part of this
session's research and are cheap to keep on file — no pod-partitioning
convention, sizing, or scheduling decision is being made in this plan.
That work starts fresh, on its own, when the 300-round is actually taken up.

## Stages

### Stage 1 — `configs/project_knowledge.md`
Create a living technical/scientific overview: what this project is (Ni-Al
intermetallic MLIP development), the phases studied, DFT methodology (QE
7.6 PBE, pseudopotentials, k-grid/smearing/cutoffs), the descriptor/gate
methodology developed this session (redundancy/leakage/role/placement
gates, why each was needed, the five failed-then-fixed rounds), dataset
lineage (Pilot-25 -> Expansion-75 -> Dataset-100 -> v1 remediation ->
round2), training approach (MACE LoRA fine-tuning), and current status.
Updated after every stage below — this is the persistent "explain the
project to a new reader" document, distinct from `SESSION_STATE...md`
(which is a resume-checkpoint, not an explainer).

### Stage 2 — Assemble cfg101-cfg108
Extract energy/forces/stress from each config's QE XML using the exact
convention already validated for round2 (`extract_dataset75.py` method:
Hartree->eV, Bohr->Angstrom, ASE stress-sign convention). Produce labeled
extxyz (all 8, plus TRAIN/VALIDATION split files), round-trip verify, write
a validation report — mirroring Stage 12 of the prior work exactly. cfg109/
cfg110 stay untouched (sealed, geometry-only, never read for labels).

### Stage 3 — Merge into one canonical combined dataset
Union Dataset-100 + newly-assembled cfg101-108 + round2 (already assembled)
into a single combined dataset. Checks before finalizing: no config-ID
collisions, no duplicate geometries across the full population, and a
**final population-level re-check of gates (a)-(d)** now that the full
combined TRAIN/VALIDATION set exists together for the first time (this is
a consistency check, not a redesign — the roles were already decided
per-round at design time). Report result.

### Stage 4 — Confirm split strategy
**Confirm the split** from "Grounding facts" above (TRAIN 75 / VALIDATION
18 / TEST+HOLDOUT 20 unchanged / SEALED 2) — **open question below needs
your sign-off**, since it affects whether TEST/HOLDOUT gets any new
members. No pod/300-round planning happens in this stage — that's deferred
(see "Deferred / advanced stage" below).

### Stage 5 — Execute the split
Write the final combined `TRAIN`/`VALIDATION` extxyz files (TEST/BLIND_HOLDOUT
untouched, just referenced), manifests, hashes. Report.

### Stage 6 — Train
Run MACE LoRA fine-tuning on the merged split, same method/hyperparameters
as the existing Dataset-100 run (foundation model, LoRA rank 4, etc.) with
updated dataset paths. Expected wall time ~380-400s (see above) — fast
enough to run in the foreground, not a long-running/tmux case. Report
training outcome (final losses, RMSEs, checkpoint selected).

### Stage 7 — Interim gate evaluation
Per `AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt`'s interim (non-sealed,
threshold-free) gate: relative-energy error on cfg043 (HOLDOUT, not sealed)
and cfg115 (VALIDATION, not sealed) — new model vs the OLD Dataset-100
model. No pass/fail threshold at this stage; this is a progress signal into
the 300-round, not a go/no-go gate. Report the two numbers.

## Deferred / advanced stage (not part of this plan, explicit go-ahead needed later)

The 300-structure round — sizing it, designing the collision-safe
partitioning/naming convention for the 10 external pods (separate machines,
sharing a network volume, per your clarification), timing/scheduling
estimates, and the actual scientific design (strains/rattle/roles) of the
~185 new configs needed to reach 300 — is explicitly **out of scope for
this plan**. It starts fresh as its own stage when you're ready to take it
up, not folded into the current merge -> split -> train pass.

## Open question before Stage 4 executes

Dataset-100 carved out a TEST + BLIND_HOLDOUT set (20 structures) as a
generalization control, independent of TRAIN/VALIDATION. Neither v1
(cfg101-110) nor round2 (cfg111-115) were designed with any TEST/HOLDOUT
role — cfg109/110 (sealed CONFIRMATION_HOLDOUT) currently play a similar
"final check" role for this remediation branch specifically. My default
plan is to **leave Dataset-100's TEST/BLIND_HOLDOUT exactly as-is** (no new
members added to it) and let cfg109/110 continue to serve as this branch's
own final holdout, unsealed once at the very end per the roadmap. Flag if
you'd rather do something different here before I proceed to Stage 4.
