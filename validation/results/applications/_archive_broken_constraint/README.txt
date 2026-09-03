First Phase 15 run, archived 2026-09-03.

The APB (15.2) and GSFE (15.3) relaxations used

    set_constraint([FixedPlane(i, (0, 0, 1)) ...])

under a comment reading "relax only perpendicular to the fault plane". ASE's
FixedPlane confines an atom TO the plane whose normal is the given direction -
so this froze z and left the in-plane coordinates free, the exact opposite of
the stated intent. FixedLine(i, (0,0,1)) is the constraint that implements it.

Consequence for 15.3: every intermediate shift relaxed back to f=0 or forward
to f=1, so the "curve" was a step function - ~0 mJ/m^2 for f<=0.5 and ~202
(the APB value) for f>=0.6. The reported "unstable fault energy 203.5 mJ/m^2"
was just the maximum of that step, not a saddle-point energy.

Measured directly at f=0.5 on a 96-atom slab, same cell, same model:

    FixedPlane : gamma =    0.3 mJ/m^2, block slid -0.6369 A of the imposed
                 +1.2612 A, out-of-plane relaxation 0.0000 A
    FixedLine  : gamma = 1347.0 mJ/m^2, block slid +0.0000 A,
                 out-of-plane relaxation 0.0750 A

Consequence for 15.2: the APB at f=1.0 is a genuine local minimum in the
in-plane coordinate, so it did not slide and 202.3 mJ/m^2 is a plausible
number - but it was computed with z frozen, i.e. with no perpendicular
relaxation, so it is an unrelaxed UPPER BOUND.

15.1 (NEB vacancy barrier, 1.1683 eV) and 15.4 (high-T probe, 5/5 phases
intact) use no such constraint and were unaffected.
