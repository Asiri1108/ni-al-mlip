#!/usr/bin/env python
"""
Ni-Al MACE screening tool  (Phase 14 deliverable)
=================================================

Decides whether the al3ni_combined227_lora_v1 MACE model may be trusted on a
given structure, and only then reports energetics.

The verdict is printed FIRST. For an UNRELIABLE input the tool refuses to print
energetics at all - a silently-produced number for an out-of-range composition
is the exact failure mode this model exhibits (Phase 13.1: pure Al is wrong by
+48 meV/atom, pure Ni by +113 meV/atom, with no internal warning whatsoever).

USAGE
  python screening_tool.py --demo
  python screening_tool.py --bulk Ni fcc 3.52
  python screening_tool.py --cif  mystructure.cif
  python screening_tool.py --phase AlNi --scale 1.04
  python screening_tool.py --mp mp-1487            (needs mp-api + MP_API_KEY)

DISTANCE METRIC
  d = ||F - I||_F, the Frobenius norm of the deformation gradient relative to the
  phase's relaxed reference cell. Measured Spearman correlation with |error| is
  +0.668 over the 227 QE/PBE configurations.

  Why this and not the 3-component descriptor originally specified: that form
  (shape-RMSD + volume + strain, equal-weight z-scores) scores only +0.068. Its
  shape/rattle term is ANTI-correlated with error (-0.054), because the rattle
  family has the largest shape-RMSD and the smallest error (0.149 meV/atom), and
  its volume term as z-scored is inert (+0.023). Strain alone carries the signal,
  and it already captures isotropic volume change analytically: for F = sI,
  ||F - I||_F = sqrt(3)|s - 1|.

CALIBRATION (Phase 13, 227 configurations)
  d = ||F-I||_F     mean |error|   max |error|    (meV/atom, relative energy)
    < 0.02              0.25           0.97
    0.02 - 0.04         0.83           3.06
    0.04 - 0.06         1.46           4.69
    0.06 - 0.08         3.26           9.71
    > 0.08              4.27           7.63
  TRAIN distribution: p50=0.030  p90=0.052  p99=0.088  max=0.097
  Reference points: 1% isotropic -> 0.017 ; 3% -> 0.052 ; 5% -> 0.087

KNOWN LIMITATION (do not remove this notice)
  The metric uses cell strain only, so it CANNOT resolve rattle-only differences:
  two structures at identical strain but different internal displacement receive
  an identical distance. 63 such matched-cell pairs exist in the training set.
  This is a stronger form of the blind spot noted in the original design.
"""
import os
import sys
import argparse

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# --- QE/PBE elemental chemical potentials. The ONLY admissible references. ----
MU_AL = -537.46115182
MU_NI = -4670.57345642
X_MIN, X_MAX = 0.25, 0.75

# TRAIN distribution of d = ||F - I||_F (Phase 13.3)
TRAIN_D_P90, TRAIN_D_MAX = 0.0520, 0.0970

MODEL = os.path.join(ROOT, "work", "archive", "ni_al", "models",
                     "al3ni_combined227_lora_v1", "al3ni_combined227_lora_v1.model")
DATASET = os.path.join(ROOT, "work", "archive", "ni_al", "data", "datasets",
                       "ni_al_combined227_dft.extxyz")
X_NI = {"Al3Ni": 0.25, "Al3Ni2": 0.40, "AlNi": 0.50, "Al3Ni5": 0.625, "AlNi3": 0.75}

# QE/PBE DFT formation energies of the five known phases (Phase 7)
KNOWN_EF = {"Al3Ni": -0.39673, "Al3Ni2": -0.59645, "AlNi": -0.63840,
            "Al3Ni5": -0.54684, "AlNi3": -0.41658}


def banner(verdict, reasons):
    bar = "=" * 72
    print(bar)
    print("VERDICT: " + verdict)
    print(bar)
    for r in reasons:
        print("  - " + r)
    print()


def load_references():
    from ase.io import read
    atoms = read(DATASET, ":")
    ref = {a.info["phase"]: a for a in atoms if a.info["config_type"] == "relaxed"}
    return atoms, ref


def composition(a):
    s = a.get_chemical_symbols()
    n_al, n_ni = s.count("Al"), s.count("Ni")
    other = sorted(set(s) - {"Al", "Ni"})
    n = len(s)
    return n_al, n_ni, other, (n_ni / n if n else float("nan"))


def match_known_phase(a, ref):
    """If `a` is a strained/scaled variant of a known phase, return (phase, F).

    Requires the same atom count, the same species multiset and matching
    fractional coordinates. That correspondence is what makes the calibrated
    strain/volume distance meaningful; without it the metric is undefined.
    """
    for ph, r in ref.items():
        if len(a) != len(r):
            continue
        if sorted(a.get_chemical_symbols()) != sorted(r.get_chemical_symbols()):
            continue
        try:
            F = np.linalg.solve(r.cell.array, a.cell.array)
        except np.linalg.LinAlgError:
            continue
        d = a.get_scaled_positions() - r.get_scaled_positions()
        d -= np.round(d)
        if np.abs(d).max() < 5e-2:      # tolerant: rattle is allowed
            return ph, F
    return None, None


