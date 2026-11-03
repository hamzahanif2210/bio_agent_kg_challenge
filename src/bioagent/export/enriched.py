"""The enriched graph: kept (pruned) Pharos edges + context edges from public KGs + node features, as KGX and PyTorch Geometric.

  python -m bioagent.export.enriched data/processed/pharos_pruned_v3.pruned data/context/context data/features exports/enriched

Context sets (pathways, phenotypes, subcellular locations, tissue expression) are listed in scripts/build_context.py; each context edge keeps
its `evidence` ("context:pathway", ...) so it can be filtered out. Node features are stored as data[type].x_text (64) and x_seq (420, proteins).
No held-out test edges are removed here: when you evaluate link prediction, split first and then drop context pairs equal to a held-out pair
(bioagent.eval.split.leaked does this).
"""
import os
import sys

import numpy as np
import pandas as pd

from bioagent.export.formats import to_kgx, to_pyg
from bioagent.standards.biolink import specialise

if __name__ == "__main__":
    graph, ctx, feat_dir, out = sys.argv[1:5]
    nodes, edges = pd.read_parquet(f"{graph}.nodes.parquet"), pd.read_parquet(f"{graph}.edges.parquet")
    edges = specialise(nodes, edges).reset_index(drop=True)
    ce, cn = pd.read_parquet(f"{ctx}.edges.parquet"), pd.read_parquet(f"{ctx}.nodes.parquet")
    ce = ce[ce.subject.isin(set(nodes.id))].assign(source="context", confidence=np.nan, verdict="keep", verdict_confidence=np.nan, rule="context",
                                                   reason="context edge from a public KG (Open Targets / OptimusKG), not a Pharos relation", needs_review=False)
    cn = cn[cn.id.isin(set(ce.object))].assign(source="context")
    nodes = pd.concat([nodes, cn[~cn.id.isin(set(nodes.id))]], ignore_index=True)
    edges = pd.concat([edges, ce], ignore_index=True)
    feats = {k: (np.load(f"{feat_dir}/{k}.npz", allow_pickle=True)["ids"], np.load(f"{feat_dir}/{k}.npz", allow_pickle=True)["X"].astype(np.float32))
             for k in ("text", "seq")}
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    to_kgx(nodes, edges, f"{out}.kgx")
    print(to_pyg(nodes, edges, f"{out}.pyg.pt", feats))
