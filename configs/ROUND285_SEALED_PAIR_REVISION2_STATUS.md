# Round-285 Sealed Pair Revision 2 (design-only, NO DFT run)

Generated UTC: 2026-08-18T14:11:29.671317+00:00

cfg298 retired (descriptor-degenerate with the feedback probe cfg043 -- see retirement log for full reasoning). cfg297 retained unchanged. This revision proposes cfg299_Al3Ni_volume_rattle_expansion as the replacement second seal.

## cfg299 (volume_rattle_expansion, s=3.6%)

min_dist to nearest of 15 TRAIN rungs: 0.424441 (nearest: cfg292_Al3Ni_volume_rattle_expansion) vs threshold 0.3269 -> **PASS**

Degeneracy check (d_vol, d_strain must both be >> 1e-3 to be non-degenerate; the true-collapse floor observed for cfg298 vs cfg043 was ~1e-8/1e-9):

| reference | d_shape | d_vol | d_strain | degenerate? |
|---|---|---|---|---|
| cfg043 | 0.012485 | 4.74e-02 | 1.79e-03 | no |
| cfg109 | 0.023725 | 1.91e-01 | 7.19e-03 | no |
| cfg110 | 0.017635 | 1.91e-01 | 7.19e-03 | no |
| cfg115 | 0.064971 | 8.21e-01 | 3.08e-02 | no |
| cfg297 | 0.013624 | 4.74e-02 | 1.79e-03 | no |

**Overall degeneracy verdict: ALL CLEAR**

## Status
cfg299_Al3Ni_volume_rattle_expansion ACCEPTED as the replacement second seal. cfg297_Al3Ni_iso_expansion retained unchanged. Sealed pair is now {cfg297, cfg299}. Geometry and QE input written; DFT NOT run.