def distance_to_train(a, ph, F, ref):
    """d = ||F - I||_F. Volume deviation is reported for context only; it is NOT
    part of the distance (see the module docstring)."""
    r = ref[ph]
    dvol = a.get_volume() / len(a) - r.get_volume() / len(r)
    strain = float(np.linalg.norm(F - np.eye(3), ord="fro"))
    return strain, dvol, strain


def expected_error(d):
    for hi, mean, mx in [(0.02, 0.25, 0.97), (0.04, 0.83, 3.06), (0.06, 1.46, 4.69),
                         (0.08, 3.26, 9.71), (float("inf"), 4.27, 7.63)]:
        if d < hi:
            return mean, mx
    return 4.27, 9.71


def formation_energy(E, symbols):
    n_al = symbols.count("Al")
    n_ni = symbols.count("Ni")
    return (E - n_al * MU_AL - n_ni * MU_NI) / (n_al + n_ni)


def screen(a, relax=True):
    from ase.optimize import FIRE
    from ase.filters import FrechetCellFilter
    from mace.calculators import MACECalculator

    _, ref = load_references()
    n_al, n_ni, other, x = composition(a)
    reasons = []

    # ---- gate 1: composition -------------------------------------------
    if other:
        banner("UNRELIABLE",
               ["Structure contains element(s) %s. This model was trained on "
                "Al-Ni only (Z = 13, 28)." % ", ".join(other),
                "Energetics withheld: the model has no parameters for these species."])
        return {"verdict": "UNRELIABLE", "reason": "foreign elements"}

    if not (X_MIN - 1e-9 <= x <= X_MAX + 1e-9):
        banner("UNRELIABLE", [
            "x_Ni = %.4f is outside the validated range [%.2f, %.2f]." % (x, X_MIN, X_MAX),
            "Measured behaviour outside this range (Phase 13.1): pure Al is wrong by "
            "+48.4 meV/atom, pure Ni by +112.5 meV/atom.",
            "The model returns smooth, finite, confident values there with NO internal "
            "warning - which is precisely why this gate exists.",
            "Energetics withheld."])
        return {"verdict": "UNRELIABLE", "reason": "composition out of range", "x_Ni": x}

    # ---- gate 2: distance to the training envelope ----------------------
    ph, F = match_known_phase(a, ref)
    if ph is None:
        d = None
        verdict = "CAUTION"
        reasons += [
            "Structure is NOT a strained variant of any of the five known phases "
            "(Al3Ni, Al3Ni2, AlNi, Al3Ni5, AlNi3).",
            "The calibrated strain/volume distance is UNDEFINED for a novel structure "
            "type, so no quantitative error estimate can be quoted.",
            "This is a NOVEL STRUCTURE TYPE, not merely a thin region: the training set "
            "contains no configuration of this kind at any density."]
    else:
        d, dvol, strain = distance_to_train(a, ph, F, ref)
        mean_e, max_e = expected_error(d)
        reasons += [
            "Matches known phase %s (x_Ni = %.3f)." % (ph, X_NI[ph]),
            "Distance d = ||F-I||_F = %.4f (TRAIN p90 = %.4f, max = %.4f); "
            "equivalent to about %.1f%% isotropic strain."
            % (d, TRAIN_D_P90, TRAIN_D_MAX, d / np.sqrt(3) * 100),
            "Volume deviation %+.4f A^3/atom (context only, not part of d)." % dvol]
        if d > TRAIN_D_MAX:
            verdict = "CAUTION"
            reasons += [
                "EXTRAPOLATION: d exceeds the largest distance present in TRAIN (%.3f). "
                "No training configuration is this far out." % TRAIN_D_MAX,
                "Expected error is worse than %.2f meV/atom; the calibration does not "
                "extend here." % max_e]
        elif d > TRAIN_D_P90:
            verdict = "CAUTION"
            reasons += [
                "THIN DENSITY: inside the training envelope but beyond its 90th "
                "percentile - few training points nearby.",
                "Expected |error| ~ %.2f meV/atom, worst observed %.2f." % (mean_e, max_e)]
        else:
            verdict = "RELIABLE"
            reasons += [
                "Well inside the training envelope.",
                "Expected |error| ~ %.2f meV/atom, worst observed in this band %.2f."
                % (mean_e, max_e)]

    # ---- physics-based warning that applies regardless of the above -----
    if len(a) > 1:
        dmin = float(a.get_all_distances(mic=True)[np.triu_indices(len(a), 1)].min())
        if dmin < 1.8:
            if verdict == "RELIABLE":
                verdict = "CAUTION"
            reasons.append(
                "Minimum interatomic distance %.3f A is below 1.8 A. The model has no "
                "short-range repulsive core (Phase 13.2) and UNDERESTIMATES repulsion at "
                "close approach. Not valid for cascades or radiation damage." % dmin)

    banner(verdict, reasons)

    # ---- energetics (only reached for RELIABLE / CAUTION) ---------------
    calc = MACECalculator(model_paths=MODEL, device="cpu", default_dtype="float64")
    w = a.copy()
    w.calc = calc
    E0 = w.get_potential_energy()
    print("ENERGETICS")
    print("  composition             Al%d Ni%d   x_Ni = %.4f   N = %d" % (n_al, n_ni, x, len(a)))
    print("  E/atom (as given)       %.6f eV" % (E0 / len(w)))
    if relax:
        opt = FIRE(FrechetCellFilter(w), logfile=os.devnull)
        opt.run(fmax=0.01, steps=500)
        print("  relaxation              %d steps, converged = %s"
              % (opt.get_number_of_steps(), opt.converged()))
        E0 = w.get_potential_energy()
        print("  E/atom (relaxed)        %.6f eV" % (E0 / len(w)))
        print("  V/atom (relaxed)        %.4f A^3" % (w.get_volume() / len(w)))
    ef = formation_energy(E0, w.get_chemical_symbols())
    print("  E_formation (QE mu)     %.6f eV/atom" % ef)
    if ef > 0:
        print("    NOTE: positive formation energy - predicted UNSTABLE vs Al + Ni.")

    print("\n  Position vs the five known phases (QE/PBE DFT formation energies):")
    for k in sorted(KNOWN_EF, key=lambda kk: X_NI[kk]):
        mark = "  <-- this structure sits here" if abs(X_NI[k] - x) < 1e-6 else ""
        print("    %-7s x_Ni=%.3f  E_f = %+.5f eV/atom%s" % (k, X_NI[k], KNOWN_EF[k], mark))

    xs = sorted(X_NI.items(), key=lambda kv: kv[1])
    lo = max([p for p in xs if p[1] <= x], key=lambda p: p[1], default=None)
    hi = min([p for p in xs if p[1] >= x], key=lambda p: p[1], default=None)
    if lo and hi and hi[1] > lo[1]:
        t = (x - lo[1]) / (hi[1] - lo[1])
        tie = KNOWN_EF[lo[0]] * (1 - t) + KNOWN_EF[hi[0]] * t
        print("\n  Tie-line between %s and %s at x_Ni=%.4f: %+.5f eV/atom"
              % (lo[0], hi[0], x, tie))
        print("  This structure:                              %+.5f eV/atom" % ef)
        print("  %s by %.2f meV/atom"
              % ("BELOW the tie-line (would be stable)" if ef < tie
                 else "ABOVE the tie-line (would decompose)", abs(ef - tie) * 1000))

    if verdict == "CAUTION":
        print("\n  REMINDER: verdict is CAUTION. Treat every number above as indicative "
              "only, and confirm with DFT before use.")
    return {"verdict": verdict, "x_Ni": x, "distance": d, "E_f_eV_atom": ef}


