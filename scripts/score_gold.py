"""Score our keep/prune verdicts against a labelled edge list, per rule. Use when a gold set (ours or the organizers') exists.

  python scripts/score_gold.py LABELS.tsv [--graph data/processed/pharos_pruned_v3.whole] [--out runs/gold_scores.json]

LABELS.tsv columns: subject, predicate (optional), object, label  (label: keep/true/1 = a real edge; prune/false/0 = not real).
Edges are matched on (subject, object) in either order; predicate is used only if present in both. Reports counts of matched edges, accuracy,
precision and recall of "keep", and the same per rule so weak rules can be found.
"""
import argparse, json
import pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument("labels")
ap.add_argument("--graph", default="data/processed/pharos_pruned_v3.whole"); ap.add_argument("--out", default="runs/gold_scores.json")
a = ap.parse_args()
POS = {"keep", "true", "1", "yes", "real", "positive"}
lab = pd.read_csv(a.labels, sep=None, engine="python", dtype=str)
lab["truth"] = lab["label"].str.strip().str.lower().isin(POS)
key = lambda s, o: [tuple(sorted(t)) for t in zip(s, o)]
lab["k"] = key(lab.subject, lab.object)
lab = lab.drop_duplicates("k")
cols = ["subject", "object", "rule", "verdict"] + (["predicate"] if "predicate" in lab.columns else [])
e = pd.read_parquet(f"{a.graph}.edges.parquet", columns=cols)
e["k"] = key(e.subject, e.object)
m = e.merge(lab[["k", "truth"] + (["predicate"] if "predicate" in lab.columns else [])], on="k", suffixes=("", "_gold"))
if "predicate" in lab.columns: m = m[m.predicate == m.predicate_gold]
m["pred"] = m.verdict == "keep"
def stats(d):
    tp = int((d.pred & d.truth).sum()); fp = int((d.pred & ~d.truth).sum()); fn = int((~d.pred & d.truth).sum()); tn = int((~d.pred & ~d.truth).sum())
    n = len(d)
    return dict(n=n, accuracy=round((tp + tn) / n, 4) if n else None, precision=round(tp / (tp + fp), 4) if tp + fp else None,
                recall=round(tp / (tp + fn), 4) if tp + fn else None, tp=tp, fp=fp, fn=fn, tn=tn)
res = {"labelled": len(lab), "matched": len(m), "overall": stats(m), "by_rule": {r: stats(d) for r, d in m.groupby("rule")}}
json.dump(res, open(a.out, "w"), indent=1); print(json.dumps(res["overall"], indent=1), f"matched {len(m)} of {len(lab)}")
