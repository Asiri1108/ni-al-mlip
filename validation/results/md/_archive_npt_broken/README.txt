Broken NPT trajectories, archived 2026-09-02.

These 10 NPT runs were produced with compressibility_au=5e-7 in
scripts/phase11_md.py. ASE expects that parameter in atomic units (A^3/eV);
5e-7 is a bar^-1-scale number, roughly 2e6 times too small. The Berendsen
scaling factor was therefore 1.0 to within 1e-10 and the cell never moved:
lattice constant a changed by ~1e-7 A over the full 5 ps in every run.

Consequence: they are valid as NVT stability data but carry no barostat
information, and md_thermal_expansion_broken.csv derived from them gives
alpha_linear ~1.5e-11 /K against a physical ~1e-5 /K -- six orders of
magnitude low. Do not use those numbers.

Verified by a controlled probe (identical cell, identical initial velocities,
900 K, 0.8 ps, Al3Ni2 40 atoms):
    compressibility_au=5e-7    -> da = +2.4e-08 A  (+0.0000 % volume)
    compressibility_au=1.1721  -> da = +4.06e-02 A (+1.51 % volume)
The corrected run's 1.51 % at 0.8 ps matches the expected equilibrium 2.7 %
scaled by 1-exp(-0.8/tau) with tau=1 ps, confirming the corrected value.

The 20 NVT trajectories were unaffected and were NOT re-run.
