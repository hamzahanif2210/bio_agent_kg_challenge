"""Maintenance mode: bring the graph up to date when Pharos changes (a new release, corrected records).

  python -m bioagent.ingest.update data/processed/pharos_evidence data/processed/pharos_updated --targets EGFR TP53
  python -m bioagent.ingest.update data/processed/pharos_evidence data/processed/pharos_updated --sample 200

Re-fetches the chosen targets live (cache bypassed), rebuilds their edges, and compares with the edges the graph already has
for them. Writes the updated graph plus PREFIX.delta.json (what was added, removed or re-scored, per edge type). New edges
are then pruned with the same rules as the rest of the graph; new weak disease edges are flagged so the PubMed tier
(scripts/pubmed_counts.py) and the LLM judge can look at them. Edges of untouched targets are left as they are.
"""
import argparse
import json
import random

import numpy as np
import pandas as pd

from bioagent.ingest.pharos import fetch_target, to_kg

KEY = ["subject", "object", "evidence"]


def owned_by(edges, tids):
    """Edges that a target's own Pharos record produces: ligand edges point at the target, all others start at it."""
    lig = edges.evidence == "pharos:ligand_activity"
    return (~lig & edges.subject.isin(tids)) | (lig & edges.object.isin(tids))


def diff_edges(old, new, tol=0.01):
    """old/new: edge tables for the same targets. Returns (added, removed, rescored) as DataFrames."""
    o, n = old.drop_duplicates(KEY).set_index(KEY), new.drop_duplicates(KEY).set_index(KEY)
    added, removed = n.loc[n.index.difference(o.index)].reset_index(), o.loc[o.index.difference(n.index)].reset_index()
    both = o.index.intersection(n.index)
    a, b = o.loc[both, "confidence"].to_numpy(dtype=float), n.loc[both, "confidence"].to_numpy(dtype=float)
    changed = (np.isnan(a) != np.isnan(b)) | (np.abs(np.nan_to_num(a) - np.nan_to_num(b)) > tol)
    rescored = n.loc[both[changed]].reset_index().assign(old_confidence=a[changed])
    return added, removed, rescored


def apply_update(nodes, edges, fresh_nodes, fresh_edges, tids):
    """Swap the targets' own edges for the fresh ones. New edges get verdict columns later (prune_edges)."""
    old = edges[owned_by(edges, tids)]
    added, removed, rescored = diff_edges(old, fresh_edges)
    drop = old.set_index(KEY).index.isin(removed.set_index(KEY).index) if len(removed) else np.zeros(len(old), bool)
    keep = edges.drop(old.index[drop])
    if len(rescored):                          # take the new score and evidence for edges that stayed
        r = rescored.set_index(KEY)
        idx = keep.set_index(KEY).index.isin(r.index)
        k = keep.set_index(KEY)
        k.loc[idx, "confidence"] = r.loc[k.index[idx], "confidence"].to_numpy()
        k.loc[idx, "attributes"] = r.loc[k.index[idx], "attributes"].to_numpy()
        keep = k.reset_index()[keep.columns]
    out = pd.concat([keep, added.reindex(columns=edges.columns)], ignore_index=True)
    new_nodes = fresh_nodes[~fresh_nodes.id.isin(set(nodes.id))]
    return pd.concat([nodes, new_nodes], ignore_index=True), out, {"added": added, "removed": removed, "rescored": rescored}


def summarize(delta):
    return {k: (v.groupby("evidence").size().to_dict() if len(v) else {}) for k, v in delta.items()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("graph"); ap.add_argument("out")
    ap.add_argument("--targets", nargs="+"); ap.add_argument("--sample", type=int, help="re-check N random targets")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    nodes, edges = pd.read_parquet(f"{a.graph}.nodes.parquet"), pd.read_parquet(f"{a.graph}.edges.parquet")
    names = a.targets or [i.replace("UniProtKB:", "") for i in random.Random(a.seed).sample(
        sorted(set(edges.subject[edges.evidence == "pharos:go"])), a.sample)]
    fresh = [t for t in (fetch_target(x, refresh=True) for x in names) if t]
    tids = {f"UniProtKB:{t['uniprot']}" for t in fresh}
    fn, fe = to_kg(fresh)
    n2, e2, delta = apply_update(nodes, edges, fn, fe, tids)
    n2.to_parquet(f"{a.out}.nodes.parquet"); e2.to_parquet(f"{a.out}.edges.parquet")
    rep = {"targets_checked": len(fresh), "summary": summarize(delta),
           "examples": {k: v.head(5)[KEY].to_dict("records") for k, v in delta.items()}}
    json.dump(rep, open(f"{a.out}.delta.json", "w"), indent=1, default=str)
    print(json.dumps(rep["summary"], indent=1))
