# Cross-Phase Drift Watchlist

Tracks potential LoRA fine-tuning interference on phases **not** targeted
by a given remediation round — i.e. whether fine-tuning on new Al3Ni data
measurably disturbs the model's fit on AlNi/Al3Ni2/AlNi3/Al3Ni5, which
received no new TRAIN/VALIDATION data of their own. Living document,
checked and appended to at each future retraining round. Distinct from
`AL3NI_INTERIM_GATE_STATUS.txt` (a single-run progress snapshot for the
cfg043/cfg115 remediation-specific gate) — this tracks a different,
open-ended question across multiple rounds.

## WATCH-001 — opened 2026-08-15, after combined-113 training (Stage 6/7)

**Status: OPEN**

**Observation:** comparing OLD (`dataset100_matpes_pbe_lora_v1`) vs NEW
(`al3ni_combined113_lora_v1`) on the original Dataset-100 VALIDATION-15,
two configs in phases untouched by this remediation round (only Al3Ni
gained new TRAIN/VALIDATION data) showed measurable relative-energy-error
degradation:

- `cfg098_AlNi3_volume_rattle_compression`: 0.057 -> -0.474 meV/atom (sign
  flip, ~8x magnitude)
- `cfg056_Al3Ni5_uniaxial_x_expansion`: 0.926 -> 1.135 meV/atom

**Context / why this isn't (yet) alarming:** both remain far below any
concerning threshold in absolute terms (historical red line ~21 meV/atom
on AlNi, from Pilot-25). The picture is mixed rather than purely positive:
aggregate force RMSE (0.00365 -> 0.00385 eV/Angstrom) and stress RMSE
(0.32253 -> 0.34344 GPa) on the same original-15 set both ticked up
slightly, even as the primary relative-energy-error metric improved in
aggregate (RMSE 0.4476 -> 0.4163 meV/atom). This is a **single training
run with no repeated-seed baseline** — it is not yet possible to
distinguish real cross-phase interference (LoRA adapter capacity being
pulled toward the newly-emphasized Al3Ni region at the expense of other
phases) from ordinary training stochasticity (a different run with a
different seed could plausibly show similar-sized fluctuations on
untouched phases with no interference at all).

**Action (deferred, tied to the next retraining round):**
1. After the 300-structure retraining round, re-check these same two
   configs, plus the force/stress aggregates on the original 15
   validation configs.
2. **If the degradation is consistent or growing** across rounds:
   investigate LoRA interference before the 500-structure round —
   candidate mitigations include phase-balanced sampling, separate
   per-phase adapters, or regularization against forgetting.
3. **If it does not reappear, or does not grow:** treat it as training
   noise and close this watch item.

**Source data:** the OLD-vs-NEW per-config comparison and aggregate
figures above come from the read-only regression analysis performed after
Stage 7 (see the conversation record / `AL3NI_INTERIM_GATE_STATUS.txt` for
the Stage 7 cfg043/cfg115 result this analysis extended). Not re-derived
here; this file exists to make sure that finding isn't lost.

## Update log

- 2026-08-15: WATCH-001 opened.
