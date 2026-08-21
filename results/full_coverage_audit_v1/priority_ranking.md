# Full Coverage / Extrapolation-Ceiling Audit — Priority Ranking

Read-only audit, same diagnostic method that originally caught the Al3Ni
cfg043 gap (TRAIN extrema vs every VALIDATION/TEST/BLIND_HOLDOUT point),
applied to all 5 phases and every strain family present in combined-113.
cfg109/cfg110 excluded (sealed, untouched). No structures designed or
generated here — this table exists to drive that design, not replace it.

Raw per-row data: `coverage_ceiling_report.csv` (113 configs x their
family bucket, one row per flag/status).

## Method note: 8 flags excluded as metadata artifacts, not findings

Eight Pilot-25 historical configs (`*_rattle_003`, `*_shear015_rattle002`
across AlNi/Al3Ni2/Al3Ni5/AlNi3/Al3Ni) initially flagged as extrapolation
because their `rattle_sigma_A`/`shear_value` fields are recorded as
`historical_not_recorded` in the frozen Dataset-100 manifest (coerced to
0.0 for the axis check) — their config_family *names* imply nonzero
historical values (e.g. "rattle_003" ~ sigma 0.003) that cannot be
precisely recovered from the frozen manifest. These are marked
`METADATA_GAP_NOT_EVALUABLE` in the CSV, not `EXTRAPOLATION` — excluded
from the ranking below.

## Tier 1 — CRITICAL: zero TRAIN support for an entire family/phase bucket

The most severe category — not "outside range" but **no training signal
at all** for that deformation type in that phase. Every VALIDATION/
BLIND_HOLDOUT point in these buckets is extrapolating by construction.

| Family | Phases with zero TRAIN | Phases WITH TRAIN (n) |
|---|---|---|
| **biaxial** | **Al3Ni, Al3Ni2, Al3Ni5, AlNi, AlNi3 (ALL 5)** | none |
| **shear_rattle** | Al3Ni2, Al3Ni5, AlNi, AlNi3 (4/5) | Al3Ni (1) |
| **orthorhombic** | Al3Ni2, AlNi, AlNi3 (3/5) | Al3Ni (1), Al3Ni5 (1) |
| **volume_rattle** | **AlNi3 only** | Al3Ni (5), Al3Ni2 (1), Al3Ni5 (1), AlNi (1) |

**Biaxial deformation has never been trained on, in any phase, anywhere in
this project.** Every biaxial config that exists (`cfg039`, `cfg073`,
`cfg058`, `cfg087`, `cfg099`) is VALIDATION or BLIND_HOLDOUT only. This
looks like it could be an intentional design choice (holding out an
entire deformation mode to test generalization) rather than an oversight
— but that's a design decision this audit surfaces, not one it makes.
Same pattern, less universal, for shear_rattle and orthorhombic.

**`cfg098_AlNi3_volume_rattle_compression`** (the WATCH-001 config) is the
*only* AlNi3 volume_rattle config that exists at all — confirmed by local
density: its nearest same-phase TRAIN neighbor is
`cfg091_AlNi3_iso_compression` at descriptor distance 0.6414, from a
**different deformation family entirely**. There is no volume_rattle
TRAIN anchor for AlNi3 at any distance.

## Tier 2 — HIGH: range/sign extrapolation beyond thin existing TRAIN

TRAIN support exists in these buckets but is thin (often 1 point), and a
VALIDATION/HOLDOUT member sits outside its range.

| Phase | Family | Config | Role | Margin outside TRAIN range |
|---|---|---|---|---|
| **Al3Ni5** | **uniaxial** | **cfg056_Al3Ni5_uniaxial_x_expansion** | VALIDATION | **0.033** (sign flip — TRAIN is compression-only, -0.015) |
| Al3Ni2 | volume_rattle | cfg075_Al3Ni2_volume_rattle_expansion | BLIND_HOLDOUT | 0.060 |
| Al3Ni5 | volume_rattle | cfg060_Al3Ni5_volume_rattle_expansion | BLIND_HOLDOUT | 0.060 |
| Al3Ni | shear_rattle | cfg044_Al3Ni_shear_rattle_xy_negative | BLIND_HOLDOUT | 0.045 |
| Al3Ni | volume_rattle | cfg107_Al3Ni_volume_rattle_compression | VALIDATION | 0.015 (+ 2.22x internal gap, see below) |

