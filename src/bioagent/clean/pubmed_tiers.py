"""Pruning v2, tiers 1 and 2 (no LLM): re-decide the weak-evidence disease edges using PubMed co-mention counts.

  python -m bioagent.clean.pubmed_tiers data/processed/pharos_pruned data/processed/pubmed_counts.jsonl data/processed/pharos_pruned_v2

Only edges the v1 rules pruned for weak evidence (rule `disease_weak_only`) are touched:
  0 co-mentions     stay pruned, reason now cites the literature check   (rule pubmed_none)
  >= RESCUE (10)    flipped to keep                                      (rule pubmed_rescue)
  1..9              unchanged, left flagged for the LLM judge (tier 3)
  no count          unchanged (the lookup failed)
Every edge gets a `pubmed_count` column (NaN where not looked up).
"""
import json
import sys

import numpy as np
import pandas as pd

RESCUE = 10


def rescue_conf(n):
    """0.6 at 10 co-mentions rising to 0.8 at 100 or more (heuristic, like the v1 priors)."""
    return np.clip(0.6 + 0.2 * (np.log10(np.maximum(n, 1)) - 1), 0.6, 0.8).round(3)


def apply_tiers(whole, nodes, counts):
    """whole: v1 edge table with verdict columns. counts: DataFrame gene, disease, count."""
    name = dict(zip(nodes.id, nodes.name))
    cnt = {(g, d): n for g, d, n in zip(counts.gene, counts.disease, counts["count"])}
    w = whole.copy()
    w["pubmed_count"] = np.nan
    idx = w.index[w.rule == "disease_weak_only"]
    n = np.array([cnt.get((name[s], name[o]), np.nan) for s, o in zip(w.subject[idx], w.object[idx])])
    w.loc[idx, "pubmed_count"] = n
    none, resc = pd.Series(n == 0, index=idx), pd.Series(n >= RESCUE, index=idx)
    i0, i1 = idx[none.to_numpy()], idx[resc.to_numpy()]
    w.loc[i0, "reason"] = w.loc[i0, "reason"] + "; PubMed has no article mentioning both"
    w.loc[i0, "rule"] = "pubmed_none"
    w.loc[i0, "needs_review"] = False
    c = w.loc[i1, "pubmed_count"].to_numpy()
    w.loc[i1, "verdict"] = "keep"
    w.loc[i1, "verdict_confidence"] = rescue_conf(c)
    w.loc[i1, "reason"] = [f"weak database evidence, but {int(x)} PubMed articles mention both protein and disease" for x in c]
    w.loc[i1, "rule"] = "pubmed_rescue"
    w.loc[i1, "needs_review"] = False
    return w


if __name__ == "__main__":
    graph, counts_path, out = sys.argv[1:4]
    nodes = pd.read_parquet(f"{graph}.whole.nodes.parquet")
    whole = pd.read_parquet(f"{graph}.whole.edges.parquet")
    counts = pd.read_json(counts_path, lines=True).drop_duplicates(["gene", "disease"])
    w = apply_tiers(whole, nodes, counts)
    kept = w[w.verdict == "keep"]
    used = set(kept.subject) | set(kept.object)
    w.to_parquet(f"{out}.whole.edges.parquet"); nodes.to_parquet(f"{out}.whole.nodes.parquet")
    kept.to_parquet(f"{out}.pruned.edges.parquet"); nodes[nodes.id.isin(used)].to_parquet(f"{out}.pruned.nodes.parquet")
    summ = w.groupby(["evidence", "rule", "verdict"]).agg(edges=("subject", "size"), needs_review=("needs_review", "sum")).reset_index()
    print(summ.to_string(index=False))
    json.dump({"whole_edges": len(w), "kept_edges": len(kept), "pruned_edges": len(w) - len(kept),
               "by_rule": summ.to_dict("records")}, open(f"{out}.summary.json", "w"), indent=1, default=int)
    print(f"whole: {len(w)}; kept: {len(kept)}; pruned: {len(w)-len(kept)}")
