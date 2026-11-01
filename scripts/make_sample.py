"""Small sample of the final graph for the repo, so the quick-start works without our data.
Seeds: a few well-known targets; keeps each seed's best-supported neighbours per class (kept AND pruned edges, so verdicts
and reasons are visible) and every edge among the chosen nodes.   python scripts/make_sample.py
"""
import pandas as pd

SEEDS = ["EGFR", "BRCA1", "TP53", "KRAS", "ERBB2", "BRCA2", "MET", "PIK3CA", "BARD1", "RAD51"]
PER_CLASS = 25
g = "data/processed/pharos_pruned_v3.whole"
nodes = pd.read_parquet(f"{g}.nodes.parquet")
e = pd.read_parquet(f"{g}.edges.parquet")
name, cat = dict(zip(nodes.id, nodes.name)), dict(zip(nodes.id, nodes.category))
seed_ids = [i for i in nodes.id[nodes.name.isin(SEEDS) & (nodes.category == "biolink:Protein")]]
print("seeds found:", sorted(name[i] for i in seed_ids))
chosen = set(seed_ids)
for s in seed_ids:
    near = e[(e.subject == s) | (e.object == s)].copy()
    near["other"] = near.object.where(near.subject == s, near.subject)
    near["cls"] = near.other.map(cat)
    near = near.sort_values("verdict_confidence", ascending=False).drop_duplicates("other")
    for _, grp in near.groupby("cls"):
        chosen |= set(grp.head(PER_CLASS).other)
sub = e[e.subject.isin(chosen) & e.object.isin(chosen)]
n = nodes[nodes.id.isin(set(sub.subject) | set(sub.object))]
n.to_parquet("sample/sample.whole.nodes.parquet"); sub.to_parquet("sample/sample.whole.edges.parquet")
k = sub[sub.verdict == "keep"]; kn = n[n.id.isin(set(k.subject) | set(k.object))]
kn.to_parquet("sample/sample.pruned.nodes.parquet"); k.to_parquet("sample/sample.pruned.edges.parquet")
print(len(n), "nodes,", len(sub), "edges;", int((sub.verdict == 'prune').sum()), "pruned")
