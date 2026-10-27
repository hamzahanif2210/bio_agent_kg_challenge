"""Apply the v1 pruning rules to a Pharos graph and write both graphs.

  python -m bioagent.clean.run_prune data/processed/pharos_evidence /scratch/hamza95/bio_kg_data data/processed/pharos_pruned

Outputs (PREFIX = last argument):
  PREFIX.whole.{nodes,edges}.parquet   every edge with verdict columns
  PREFIX.pruned.{nodes,edges}.parquet  only kept edges (nodes limited to those still connected)
  PREFIX.summary.json                  counts per rule
"""
import json
import sys

from bioagent.clean.prune import load_resources, prune_edges
from bioagent.schema.kg import read_kg

if __name__ == "__main__":
    graph, src, out = sys.argv[1:4]
    nodes, edges = read_kg(graph)
    print("loading resources...", flush=True)
    res = load_resources(src)
    print("pruning", len(edges), "edges...", flush=True)
    v = prune_edges(edges, res)
    whole = edges.join(v)
    kept = whole[whole.verdict == "keep"]
    used = set(kept.subject) | set(kept.object)
    nodes_kept = nodes[nodes.id.isin(used)]
    whole.to_parquet(f"{out}.whole.edges.parquet")
    nodes.to_parquet(f"{out}.whole.nodes.parquet")
    kept.to_parquet(f"{out}.pruned.edges.parquet")
    nodes_kept.to_parquet(f"{out}.pruned.nodes.parquet")
    summ = (whole.groupby(["evidence", "rule", "verdict"]).agg(edges=("subject", "size"), mean_conf=("verdict_confidence", "mean"),
            needs_review=("needs_review", "sum")).round(3).reset_index())
    print(summ.to_string(index=False))
    json.dump({"whole_edges": len(whole), "kept_edges": len(kept), "pruned_edges": len(whole) - len(kept),
               "nodes_whole": len(nodes), "nodes_pruned": len(nodes_kept),
               "needs_review": int(whole.needs_review.sum()),
               "by_rule": summ.to_dict("records")}, open(f"{out}.summary.json", "w"), indent=1)
    print(f"whole: {len(whole)} edges; kept: {len(kept)}; pruned: {len(whole)-len(kept)}")
