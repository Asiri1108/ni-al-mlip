# Round-285 Sealed Pair Revision (design-only, NO DFT run)

Generated UTC: 2026-08-18T14:02:14.682095+00:00

Replaces cfg295/cfg296 (retired -- see round285_sealed_retirement_log.txt). Root cause: a sealed interpolation point inside a 0.5-point-dense TRAIN grid is bound to <=0.25 points from its nearest TRAIN neighbor. Density and seal-isolation cannot coexist in the same interval -- the only interval NOT densified to 0.5 points is 3.0%->4.0% (blocked by leakage against cfg043 at s=3.5000%), so that is where the new seal goes.

gate(b) fresh threshold (min Al3Ni TRAIN<->RESERVED, combined-220): 0.3269
Reverse-leakage check: distance to ALL 15 TRAIN rungs (8 existing iso/vr members + the 7 newly-approved round285 candidates) -- this is exactly the check that was missing for cfg295/cfg296.

| config_id | family | s (%) | min dist ALL TRAIN (15 rungs) | nearest TRAIN | vs 0.734644 (stale/wrong regime) | vs fresh 0.3269 | dist to RESERVED | nearest RESERVED |
|---|---|---|---|---|---|---|---|---|
| cfg297_Al3Ni_iso_expansion | iso_expansion | 3.50 | 0.481337 | cfg029_Al3Ni_iso_expansion | BELOW_0.734644 | PASS | 0.322191 | cfg043_Al3Ni_volume_rattle_expansion |
| cfg298_Al3Ni_volume_rattle_expansion | volume_rattle_expansion | 3.50 | 0.505965 | cfg292_Al3Ni_volume_rattle_expansion | BELOW_0.734644 | PASS | 0.195205 | cfg043_Al3Ni_volume_rattle_expansion |

**Neither candidate clears 0.734644** -- and this is expected, not a failure: 0.734644 was derived from a much sparser, earlier Al3Ni population. A 1.0-point-wide TRAIN gap at the current (much denser) combined-220+round285 TRAIN density cannot structurally produce a point 0.734644 away in this descriptor space -- that threshold belongs to a different regime and should not be used to judge isolation here (EXPANSION_BATCH_DESIGN_POLICY.md: re-derive per regime, never reuse verbatim). Both candidates clear the regime-correct fresh threshold (0.3269) comfortably, by 47-53%.

cfg297 vs cfg298 (the two new sealed candidates, cross-checked against each other): 0.265173 -- matches the project's established legitimate matched-strain-family separation scale (~0.27-0.28, same as e.g. iso/volume_rattle pairs elsewhere in this dataset), not a duplicate.

## Disclosed limitation: cfg298 vs cfg043 descriptor blind spot

cfg298 (volume_rattle_expansion, s=3.5%) and cfg043 (volume_rattle_expansion, s=3.5000%, RESERVED) are a matched-strain-family pair at (numerically) the same strain: d_shape=0.012186, d_vol=3.14e-08, d_strain=1.19e-09. d_vol/d_strain collapse to ~0 by construction -- the known descriptor blind spot for matched-strain rattle pairs (same pattern as the historical cfg106/cfg108 false-duplicate flags, later confirmed as measurement artifacts). Not a defect: cfg298's independent rattle draw (seed 20262298) produces genuinely different atomic positions and will produce genuinely different DFT labels -- only the descriptor cannot certify that independence via d_vol/d_strain alone. Per the user's explicit framing: proximity between two never-trained-on points (a new seal and an existing holdout) is test redundancy, not leakage -- there is no failure mode this creates for training integrity.

## Status
cfg297_Al3Ni_iso_expansion and cfg298_Al3Ni_volume_rattle_expansion ACCEPTED as the new sealed confirmation pair, replacing cfg109/cfg110's vacated role (cfg295/cfg296 retired). Geometry and QE input written; DFT NOT run; energy/forces/stress do not exist yet. Sealed immediately: no future script may read their DFT labels except at a single, later, explicitly designated unsealing event.
