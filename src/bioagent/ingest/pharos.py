"""Pull the Pharos KG live from its public GraphQL API and write it in the
shared schema (nodes/edges Parquet). Raw pages are cached under data/raw so
re-runs don't re-fetch.

Usage: python -m bioagent.ingest.pharos OUT_PREFIX [--limit N]
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from bioagent.schema.kg import write_kg

URL = "https://pharos-api.ncats.io/graphql"
CACHE = Path(__file__).resolve().parents[3] / "data" / "raw" / "pharos"
PAGE = 50

# skip/top live on the *inner* targets field; the outer ones are ignored.
QUERY = """
query($skip:Int,$top:Int){ targets{ targets(skip:$skip, top:$top){
  uniprot sym name tdl
  diseases{ name mondoID }
  ligands{ ligid name isdrug }
  ppis{ type target{ uniprot } }
  go{ goid term type }
} } }"""

GO_TYPE = {"F": "biolink:MolecularActivity", "P": "biolink:BiologicalProcess",
           "C": "biolink:CellularComponent"}


def _post(skip, top, retries=4):
    for i in range(retries):
        try:
            r = requests.post(URL, json={"query": QUERY, "variables": {"skip": skip, "top": top}}, timeout=120)
            r.raise_for_status()
            body = r.json()
            if "errors" in body:
                raise RuntimeError(body["errors"][0]["message"])
            return body["data"]["targets"]["targets"]
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(2 ** i)


def fetch(limit=None):
    CACHE.mkdir(parents=True, exist_ok=True)
    out, skip = [], 0
    while limit is None or skip < limit:
        top = PAGE if limit is None else min(PAGE, limit - skip)
        f = CACHE / f"targets_{skip}_{top}.json"
        if f.exists():
            page = json.loads(f.read_text())
        else:
            page = _post(skip, top)
            f.write_text(json.dumps(page))
        if not page:
            break
        out += page
        skip += top
        if len(page) < top:
            break
    return out


def to_kg(targets):
    ts = datetime.now(timezone.utc).isoformat()
    nodes, edges = {}, []

    def node(i, cat, name):
        nodes.setdefault(i, {"id": i, "category": cat, "name": name, "source": "pharos"})

    def edge(s, p, o, ev):
        edges.append({"subject": s, "predicate": p, "object": o, "source": "pharos",
                      "evidence": ev, "confidence": 1.0, "timestamp": ts, "method": "pharos_graphql"})

    for t in targets:
        if not t.get("uniprot"):
            continue
        tid = f"UniProtKB:{t['uniprot']}"
        node(tid, "biolink:Protein", t.get("sym") or t.get("name"))
        for d in t.get("diseases") or []:
            if d.get("mondoID"):
                node(d["mondoID"], "biolink:Disease", d["name"])
                edge(tid, "biolink:related_to", d["mondoID"], "pharos:disease_association")
        for l in t.get("ligands") or []:
            lid = f"PHAROS.LIGAND:{l['ligid']}"
            node(lid, "biolink:Drug" if l.get("isdrug") else "biolink:SmallMolecule", l["name"])
            edge(lid, "biolink:interacts_with", tid, "pharos:ligand_activity")
        for p in t.get("ppis") or []:
            o = (p.get("target") or {}).get("uniprot")
            if o:
                oid = f"UniProtKB:{o}"
                node(oid, "biolink:Protein", o)
                edge(tid, "biolink:interacts_with", oid, f"pharos:ppi:{p.get('type')}")
        for g in t.get("go") or []:
            node(g["goid"], GO_TYPE.get(g.get("type"), "biolink:BiologicalProcess"), g["term"])
            edge(tid, "biolink:related_to", g["goid"], "pharos:go")
    nodes_df = pd.DataFrame(nodes.values())
    edges_df = pd.DataFrame(edges).drop_duplicates(["subject", "predicate", "object"]).reset_index(drop=True)
    return nodes_df, edges_df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out_prefix")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    n, e = to_kg(fetch(a.limit))
    write_kg(n, e, a.out_prefix)
    print(f"{len(n)} nodes, {len(e)} edges")
    print(e.groupby(["predicate", "evidence"]).size().sort_values(ascending=False).head(10))
