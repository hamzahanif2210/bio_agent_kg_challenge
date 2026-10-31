"""Enrichment source 1: ontology hierarchies. Adds `subclass_of` edges between GO terms (is_a, part_of) and between MONDO diseases
(is_a), for every term already in the graph and all their ancestors. No protein-level facts are added, so nothing can duplicate a
held-out protein-GO or protein-disease edge directly; the model can still infer a parent term from a child annotation, which is the
point of an ontology (the 'true path rule').

  python -m bioagent.enrich.ontology data/processed/pharos_pruned_v3.pruned /scratch/hamza95/bio_kg_data data/processed/enriched_ont
"""
import sys

import pandas as pd

from bioagent.clean.prune import parse_obo


def parse_names(path, prefix):
    names, cur = {}, None
    for line in open(path):
        line = line.strip()
        if line.startswith("id: " + prefix):
            cur = line[4:]
        elif line == "[Term]":
            cur = None
        elif cur and line.startswith("name: "):
            names[cur] = line[6:]
    return names


def parse_info(path, prefix):
    """{id: (name, namespace)} for live terms."""
    info, cur, name = {}, None, None
    for line in open(path):
        line = line.strip()
        if line.startswith("id: " + prefix):
            cur, name = line[4:], None
        elif line == "[Term]":
            cur = None
        elif cur and line.startswith("name: "):
            name = line[6:]; info[cur] = (name, info.get(cur, ("", ""))[1])
        elif cur and line.startswith("namespace: "):
            info[cur] = (info.get(cur, ("", ""))[0], line[11:])
    return info


def hierarchy_edges(nodes, obo_path, prefix, source, edge_ts):
    """New nodes and subclass_of edges for all ancestors of the graph's terms with this id prefix."""
    obsolete, parents = parse_obo(obo_path, prefix)
    names = parse_names(obo_path, prefix)
    have = set(nodes.id)
    todo, seen, rows = [i for i in have if i.startswith(prefix) and i not in obsolete], set(), []
    while todo:
        t = todo.pop()
        if t in seen:
            continue
        seen.add(t)
        for p in parents.get(t, ()):
            if p.startswith(prefix) and p not in obsolete:
                rows.append((t, p)); todo.append(p)
    cat = dict(zip(nodes.id, nodes.category))
    new_ids = sorted({x for r in rows for x in r} - have)
    ncat = "biolink:Disease" if prefix == "MONDO:" else None
    new_nodes = pd.DataFrame({"id": new_ids, "category": [ncat or "biolink:BiologicalProcess"] * len(new_ids),
                              "name": [names.get(i, i) for i in new_ids], "source": source})
    edges = pd.DataFrame({"subject": [r[0] for r in rows], "predicate": "biolink:subclass_of", "object": [r[1] for r in rows],
                          "source": source, "evidence": f"{source}:is_a", "confidence": float("nan"), "timestamp": edge_ts,
                          "method": "ontology_hierarchy", "attributes": "{}"}).drop_duplicates(["subject", "object"])
    return new_nodes, edges


if __name__ == "__main__":
    graph, src, out = sys.argv[1:4]
    nodes, edges = pd.read_parquet(f"{graph}.nodes.parquet"), pd.read_parquet(f"{graph}.edges.parquet")
    ts = edges.timestamp.iloc[0]
    add_n, add_e = [], []
    for prefix, path, source in (("GO:", f"{src}/go/go-basic.obo", "go"), ("MONDO:", f"{src}/mondo/mondo.obo", "mondo")):
        n, e = hierarchy_edges(nodes, path, prefix, source, ts)
        add_n.append(n); add_e.append(e)
        print(f"{source}: {len(e)} subclass_of edges, {len(n)} new ancestor nodes")
    nodes2 = pd.concat([nodes] + add_n, ignore_index=True)
    edges2 = pd.concat([edges] + add_e, ignore_index=True)
    for c in edges.columns:          # structural facts from the ontology: verdict columns filled in
        if c not in add_e[0].columns:
            edges2[c] = edges2[c].where(edges2.evidence.isin(edges.evidence.unique()), {"verdict": "keep", "verdict_confidence": 1.0,
                      "reason": "ontology hierarchy (GO / MONDO)", "rule": "ontology_edge", "needs_review": False}.get(c))
    nodes2.to_parquet(f"{out}.nodes.parquet"); edges2.to_parquet(f"{out}.edges.parquet")
    print(len(nodes2), "nodes,", len(edges2), "edges")
