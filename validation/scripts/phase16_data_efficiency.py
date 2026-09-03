"""Phase 16: data-efficiency curve - N_DFT vs error on a FIXED evaluation set.

Every checkpoint is evaluated on identical structures. The evaluation set is the
reserved-20 (Dataset-100 TEST(5)+BLIND_HOLDOUT(15)), verified held out from the
TRAIN and VALIDATION splits of every generation. The headline curve uses
reserved-19 (cfg043 excluded as design-contaminated, per the project's own
threshold discipline); reserved-20 and VALIDATION-18 are reported alongside.

Prior claim under test: validation energy RMSE plateaued (~1.7/1.7/1.9) while
force and stress kept improving.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, common as C
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

GPA = 160.21766208
CKPT = [(25,  "pilot25_matpes_pbe_lora_v1",   15),
        (100, "dataset100_matpes_pbe_lora_v1", 65),
        (113, "al3ni_combined113_lora_v1",     75),
        (127, "al3ni_combined127_lora_v1",     89),
        (129, "al3ni_combined129_lora_v1",     91),
        (211, "al3ni_combined211_lora_v1",    173),
        (218, "al3ni_combined218_lora_v1",    180),
        (220, "al3ni_combined220_lora_v1",    182),
        (227, "al3ni_combined227_lora_v1",    189)]
EXCL = {"cfg043_Al3Ni_volume_rattle_expansion"}

atoms, split = C.load_dataset("combined227")
ref_id = {a.info["phase"]: a.info["config_id"] for a in atoms if a.info["config_type"] == "relaxed"}
byid = {a.info["config_id"]: a for a in atoms}
RES = [a for a in atoms if split[a.info["config_id"]] == "RESERVED"]
VAL = [a for a in atoms if split[a.info["config_id"]] == "VALIDATION"]
need = {a.info["config_id"]: a for a in RES + VAL}
for ph, r in ref_id.items(): need[r] = byid[r]

rows = []
for N, name, ntr in CKPT:
    calc = C.calc(C.model_path(name))
    P = {}
    for cid, a in need.items():
        w = a.copy(); w.calc = calc
        P[cid] = (w.get_potential_energy(), w.get_forces(), w.get_stress(voigt=True))
    def metrics(group, label):
        ee, ff, ss = [], [], []
        for a in group:
            cid = a.info["config_id"]; r = ref_id[a.info["phase"]]; n = len(a)
            ed = (a.get_potential_energy() - byid[r].get_potential_energy())/n*1000
            ep = (P[cid][0] - P[r][0])/n*1000
            ee.append(ep-ed)
            ff.append(np.abs(P[cid][1]-a.get_forces()).mean())
            ss.append(np.abs((P[cid][2]-a.get_stress(voigt=True))*GPA).mean())
        ee = np.array(ee)
        return {f"{label}_E_MAE": np.abs(ee).mean(), f"{label}_E_RMSE": np.sqrt((ee**2).mean()),
                f"{label}_E_MAX": np.abs(ee).max(),
                f"{label}_F_MAE": float(np.mean(ff)), f"{label}_S_MAE": float(np.mean(ss))}
    r = {"N_DFT": N, "model": name, "n_train": ntr}
    r.update(metrics([a for a in RES if a.info["config_id"] not in EXCL], "res19"))
    r.update(metrics(RES, "res20"))
    r.update(metrics(VAL, "val18"))
    rows.append(r)
    print(f"  N={N:4d} res19 E_MAE={r['res19_E_MAE']:6.3f} E_RMSE={r['res19_E_RMSE']:6.3f} "
          f"E_MAX={r['res19_E_MAX']:6.3f} F_MAE={r['res19_F_MAE']:.5f} S_MAE={r['res19_S_MAE']:.4f}"
          f" | val18 E_RMSE={r['val18_E_RMSE']:6.3f}", flush=True)

df = pd.DataFrame(rows)
df.to_csv(os.path.join(C.RESULTS, "data_efficiency.csv"), index=False)

fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.3))
specs = [("res19_E_RMSE", "relative-energy RMSE (meV/atom)", "Energy"),
         ("res19_F_MAE", "force MAE (eV/$\AA$)", "Forces"),
         ("res19_S_MAE", "stress MAE (GPa)", "Stress")]
for ax, (col, ylab, title) in zip(axes, specs):
    ax.plot(df.N_DFT, df[col], color="#1baf7a", lw=2, marker="o", ms=7,
            markerfacecolor="#1baf7a", markeredgecolor="#fcfcfb", mew=1.4, zorder=3)
    for _, r in df.iterrows():
        if r.N_DFT in (25, 100, 227):
            ax.annotate(f"{r[col]:.3g}", (r.N_DFT, r[col]), textcoords="offset points",
                        xytext=(6, 7), fontsize=8, color="#52514e")
    ax.set_xlabel("$N_{DFT}$ (total labelled configurations)")
    ax.set_ylabel(ylab); ax.set_title(title, loc="left", fontsize=11)
    ax.set_xscale("log"); ax.set_yscale("log")
    for s in ("top","right"): ax.spines[s].set_visible(False)
    ax.grid(True, which="both", lw=0.4, color="#e4e4de"); ax.set_axisbelow(True)
fig.suptitle("Phase 16: data-efficiency of LoRA fine-tuning for Ni-Al, fixed reserved-19 evaluation set",
             x=0.005, ha="left", fontsize=12)
fig.tight_layout(rect=[0,0,1,0.92])
fig.savefig(os.path.join(C.RESULTS, "data_efficiency_curve.png"), dpi=150)
pd.set_option("display.width", 250)
print("\n=== FIXED reserved-19 EVALUATION SET ===")
print(df[["N_DFT","n_train","res19_E_MAE","res19_E_RMSE","res19_E_MAX","res19_F_MAE","res19_S_MAE"]]
      .to_string(index=False, float_format=lambda v: f"{v:9.4f}"))
print("\n=== VALIDATION-18 (the set the plateau claim was made on) ===")
print(df[["N_DFT","val18_E_MAE","val18_E_RMSE","val18_F_MAE","val18_S_MAE"]]
      .to_string(index=False, float_format=lambda v: f"{v:9.4f}"))
