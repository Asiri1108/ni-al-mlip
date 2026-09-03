"""Task C: test the 'dilution hypothesis'.

Hypothesis under test: combined-227 loses to pilot25 on some configurations
because the high-strain / relevant training signal that pilot25 carries in
concentrated form is DILUTED in the 189-config combined-227 TRAIN set.

Data analysis only - no training, no model evaluation. Everything here is a
property of the datasets themselves.

Strain metric: the project's own definition, taken from
results/distortion/error_vs_strain.csv and reproduced here to 2e-14:

    lin_strain = (V/V0)^(1/3) - 1

where V and V0 are per-atom volumes of the configuration and of that phase's
relaxed reference. It is SIGNED: negative = compression, positive = expansion.
It is purely volumetric, so volume-preserving deformations (shear, pure rattle)
are exactly 0 by construction - a limitation stated explicitly in the report.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, common as C
from ase.io import read

D = C.DATA
OUT = C.RESULTS

atoms227, split227 = C.load_dataset("combined227")
relaxed = {a.info["phase"]: a for a in atoms227 if a.info["config_type"] == "relaxed"}
V0 = {p: r.get_volume()/len(r) for p, r in relaxed.items()}

pilot = read(os.path.join(D, "ni_al_pilot_train_15.extxyz"), ":")

# The two sets must be measured against the SAME reference volumes or the
# comparison is meaningless. Confirm pilot's own relaxed cells agree with the
# combined227 relaxed cells before using one reference for both.
ref_check = []
for a in pilot:
    if a.info["config_type"] == "relaxed":
        ph = a.info["phase"]
        ref_check.append((ph, abs(a.get_volume()/len(a) - V0[ph])))
max_ref_mismatch = max(d for _, d in ref_check)


def lin_strain_pct(a):
    return ((a.get_volume()/len(a) / V0[a.info["phase"]]) ** (1/3) - 1) * 100


def frame(atoms_list, name):
    rows = []
    for a in atoms_list:
        rows.append({"dataset": name,
                     "config_id": a.info["config_id"],
                     "phase": a.info["phase"],
                     "family": C.family(a.info["config_type"]),
                     "lin_strain_pct": lin_strain_pct(a)})
    df = pd.DataFrame(rows)
    df["abs_strain_pct"] = df.lin_strain_pct.abs()
    return df


P = frame(pilot, "pilot25_TRAIN")
c227_train = [a for a in atoms227 if split227[a.info["config_id"]] == "TRAIN"]
K = frame(c227_train, "combined227_TRAIN")
assert len(P) == 15 and len(K) == 189, (len(P), len(K))
ALL = pd.concat([P, K], ignore_index=True)
ALL.to_csv(os.path.join(OUT, "dilution_strain_per_config.csv"), index=False)

# ------------------------------------------------------------------ histogram
EDGES = [0, 0.5, 1, 2, 3, 4, np.inf]
LABELS = ["0 (exactly)", "(0,0.5]%", "(0.5,1]%", "(1,2]%", "(2,3]%", "(3,4]%", ">4%"]

def hist(df):
    s = df.abs_strain_pct.values
    counts = [int((s == 0).sum())]
    prev = 0.0
    for hi in EDGES[1:]:
        counts.append(int(((s > prev) & (s <= hi)).sum()))
        prev = hi
    return counts

hp, hk = hist(P), hist(K)
H = pd.DataFrame({"band": LABELS, "pilot25_n": hp, "combined227_n": hk})
H["pilot25_frac"] = H.pilot25_n / len(P)
H["combined227_frac"] = H.combined227_n / len(K)
H.to_csv(os.path.join(OUT, "dilution_strain_histogram.csv"), index=False)

# ------------------------------------------------- fraction above 2% strain
# pilot25's iso configs sit at 2.0000062%, i.e. a hair ABOVE 2.000 because the
# +-2% scaling was applied to a cell whose relaxed volume is not exactly the
# reference. A naive "> 2" test therefore counts all 10 of them and reports
# pilot25 as 67% high-strain. That is a floating-point artefact of a nominal
# 2% construction, not a real property, so BOTH readings are reported.
def frac_above(df, thr, strict=True):
    s = df.abs_strain_pct.values
    n = int((s > thr).sum()) if strict else int((s >= thr - 1e-9).sum())
    return n, n/len(s)

TOL = 1e-3   # 0.001 percentage points: treats 2.0000062 as "at 2%", not above
def frac_above_tol(df, thr=2.0):
    s = df.abs_strain_pct.values
    n = int((s > thr + TOL).sum())
    return n, n/len(s)

above = {}
for nm, df in [("pilot25_TRAIN", P), ("combined227_TRAIN", K)]:
    n_naive, f_naive = frac_above(df, 2.0)
    n_tol, f_tol = frac_above_tol(df)
    above[nm] = {"n_total": len(df),
                 "n_gt_2pct_naive": n_naive, "frac_gt_2pct_naive": f_naive,
                 "n_gt_2pct_tolerant": n_tol, "frac_gt_2pct_tolerant": f_tol,
                 "n_ge_2pct": int((df.abs_strain_pct >= 2.0 - TOL).sum()),
                 "frac_ge_2pct": float((df.abs_strain_pct >= 2.0 - TOL).mean()),
                 "mean_abs_strain": float(df.abs_strain_pct.mean()),
                 "median_abs_strain": float(df.abs_strain_pct.median()),
                 "max_abs_strain": float(df.abs_strain_pct.max())}

# -------------------------------------------- Al3Ni TRAIN by strain SIGN
SIGN_TOL = 1e-6
def sign_table(df):
    d = df[df.phase == "Al3Ni"]
    comp = int((d.lin_strain_pct < -SIGN_TOL).sum())
    expa = int((d.lin_strain_pct > SIGN_TOL).sum())
    zero = int((d.lin_strain_pct.abs() <= SIGN_TOL).sum())
    return {"n_Al3Ni_TRAIN": len(d), "compression": comp, "expansion": expa,
            "volume_neutral": zero,
            "compression_frac_of_signed": comp/(comp+expa) if comp+expa else None,
            "mean_abs_strain_compression": float(d[d.lin_strain_pct < -SIGN_TOL].abs_strain_pct.mean()) if comp else None,
            "mean_abs_strain_expansion": float(d[d.lin_strain_pct > SIGN_TOL].abs_strain_pct.mean()) if expa else None}

signs = {"pilot25_TRAIN": sign_table(P), "combined227_TRAIN": sign_table(K)}

# Al3Ni TRAIN compression configs in combined227, listed - the question is
# whether cfg107-like compression is represented at all.
al3ni_k = K[K.phase == "Al3Ni"].sort_values("lin_strain_pct")
al3ni_k.to_csv(os.path.join(OUT, "dilution_al3ni_train_strain.csv"), index=False)

# --------------------------------------------------------- cfg107 context
cfg107 = [a for a in atoms227 if "cfg107" in a.info["config_id"]]
c107 = None
if cfg107:
    a = cfg107[0]
    c107 = {"config_id": a.info["config_id"], "phase": a.info["phase"],
            "config_type": a.info["config_type"],
            "family": C.family(a.info["config_type"]),
            "split": split227[a.info["config_id"]],
            "lin_strain_pct": lin_strain_pct(a)}

res = {"strain_metric": "(V/V0)^(1/3)-1, signed, percent; matches results/distortion/error_vs_strain.csv to 2e-14",
       "reference_volume_source": "combined227 relaxed configs",
       "max_pilot_vs_227_relaxed_volume_mismatch_A3_per_atom": max_ref_mismatch,
       "histogram": H.to_dict("records"),
       "above_2pct": above,
       "al3ni_by_sign": signs,
       "cfg107": c107}
json.dump(res, open(os.path.join(OUT, "dilution_hypothesis.json"), "w"), indent=2)

pd.set_option("display.width", 200)
print("reference-volume mismatch pilot vs combined227 relaxed (A^3/atom):",
      f"{max_ref_mismatch:.3e}")
print("\n=== |linear strain| histogram, TRAIN sets ===")
print(H.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
print("\n=== fraction above 2% strain ===")
print(json.dumps(above, indent=2))
print("\n=== Al3Ni TRAIN by strain sign ===")
print(json.dumps(signs, indent=2))
print("\n=== cfg107 ===")
print(json.dumps(c107, indent=2))
print("\n=== combined227 Al3Ni TRAIN, all configs by strain ===")
print(al3ni_k[["config_id","family","lin_strain_pct"]].to_string(index=False,
      float_format=lambda x: f"{x:+.4f}"))

# ======================================================================
# Part 2: does the pilot25-beats-combined227 pattern track strain SIGN,
# or strain MAGNITUDE?
#
# Uses results/benchmark_per_structure.csv - already-computed Phase 3
# evaluations. No model is run here.
# ======================================================================
B = pd.read_csv(os.path.join(OUT, "benchmark_per_structure.csv"))
strain = {a.info["config_id"]: lin_strain_pct(a) for a in atoms227}
B["lin_strain_pct"] = B.config_id.map(strain)
B["abs_strain_pct"] = B.lin_strain_pct.abs()
B["sign"] = np.where(B.lin_strain_pct < -SIGN_TOL, "compression",
            np.where(B.lin_strain_pct > SIGN_TOL, "expansion", "neutral"))

piv = B.pivot_table(index=["config_id","phase","family","split","lin_strain_pct",
                          "abs_strain_pct","sign"],
                    columns="model", values="abs_E_rel_err_meV_atom").reset_index()
piv["ratio_227_over_pilot"] = piv["combined227"] / piv["pilot25"]
piv["pilot_wins"] = piv["combined227"] > piv["pilot25"]

# RESERVED-20 is the only set neither model trained on NOR selected on.
# VALIDATION-18 contains pilot25's own early-stopping configs, so it is
# reported but must not carry the argument.
CLEAN = piv[piv.split == "RESERVED"]
VAL = piv[piv.split == "VALIDATION"]

def winsplit(df, label):
    hi = df[df.abs_strain_pct > 2.0 + TOL]
    lo = df[df.abs_strain_pct <= 2.0 + TOL]
    return {"set": label, "n": len(df),
            "n_pilot_wins": int(df.pilot_wins.sum()),
            "n_high_strain_gt2pct": len(hi),
            "n_pilot_wins_high_strain": int(hi.pilot_wins.sum()),
            "n_low_strain": len(lo),
            "n_pilot_wins_low_strain": int(lo.pilot_wins.sum()),
            "mean_ratio_227_over_pilot_high": float(hi.ratio_227_over_pilot.mean()) if len(hi) else None,
            "mean_ratio_227_over_pilot_low": float(lo.ratio_227_over_pilot.mean()) if len(lo) else None}

wins = [winsplit(CLEAN, "RESERVED-20 (clean held-out for both)"),
        winsplit(VAL, "VALIDATION-18 (contaminated: 5 configs are pilot25's val set)")]

# by sign, restricted to the high-|strain| configs where pilot25 ever wins
def bysign(df, label):
    out = []
    for s in ["compression", "expansion", "neutral"]:
        d = df[df.sign == s]
        if not len(d):
            continue
        out.append({"set": label, "sign": s, "n": len(d),
                    "n_pilot_wins": int(d.pilot_wins.sum()),
                    "median_ratio_227_over_pilot": float(d.ratio_227_over_pilot.median())})
    return out

signwins = bysign(CLEAN, "RESERVED-20") + bysign(VAL, "VALIDATION-18")

# nearest same-phase TRAIN neighbour in strain space, for the two contested configs
trainK = K.copy()
def neighbours(cid):
    a = [x for x in atoms227 if x.info["config_id"] == cid][0]
    s = lin_strain_pct(a); ph = a.info["phase"]; fam = C.family(a.info["config_type"])
    def near(df, samefam):
        d = df[(df.phase == ph)]
        if samefam:
            d = d[d.family == fam]
        if not len(d):
            return None
        i = (d.lin_strain_pct - s).abs().idxmin()
        return {"config_id": d.loc[i,"config_id"], "strain": float(d.loc[i,"lin_strain_pct"]),
                "gap_pct_points": float(abs(d.loc[i,"lin_strain_pct"] - s))}
    return {"config_id": cid, "strain_pct": s, "phase": ph, "family": fam,
            "combined227_TRAIN_nearest_same_phase": near(trainK, False),
            "combined227_TRAIN_nearest_same_phase_and_family": near(trainK, True),
            "pilot25_TRAIN_nearest_same_phase": near(P, False),
            "combined227_TRAIN_max_abs_strain_same_phase": float(trainK[trainK.phase==ph].abs_strain_pct.max()),
            "pilot25_TRAIN_max_abs_strain_same_phase": float(P[P.phase==ph].abs_strain_pct.max())}

nb = {c: neighbours(c) for c in ["cfg107_Al3Ni_volume_rattle_compression",
                                 "cfg115_Al3Ni_iso_expansion"]}

res["win_analysis"] = wins
res["win_by_sign"] = signwins
res["contested_config_neighbourhoods"] = nb
res["val18_and_reserved20_per_config"] = piv[
    piv.split.isin(["VALIDATION","RESERVED"])].sort_values("abs_strain_pct").to_dict("records")
json.dump(res, open(os.path.join(OUT, "dilution_hypothesis.json"), "w"), indent=2, default=float)
piv.to_csv(os.path.join(OUT, "dilution_error_vs_strain_by_model.csv"), index=False)

print("\n\n=== pilot25 vs combined227 wins, by strain magnitude ===")
print(pd.DataFrame(wins).to_string(index=False))
print("\n=== by strain sign ===")
print(pd.DataFrame(signwins).to_string(index=False))
print("\n=== contested configs: training neighbourhood ===")
print(json.dumps(nb, indent=2, default=float))
print("\n=== held-out configs sorted by |strain| (RESERVED + VALIDATION) ===")
show = piv[piv.split.isin(["VALIDATION","RESERVED"])].sort_values("abs_strain_pct",
        ascending=False)[["config_id","split","sign","lin_strain_pct","pilot25",
        "combined227","ratio_227_over_pilot"]]
print(show.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

# ======================================================================
# Part 3: the decisive test.
#
# A dilution mechanism predicts that combined-227 does badly at -4% Al3Ni
# compression BECAUSE that region is under-represented in its TRAIN set.
# If that is the cause, the error must be much smaller on a -4% config the
# model actually trained on than on the held-out one at the same strain.
#
# cfg101_Al3Ni_iso_compression         is TRAIN, strain -4.000%
# cfg107_Al3Ni_volume_rattle_compression is VALIDATION, strain -4.000%
#
# Same phase, same strain, one trained on and one not.
# ======================================================================
PAIRS = [("cfg101_Al3Ni_iso_compression", "cfg107_Al3Ni_volume_rattle_compression")]
Bc = B[B.model == "combined227"].set_index("config_id")
decisive = []
for tr_id, ho_id in PAIRS:
    decisive.append({
        "trained_on": tr_id, "trained_on_split": Bc.loc[tr_id, "split"],
        "trained_on_strain_pct": strain[tr_id],
        "trained_on_abs_err": float(Bc.loc[tr_id, "abs_E_rel_err_meV_atom"]),
        "held_out": ho_id, "held_out_split": Bc.loc[ho_id, "split"],
        "held_out_strain_pct": strain[ho_id],
        "held_out_abs_err": float(Bc.loc[ho_id, "abs_E_rel_err_meV_atom"]),
    })
    decisive[-1]["ratio_heldout_over_trained"] = (
        decisive[-1]["held_out_abs_err"] / decisive[-1]["trained_on_abs_err"])

# How much of combined227's OWN Al3Ni TRAIN set does it fail to fit?
own = B[(B.model == "combined227") & (B.split == "TRAIN") & (B.phase == "Al3Ni")].copy()
own["strain"] = own.config_id.map(strain)
BAR = C.THRESHOLDS["locked_acceptance_bar_meV_atom"]
self_fit = {"n_Al3Ni_TRAIN": len(own),
            "n_exceeding_locked_bar": int((own.abs_E_rel_err_meV_atom > BAR).sum()),
            "bar_meV_atom": BAR,
            "worst": own.nlargest(3, "abs_E_rel_err_meV_atom")[
                ["config_id","strain","abs_E_rel_err_meV_atom"]].to_dict("records")}

res["decisive_train_vs_heldout_at_same_strain"] = decisive
res["combined227_self_fit_Al3Ni"] = self_fit
res["train_phase_composition"] = {
    "pilot25_TRAIN": P.phase.value_counts().to_dict(),
    "combined227_TRAIN": K.phase.value_counts().to_dict(),
    "Al3Ni_share_pilot25": float((P.phase == "Al3Ni").mean()),
    "Al3Ni_share_combined227": float((K.phase == "Al3Ni").mean())}
json.dump(res, open(os.path.join(OUT, "dilution_hypothesis.json"), "w"), indent=2, default=float)

print("\n\n=== DECISIVE TEST: same phase, same strain, trained-on vs held-out ===")
print(json.dumps(decisive, indent=2, default=float))
print("\n=== combined227 on its OWN Al3Ni TRAIN set ===")
print(json.dumps(self_fit, indent=2, default=float))
print("\n=== Al3Ni share of TRAIN ===")
print(f"  pilot25:     {(P.phase=='Al3Ni').mean()*100:.1f}%  ({(P.phase=='Al3Ni').sum()}/{len(P)})")
print(f"  combined227: {(K.phase=='Al3Ni').mean()*100:.1f}%  ({(K.phase=='Al3Ni').sum()}/{len(K)})")

# ------------------------------------------------------------------- figure
# Two distributions over ordered strain bands -> grouped bars. Plotted as
# FRACTION of each set, never raw count: n = 15 vs n = 189, so counts would
# encode set size rather than composition. Counts are printed on the bars.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

S1, S2 = "#2a78d6", "#eb6834"      # validated categorical slots 1 and 2
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e3e2df"
x = np.arange(len(LABELS)); w = 0.38
fig, ax = plt.subplots(figsize=(9.2, 4.6), dpi=170)
fig.patch.set_facecolor("#fcfcfb"); ax.set_facecolor("#fcfcfb")
b1 = ax.bar(x - w/2, H.pilot25_frac, w, color=S1, label="pilot25 TRAIN (n=15)", zorder=3)
b2 = ax.bar(x + w/2, H.combined227_frac, w, color=S2, label="combined-227 TRAIN (n=189)", zorder=3)
for bars, ns in ((b1, hp), (b2, hk)):
    for r, n in zip(bars, ns):
        if n:
            ax.text(r.get_x()+r.get_width()/2, r.get_height()+0.012, str(n),
                    ha="center", va="bottom", fontsize=8, color=INK2)
ax.set_xticks(x); ax.set_xticklabels(LABELS, fontsize=9, color=INK2)
ax.set_ylabel("fraction of the TRAIN set", fontsize=9, color=INK2)
ax.set_xlabel("|linear strain|,  (V/V\u2080)$^{1/3}$ \u2212 1", fontsize=9, color=INK2)
ax.set_title("Where the training strain actually sits\n"
             "bar labels are configuration counts", fontsize=11, color=INK, loc="left")
ax.set_ylim(0, max(max(H.pilot25_frac), max(H.combined227_frac))*1.18)
ax.yaxis.grid(True, color=GRID, lw=0.8, zorder=0); ax.set_axisbelow(True)
for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
ax.spines["bottom"].set_color(GRID)
ax.tick_params(length=0, colors=INK2)
ax.legend(frameon=False, fontsize=9, labelcolor=INK2, loc="upper right")
ax.annotate("pilot25's 10 iso configs are nominally ±2.000%; they land at\n"
            "2.0000062% and fall in this band by floating-point dust, not by design",
            xy=(4 - w/2, H.pilot25_frac[4]), xytext=(0.42, 0.545),
            fontsize=8, color=INK2, ha="left",
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8,
                            shrinkA=0, shrinkB=3))
fig.text(0.012, 0.012,
         "Volumetric metric: shear and pure-rattle configurations are exactly 0 by "
         "construction and all fall in the first band.",
         fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.035, 1, 1))
fig.savefig(os.path.join(OUT, "dilution_strain_histogram.png"),
            facecolor=fig.get_facecolor())
print("\nwrote results/dilution_strain_histogram.png")
