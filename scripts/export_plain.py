"""Plain edge-list exports for evaluators with a different format.

  python scripts/export_plain.py [--graph data/processed/pharos_pruned_v3.whole] [--out exports]

Writes OUT/edges_kept.csv (pruned edges removed) and OUT/edges_all.csv (every edge with a `kept` 0/1 column). Columns: subject,
predicate, object, verdict, rule, verdict_confidence. No node features and no context edges.
"""
import argparse, os
import pandas as pd
from bioagent.standards.biolink import specialise

ap = argparse.ArgumentParser(); ap.add_argument("--graph", default="data/processed/pharos_pruned_v3.whole"); ap.add_argument("--out", default="exports")
a = ap.parse_args()
e = pd.read_parquet(f"{a.graph}.edges.parquet")
nodes = pd.read_parquet(f"{a.graph}.nodes.parquet")
e = specialise(nodes, e)
c = ["subject", "predicate", "object", "verdict", "rule", "verdict_confidence"]
e = e[[x for x in c if x in e.columns]].copy(); e["kept"] = (e.verdict == "keep").astype(int)
os.makedirs(a.out, exist_ok=True)
e.to_csv(f"{a.out}/edges_all.csv", index=False); e[e.kept == 1].to_csv(f"{a.out}/edges_kept.csv", index=False)
print(len(e), int(e.kept.sum()))
