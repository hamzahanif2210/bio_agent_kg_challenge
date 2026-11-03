"""Mean +/- s.d. over seeds of test hard-negative (degree) AUROC for every ablation config x target. Plain GraphSAGE baselines come from the earlier runs."""
import glob, json, re, sys
import numpy as np, pandas as pd

rows = []
for f in glob.glob("runs/ft_*_s*.json"):
    m = re.match(r"runs/ft_(.+)_(ppi|disease|go|ligand)_s(\d)\.json", f)
    try: d = json.load(open(f))
    except Exception: continue
    rows.append((m.group(1), m.group(2), int(m.group(3)), d["test_degree_auroc"], d.get("context_edges"), d.get("context_leaked_dropped")))
for tag, name in (("pharos", "plain Pharos (baseline)"), ("prunedv3", "pruned (no features)")):
    for f in glob.glob(f"runs/{tag}_*_s*.json"):
        m = re.match(rf"runs/{tag}_(ppi|disease|go|ligand)_s(\d)\.json", f)
        if m:
            try: rows.append((name, m.group(1), int(m.group(2)), json.load(open(f))["test_degree_auroc"], None, None))
            except Exception: pass
df = pd.DataFrame(rows, columns=["config", "target", "seed", "auroc", "ctx", "leak"])
g = df.groupby(["config", "target"]).auroc.agg(["mean", "std", "count"]).reset_index()
g["cell"] = g.apply(lambda r: f"{r['mean']:.3f}±{(0 if np.isnan(r['std']) else r['std']):.3f} (n={r['count']})", axis=1)
t = g.pivot(index="config", columns="target", values="cell")
order = ["plain Pharos (baseline)", "pruned (no features)"] + sorted(c for c in t.index if not c.startswith(("plain Pharos", "pruned (no")))
print(t.reindex(order).to_string())
lk = df.dropna(subset=["leak"]).groupby("config").agg(ctx=("ctx", "mean"), leaked=("leak", "mean"))
print("\ncontext edges kept / leaked pairs dropped (mean per run)"); print(lk.round(0).to_string())
