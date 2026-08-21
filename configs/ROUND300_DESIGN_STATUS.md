# Round-300 Batch: Generated and Gate-Checked (design-only, NO DFT run)

Generated UTC: 2026-08-16T11:35:47.313979+00:00
Source roster: /workspace/ni_al/data/al3ni_remediation_v1/round300_scope_roster.csv (128 proposed)
cfg109/cfg110 (sealed): geometry-only read for gate (b), Al3Ni candidates only. Labels never touched.

## Per-phase gate thresholds (freshly derived this round, from current combined-129 population)

| Phase | n population | n TRAIN | redundancy threshold (5th pct) | leakage threshold (Al3Ni only) |
|---|---|---|---|---|
| AlNi | 22 | 16 | 0.941703 | N/A |
| Al3Ni | 38 | 27 | 0.434006 | 0.451548 |
| Al3Ni2 | 22 | 15 | 0.885371 | N/A |
| Al3Ni5 | 25 | 17 | 0.913861 | N/A |
| AlNi3 | 22 | 16 | 0.776411 | N/A |

## Results

Proposed: 128
KEPT: 82
REJECTED: 46
  - failed gate (a) redundancy: 46
  - failed gate (b) leakage: 0
  - failed gate (c) duplicate: 0

## Per-phase kept/proposed

| Phase | Kept | Proposed |
|---|---|---|
| AlNi | 16 | 26 |
| Al3Ni | 17 | 23 |
| Al3Ni2 | 15 | 27 |
| Al3Ni5 | 15 | 25 |
| AlNi3 | 19 | 27 |

## Per-family kept

| Family | Kept |
|---|---|
| biaxial | 22 |
| orthorhombic | 25 |
| shear_rattle | 12 |
| uniaxial | 19 |
| volume_rattle | 4 |

## Sizing outcome

Current project total: 131
KEPT this round: 82
Projected total if DFT'd and merged: 131 + 82 = **213** (71% of the 300 milestone)

## What this does NOT do

- Does NOT run DFT. Structures and QE inputs are frozen and ready, not submitted.
- Does NOT merge anything into any TRAIN/VALIDATION file.
- cfg109/cfg110 remain sealed; only geometry was read for gate (b) (Al3Ni candidates only).

Full per-candidate gate results: `/workspace/ni_al/data/al3ni_remediation_v1/round300_gate_report.csv`
Frozen manifest (KEPT only): `/workspace/ni_al/data/al3ni_remediation_v1/round300_manifest.csv`