def main():
    p = argparse.ArgumentParser(description="Ni-Al MACE reliability screening")
    p.add_argument("--cif")
    p.add_argument("--bulk", nargs=3, metavar=("SYMBOL", "STRUCTURE", "A"))
    p.add_argument("--phase", choices=sorted(X_NI))
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--mp", metavar="MP_ID")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--no-relax", action="store_true")
    args = p.parse_args()

    from ase.io import read
    from ase.build import bulk as ase_bulk

    if args.demo:
        _, ref = load_references()
        expanded = ref["AlNi"].copy()
        expanded.set_cell(expanded.cell.array * 1.06, scale_atoms=True)
        cases = [("pure Ni fcc - composition OOD", ase_bulk("Ni", "fcc", a=3.52, cubic=True)),
                 ("AlNi at equilibrium - in distribution", ref["AlNi"].copy()),
                 ("AlNi expanded 6% - beyond the envelope", expanded)]
        for name, a in cases:
            print("\n" + "#" * 72)
            print("# CASE: " + name)
            print("#" * 72)
            screen(a, relax=not args.no_relax)
        return

    if args.cif:
        a = read(args.cif)
    elif args.bulk:
        a = ase_bulk(args.bulk[0], args.bulk[1], a=float(args.bulk[2]), cubic=True)
    elif args.phase:
        _, ref = load_references()
        a = ref[args.phase].copy()
        if args.scale != 1.0:
            a.set_cell(a.cell.array * args.scale ** (1 / 3.0), scale_atoms=True)
    elif args.mp:
        try:
            from mp_api.client import MPRester
        except ImportError:
            sys.exit("mp-api not installed. pip install mp-api, and set MP_API_KEY.")
        key = os.environ.get("MP_API_KEY")
        if not key:
            sys.exit("Set MP_API_KEY to use --mp.")
        from pymatgen.io.ase import AseAtomsAdaptor
        with MPRester(key) as m:
            s = m.get_structure_by_material_id(args.mp)
        a = AseAtomsAdaptor.get_atoms(s)
    else:
        p.print_help()
        return
    screen(a, relax=not args.no_relax)


if __name__ == "__main__":
    main()
