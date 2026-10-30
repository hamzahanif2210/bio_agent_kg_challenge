"""Export a graph (nodes + edges with verdict columns) as KGX TSV and as a PyTorch Geometric HeteroData file.

  python -m bioagent.export.formats data/processed/pharos_pruned_v3.whole  exports/whole
  python -m bioagent.export.formats data/processed/pharos_pruned_v3.pruned exports/pruned

Writes OUT.kgx/{nodes,edges}.tsv and OUT.pyg.pt. Predicates are specialised first (bioagent.standards.biolink).
Load the PyG file with:  data = torch.load("OUT.pyg.pt", weights_only=False)["data"]
  data["Protein", "associated_with", "Disease"].edge_index / .edge_attr   (see EDGE_ATTR)
  torch.load(...)["node_ids"]["Protein"][i] is the CURIE of node i of that type.
"""
import os
import sys

import numpy as np
import pandas as pd

from bioagent.standards.biolink import specialise

EDGE_ATTR = ["source_score", "has_source_score", "verdict_confidence", "kept", "needs_review"]
KGX_EXTRA = ["evidence", "confidence", "verdict", "verdict_confidence", "reason", "rule", "needs_review",
             "pubmed_count", "judge_model", "judge_p_real", "original_predicate", "timestamp", "method", "attributes"]


def to_kgx(nodes, edges, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    n = pd.DataFrame({"id": nodes.id, "category": nodes.category, "name": nodes.name, "provided_by": "infores:" + nodes.source})
    n.to_csv(f"{out_dir}/nodes.tsv", sep="\t", index=False)
    e = pd.DataFrame({"id": [f"edge-{i}" for i in range(len(edges))], "subject": edges.subject.to_numpy(),
                      "predicate": edges.predicate.to_numpy(), "object": edges.object.to_numpy(),
                      "primary_knowledge_source": "infores:" + edges.source.to_numpy(),
                      "knowledge_level": "not_provided", "agent_type": "not_provided"})
    for c in KGX_EXTRA:
        if c in edges.columns:
            e[c] = edges[c].to_numpy()
    e.to_csv(f"{out_dir}/edges.tsv", sep="\t", index=False)


def _short(curie):
    return curie.split(":", 1)[1]


def to_pyg(nodes, edges, path):
    import torch
    from torch_geometric.data import HeteroData
    ntype = dict(zip(nodes.id, nodes.category.map(_short)))
    data, node_ids, index = HeteroData(), {}, {}
    for t, g in nodes.groupby(nodes.category.map(_short)):
        node_ids[t] = g.id.tolist()
        index[t] = {i: k for k, i in enumerate(node_ids[t])}
        data[t].num_nodes = len(g)
    kept = (edges.verdict == "keep").to_numpy() if "verdict" in edges.columns else np.ones(len(edges), bool)
    attr = np.stack([np.nan_to_num(edges.confidence.to_numpy(dtype=float), nan=0.0),
                     edges.confidence.notna().to_numpy(dtype=float),
                     edges.verdict_confidence.to_numpy(dtype=float) if "verdict_confidence" in edges.columns else np.full(len(edges), np.nan),
                     kept.astype(float),
                     edges.needs_review.to_numpy(dtype=float) if "needs_review" in edges.columns else np.zeros(len(edges))], axis=1).astype(np.float32)
    st, ot = edges.subject.map(ntype), edges.object.map(ntype)
    pred = edges.predicate.map(_short)
    for (s, p, o), g in edges.assign(_s=st, _o=ot, _p=pred).groupby(["_s", "_p", "_o"]):
        src = np.array([index[s][x] for x in g.subject])
        dst = np.array([index[o][x] for x in g.object])
        et = (s, p, o)
        data[et].edge_index = torch.tensor(np.stack([src, dst]), dtype=torch.long)
        data[et].edge_attr = torch.from_numpy(attr[edges.index.get_indexer(g.index)])
    torch.save({"data": data, "node_ids": node_ids, "edge_attr_columns": EDGE_ATTR}, path)
    return data


if __name__ == "__main__":
    graph, out = sys.argv[1:3]
    nodes, edges = pd.read_parquet(f"{graph}.nodes.parquet"), pd.read_parquet(f"{graph}.edges.parquet")
    edges = specialise(nodes, edges).reset_index(drop=True)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    to_kgx(nodes, edges, f"{out}.kgx")
    d = to_pyg(nodes, edges, f"{out}.pyg.pt")
    print(d)
    print(edges.predicate.value_counts().to_string())