**`cfg056_Al3Ni5_uniaxial_x_expansion`** (the other WATCH-001 config):
Al3Ni5's only uniaxial TRAIN point (`cfg049_Al3Ni5_uniaxial_y_compression`,
-0.015) is *compression on a different axis* — cfg056 is *expansion*
(+0.018). This is the same category of error as the original cfg043
diagnosis (sign/direction extrapolation), just smaller in scope. Local
density confirms: nearest same-phase TRAIN neighbor is
`cfg046_Al3Ni5_iso_expansion` at distance 0.8999 — again, a different
deformation family, not a genuine uniaxial anchor.

**`cfg107_Al3Ni_volume_rattle_compression`** is notable: this session's v1
remediation fixed the Al3Ni volume_rattle *expansion* ceiling (now +5.60%
via cfg113/114) but never touched the *compression* side — TRAIN
compression ceiling there is still -0.025 (`cfg037`, unchanged since
Dataset-100), and cfg107 (VALIDATION, -0.040) sits beyond it. This is the
untouched mirror of the exact problem this whole session's work fixed on
the expansion side.

## Tier 3 — MEDIUM: smaller range extrapolations

| Phase | Family | Config | Role | Margin |
|---|---|---|---|---|
| Al3Ni2 | shear | cfg074_Al3Ni2_shear_xz_negative | BLIND_HOLDOUT | 0.012 |
| Al3Ni5 | shear | cfg059_Al3Ni5_shear_yz_negative | BLIND_HOLDOUT | 0.012 |
| Al3Ni5 | rattle | cfg061_Al3Ni5_rattle_xlarge | BLIND_HOLDOUT | 0.010 |
| Al3Ni | shear | cfg042_Al3Ni_shear_xz_negative | BLIND_HOLDOUT | 0.008 |
| Al3Ni | uniaxial | cfg041_Al3Ni_uniaxial_z_compression | BLIND_HOLDOUT | 0.007 |

## Sparse internal-gap flag (not an edge problem, a hole)

`Al3Ni / volume_rattle`: consecutive TRAIN gap between -0.0200 and
+0.0200 (size 0.040 vs median consecutive spacing 0.018, 2.22x) — the
zone immediately around zero strain in this family is thinner than the
rest of the TRAIN ladder, though not unsupported (unlike Tier 1 items).

## Well covered — no action needed

**Isotropic** is the best-covered family in every phase (TRAIN counts:
Al3Ni 11, Al3Ni2/Al3Ni5/AlNi/AlNi3 6 each) — zero extrapolation flags
anywhere. Plain **rattle** (aside from the metadata-gap historical points
and cfg061 above) is reasonably covered.

## Local density, explicit (as requested)

| Config | Nearest same-phase TRAIN neighbor | Distance | Neighbor's family |
|---|---|---|---|
| cfg098_AlNi3_volume_rattle_compression | cfg091_AlNi3_iso_compression | **0.6414** | iso_compression (different family) |
| cfg056_Al3Ni5_uniaxial_x_expansion | cfg046_Al3Ni5_iso_expansion | **0.8999** | iso_expansion (different family) |

Same descriptor methodology as `geometry_redundancy.csv` (species-grouped
shape RMSD + vol/atom + Green-Lagrange strain, z-scored by that phase's
own population), computed fresh per-phase since AlNi3 (4 atoms) and
Al3Ni5 (8 atoms) have different compositions/atom counts than Al3Ni (16
atoms) — not directly comparable to the Al3Ni-specific 0.794907 threshold,
but same method, useful as a same-methodology reference point. Both
configs' nearest TRAIN anchors are from an unrelated deformation family —
low local density is confirmed, consistent with a genuine coverage gap
rather than pure training noise.

## Top 3 priorities for the 300-structure round

1. **Biaxial deformation, all 5 phases** — the single most systemic gap:
   zero TRAIN representation anywhere, in any phase. Whether this was
   intentional (generalization holdout) or an oversight is a design call,
   but it can no longer be assumed benign without a decision either way.
2. **AlNi3 volume_rattle (cfg098) and Al3Ni5 uniaxial expansion (cfg056)**
   — the two WATCH-001 configs. Both confirmed as genuine coverage gaps
   (zero/wrong-direction TRAIN support, low local density with a
   different-family nearest neighbor), directly explaining their observed
   degradation. Highest-confidence, most actionable items.
3. **Shear_rattle (4/5 phases) and orthorhombic (3/5 phases)** — same
   category as biaxial, slightly less universal. Combined with biaxial,
   these three families account for the large majority of Tier 1 flags.

Worth flagging separately even though it didn't make the top 3: the
**Al3Ni volume_rattle compression-side mirror gap (cfg107)** — this
session fixed the expansion ceiling but left the compression side exactly
where Dataset-100 left it. Cheap to close given the ladder-extension
method already validated this session.
