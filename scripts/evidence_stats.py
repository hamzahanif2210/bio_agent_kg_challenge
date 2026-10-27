"""Coverage of per-edge evidence in a graph. Usage: python scripts/evidence_stats.py PREFIX"""
import json, sys
import pandas as pd
from bioagent.schema.kg import read_kg
n, e = read_kg(sys.argv[1])
e["has_conf"] = e.confidence.notna()
print(e.groupby("evidence").agg(edges=("subject", "size"), with_score=("has_conf", "mean"),
      mean=("confidence", "mean"), p10=("confidence", lambda x: x.quantile(.1)), p90=("confidence", lambda x: x.quantile(.9))).round(3).sort_values("edges", ascending=False))
d = e[e.evidence == "pharos:disease_association"]
a = pd.DataFrame([json.loads(x) for x in d.attributes])
print("\ndisease edges: supporting-record count (n_assoc) quantiles:\n", a.n_assoc.describe().round(1).to_string())
print("share with 1 supporting database type:", round((a.assoc_types.map(lambda t: len(t) if t else 0) == 1).mean(), 3))
print("distinct database types:", sorted({t for ts in a.assoc_types.dropna() for t in ts}))
