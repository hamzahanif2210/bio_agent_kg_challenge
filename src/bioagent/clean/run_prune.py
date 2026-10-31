"""Apply the v1 pruning rules to a Pharos graph and write both graphs.

  python -m bioagent.clean.run_prune data/processed/pharos_evidence /scratch/hamza95/bio_kg_data data/processed/pharos_pruned [CRAPOME_TSV]

Outputs (PREFIX = last argument):
  PREFIX.whole.{nodes,edges}.parquet   every edge with verdict columns
  PREFIX.pruned.{nodes,edges}.parquet  only kept edges (nodes limited to those still connected)
  PREFIX.summary.json                  counts per rule
"""
import json
import sys

import pandas as pd

from bioagent.clean.prune import load_resources, prune_edges, remap_obsolete
from bioagent.schema.kg import read_kg

def new_term_nodes(term_ids, nodes, src):
    """Nodes for replacement terms that are not in the graph yet (name and class from the GO / MONDO files)."""
    from bioagent.enrich.ontology import parse_info
    missing = sorted(set(term_ids) - set(nodes.id))
    if not missing:
        return pd.DataFrame(columns=nodes.columns)
    info = {**parse_info(f"{src}/go/go-basic.obo", "GO:"), **parse_info(f"{src}/mondo/mondo.obo", "MONDO:")}
    cls = {"molecular_function": "biolink:MolecularActivity", "biological_process": "biolink:BiologicalProcess",
           "cellular_component": "biolink:CellularComponent"}
    return pd.DataFrame({"id": missing, "category": [("biolink:Disease" if i.startswith("MONDO:") else cls.get(info.get(i, ("", ""))[1], "biolink:BiologicalProcess")) for i in missing],
                         "name": [info.get(i, (i, ""))[0] for i in missing], "source": ["mondo" if i.startswith("MONDO:") else "go" for i in missing]})


if __name__ == "__main__":
    graph, src, out = sys.argv[1:4]
    crapome = sys.argv[4] if len(sys.argv) > 4 else None
    nodes, edges = read_kg(graph)
    print("loading resources...", flush=True)
    res = load_resources(src, crapome)
    edges = remap_obsolete(edges, res)
    moved = edges.original_object.notna()
    print(f"remapped {int(moved.sum())} edges from obsolete terms to their replacements", flush=True)
    nodes = pd.concat([nodes, new_term_nodes(edges[moved].object, nodes, src)], ignore_index=True)
    print("pruning", len(edges), "edges...", flush=True)
    v = prune_edges(edges, res)
    v.loc[moved.to_numpy(), "reason"] = ("term remapped from obsolete " + edges.original_object[moved] + "; ") + v.reason[moved.to_numpy()]
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
