"""Pull the Pharos KG live from its public GraphQL API and write it in the
shared schema (nodes/edges Parquet). Raw pages are cached under data/raw so
re-runs don't re-fetch.

Usage: python -m bioagent.ingest.pharos OUT_PREFIX [--limit N]
"""
import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from bioagent.schema.kg import write_kg

URL = "https://pharos-api.ncats.io/graphql"
# pharos/ = old truncated pages, pharos_full/ = full lists without evidence; pharos_evidence/ = full lists + evidence
CACHE = Path(__file__).resolve().parents[3] / "data" / "raw" / "pharos_evidence"
PAGE = 20
# Pharos returns only 10 items per nested list (20 for GO) unless `top` is given; we use top:5000.
# Per-edge evidence: PPI props (Score, p_int) and, per disease, the supporting association
# records (source database `type` and `score`; capped at 100 per disease).
FIELDS = """
  uniprot sym name tdl
  diseases(top:5000){ name mondoID associations(top:100){ type score } }
  ligands(top:5000){ ligid name isdrug }
  ppis(top:5000){ type props{ name value } target{ uniprot } }
  go(top:5000){ goid term type }"""

# skip/top live on the *inner* targets field; the outer ones are ignored.
QUERY = "query($skip:Int,$top:Int){ targets{ targets(skip:$skip, top:$top){" + FIELDS + "\n} } }"

GO_TYPE = {"F": "biolink:MolecularActivity", "P": "biolink:BiologicalProcess",
           "C": "biolink:CellularComponent"}


def _float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def slim(t):
    """Reduce evidence-heavy fields to what we keep, before caching."""
    for d in t.get("diseases") or []:
        assoc = d.pop("associations", None) or []
        scores = [a["score"] for a in assoc if a.get("score") is not None]
        d["assoc"] = {"n": len(assoc), "types": sorted({a["type"] for a in assoc if a.get("type")}),
                      "max_score": max(scores) if scores else None}
    for p in t.get("ppis") or []:
        props = {x["name"]: x["value"] for x in (p.pop("props", None) or [])}
        p["score"], p["p_int"] = _float(props.get("Score")), _float(props.get("p_int"))
    return t


def _post(skip, top, retries=4):
    for i in range(retries):
        try:
            r = requests.post(URL, json={"query": QUERY, "variables": {"skip": skip, "top": top}}, timeout=120)
            r.raise_for_status()
            body = r.json()
            if "errors" in body:
                raise RuntimeError(body["errors"][0]["message"])
            return [slim(t) for t in body["data"]["targets"]["targets"]]
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


TARGET_QUERY = "query($q:ITarget){ target(q:$q){" + FIELDS + "\n} }"
TARGET_CACHE = CACHE.parent / "pharos_targets"
_UNIPROT = re.compile(r"^([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})$")


def fetch_target(identifier, retries=3):
    """One target by gene symbol or UniProt accession (live API, cached on disk).
    Returns the target dict, or None if Pharos has no such target."""
    ident = identifier.strip()
    q = {"uniprot": ident.upper()} if _UNIPROT.match(ident.upper()) else {"sym": ident}
    TARGET_CACHE.mkdir(parents=True, exist_ok=True)
    f = TARGET_CACHE / (re.sub(r"[^A-Za-z0-9_.-]", "_", ident.upper()) + ".json")
    if f.exists():
        return json.loads(f.read_text())
    for i in range(retries):
        try:
            r = requests.post(URL, json={"query": TARGET_QUERY, "variables": {"q": q}}, timeout=60)
            r.raise_for_status()
            body = r.json()
            if "errors" in body:
                raise RuntimeError(body["errors"][0]["message"])
            t = body["data"]["target"]
            t = slim(t) if t else t
            f.write_text(json.dumps(t))
            return t
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(2 ** i)


def to_kg(targets):
    ts = datetime.now(timezone.utc).isoformat()
    nodes, edges = {}, []

    def node(i, cat, name):
        nodes.setdefault(i, {"id": i, "category": cat, "name": name, "source": "pharos"})

    def edge(s, p, o, ev, conf=None, attrs=None):
        # confidence = the source-reported score where Pharos gives one, else NaN (unknown)
        edges.append({"subject": s, "predicate": p, "object": o, "source": "pharos",
                      "evidence": ev, "confidence": float("nan") if conf is None else conf,
                      "timestamp": ts, "method": "pharos_graphql",
                      "attributes": json.dumps(attrs or {}, sort_keys=True)})

    for t in targets:
        if not t.get("uniprot"):
            continue
        tid = f"UniProtKB:{t['uniprot']}"
        node(tid, "biolink:Protein", t.get("sym") or t.get("name"))
        for d in t.get("diseases") or []:
            if d.get("mondoID"):
                node(d["mondoID"], "biolink:Disease", d["name"])
                a = d.get("assoc") or {}
                edge(tid, "biolink:related_to", d["mondoID"], "pharos:disease_association",
                     a.get("max_score"), {"n_assoc": a.get("n"), "assoc_types": a.get("types")})
        for l in t.get("ligands") or []:
            lid = f"PHAROS.LIGAND:{l['ligid']}"
            node(lid, "biolink:Drug" if l.get("isdrug") else "biolink:SmallMolecule", l["name"])
            edge(lid, "biolink:interacts_with", tid, "pharos:ligand_activity")
        for p in t.get("ppis") or []:
            o = (p.get("target") or {}).get("uniprot")
            if o:
                oid = f"UniProtKB:{o}"
                node(oid, "biolink:Protein", o)
                edge(tid, "biolink:interacts_with", oid, f"pharos:ppi:{p.get('type')}",
                     p.get("score"), {"p_int": p.get("p_int")})
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
