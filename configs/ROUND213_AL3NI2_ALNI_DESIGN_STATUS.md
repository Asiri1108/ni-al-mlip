# Round-213: Al3Ni2 shear-gap minimum + AlNi thin-bucket closure (design-only, NO DFT)

Generated UTC: 2026-08-16T18:20:08.336220+00:00

## Al3Ni2 shear_xy_negative magnitude sweep (finding minimum that clears gate (a))

| magnitude | status |
|---|---|
| -0.030 | REJECTED |
| -0.038 | REJECTED |
| -0.045 | KEPT |

Minimum passing magnitude: **-0.045**

## AlNi thin-bucket candidates

| config_id | purpose | value | gate(a) | gate(c) | status |
|---|---|---|---|---|---|
| cfg280_AlNi_shear_xy_positive | close AlNi/shear thin bucket (n=1->3), axis 1/2 | 0.0300 | PASS | PASS | **KEPT** |
| cfg281_AlNi_shear_yz_positive | close AlNi/shear thin bucket (n=1->3), axis 2/2 | 0.0300 | PASS | PASS | **KEPT** |
| cfg282_AlNi_volume_rattle_iso_negative | close AlNi/volume_rattle thin bucket (n=2->3), deeper compression | -0.0400 | PASS | PASS | **KEPT** |

## Totals

Proposed: 6
KEPT: 4

## Not done in this pass
DFT has not been run. No merge into any TRAIN/VALIDATION split. Neither phase (AlNi, Al3Ni2)
has any sealed data -- cfg109/cfg110 (Al3Ni-only) were never read, not even for geometry.
