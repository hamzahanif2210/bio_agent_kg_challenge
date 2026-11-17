"""Question-to-graph: a plain-language question in, the relevant piece of the knowledge graph out.

  python -m bioagent.qa.ask data/processed/pharos_pruned_v2 "How is EGFR connected to lung cancer?" \
      --base-url https://ellm.nrp-nautilus.io/v1 --model gpt-oss        # key from env LLM_API_KEY
  python -m bioagent.qa.ask data/processed/pharos_pruned_v2 --entities EGFR "lung cancer"   # no LLM needed

Steps: (1) the LLM only picks out the names the question is about, as JSON; (2) the names are matched to graph
nodes by plain lookup (never by the LLM); (3) the subgraph is cut out of the graph and every edge is shown with
its source, evidence, verdict and reason. The LLM never supplies a fact: everything shown comes from the graph.
Two entities -> how they connect (direct edges and two-step paths); one -> its best-supported neighbours.
"""
import argparse
import json
import os
import re

import pandas as pd

from bioagent.provenance.explain import explain, format_explanation, load

SYSTEM = ("You find the biomedical entities a question is about. Reply with JSON only: "
          '{"entities": ["name or identifier as written, e.g. gene symbol, disease, drug, GO term", ...]}. '
          "At most 3 entities, no commentary.")


def extract_entities(llm, model, question, max_tokens=2000):
    r = llm(model, SYSTEM, [{"role": "user", "content": question}], [], max_tokens)
    text = " ".join(b["text"] for b in r["content"] if b["type"] == "text")
    m = re.search(r"\{.*\}", text, re.S)
    try:
        ents = json.loads(m.group(0))["entities"] if m else []
    except (ValueError, KeyError, TypeError):
        ents = []
    return [str(x).strip() for x in ents if str(x).strip()][:3]


class Index:
    """Name -> node lookup. Exact id or name first; then a whole-phrase match inside names, best-connected first."""

    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.by_name = nodes.assign(_l=nodes.name.astype(str).str.lower())
        deg = pd.concat([edges.subject, edges.object]).value_counts()
        self.by_name["_deg"] = self.by_name.id.map(deg).fillna(0)

    def find(self, text, limit=5):
        t = text.lower().strip()
        n = self.by_name
        hit = n[(n.id == text) | (n._l == t)]
        kind = "exact"
        if hit.empty:
            hit = n[n._l.str.contains(r"\b" + re.escape(t) + r"\b", regex=True)]
            kind = "partial"
        hit = hit.sort_values("_deg", ascending=False).head(limit)
        return kind, hit[["id", "name", "category", "_deg"]].to_dict("records")


def neighbours(edges, nodes, node_id, top=15, kept_only=True):
    e = edges[(edges.subject == node_id) | (edges.object == node_id)]
    if kept_only and "verdict" in e.columns:
        e = e[e.verdict == "keep"]
    name, cat = dict(zip(nodes.id, nodes.name)), dict(zip(nodes.id, nodes.category))
    e = e.assign(other=e.object.where(e.subject == node_id, e.subject))
    sc = "verdict_confidence" if "verdict_confidence" in e.columns else "confidence"
    e = e.sort_values(sc, ascending=False, na_position="last").drop_duplicates("other")
    out = {}
    for c, g in e.groupby(e.other.map(cat)):
        out[c] = [{"id": r.other, "name": name.get(r.other), "evidence": r.evidence, "score": getattr(r, sc),
                   "reason": getattr(r, "reason", None)} for r in g.head(top).itertuples()]
    return out


def answer(prefix, entities, graph=None, hops=None, kept_only=True, min_conf=0.0, types=None, max_nodes=60):
    """entities: list of names/ids. Returns (text, subgraph dict). With `hops` set, the multi-hop search with filters is used
    (qa/hops.py); without it, the two-hop explanation (two names) or the best neighbours (one name)."""
    nodes, edges = graph if graph is not None else load(prefix, standard=True)
    idx = Index(nodes, edges)
    found, notes = [], []
    for ent in entities:
        kind, hits = idx.find(ent)
        if not hits:
            notes.append(f"'{ent}': no matching node in the graph")
            continue
        if kind == "partial" or len(hits) > 1:
            notes.append(f"'{ent}': matched {hits[0]['name']} [{hits[0]['id']}]"
                         + (f" (other candidates: {', '.join(h['name'] for h in hits[1:4])})" if len(hits) > 1 else ""))
        found.append(hits[0]["id"])
    lines = list(notes)
    if hops and found:
        from bioagent.qa import hops as H
        filt = H.describe_filters(kept_only, min_conf, types)
        if len(found) >= 2:
            r = H.connect(nodes, edges, found[0], found[1], hops, kept_only, min_conf, types)
            lines += ["", H.format_paths(r, nodes, filt)]
            rows = {(x["subject"], x["object"], x.get("predicate")): x for p in r["paths"] for x in p["edges"]}
            return "\n".join(lines), {**r, "edge_rows": list(rows.values())}
        r = H.neighbourhood(nodes, edges, found[0], hops, kept_only, min_conf, types, max_nodes=max_nodes)
        lines += ["", H.format_neighbourhood(r, nodes, filt)]
        return "\n".join(lines), r
    if len(found) >= 2:
        x = explain(prefix, found[0], found[1], graph=(nodes, edges))
        lines += ["", format_explanation(x)]
        sub = {**x, "edge_rows": list(x["direct_edges"]) + [r for p in x["paths"] for r in (p["first_edge"], p["second_edge"])]}
    elif len(found) == 1:
        nb = neighbours(edges, nodes, found[0])
        nm = nodes.set_index("id").name.get(found[0])
        lines += ["", f"Best-supported kept neighbours of {nm} [{found[0]}]:"]
        for c, rows in nb.items():
            lines.append(f"  {c.replace('biolink:', '')} ({len(rows)} shown)")
            for r in rows[:8]:
                s = "" if pd.isna(r["score"]) else f", score {r['score']:.2f}"
                lines.append(f"    - {r['name']} [{r['id']}] ({r['evidence']}{s})")
        shown = {r["id"] for rows in nb.values() for r in rows[:8]}
        near = edges[(((edges.subject == found[0]) & edges.object.isin(shown)) | ((edges.object == found[0]) & edges.subject.isin(shown)))]
        if "verdict" in near.columns:
            near = near[near.verdict == "keep"]
        sub = {"center": found[0], "neighbours": nb, "edge_rows": near.drop_duplicates(["subject", "object"]).to_dict("records")}
    else:
        lines.append("I could not find any entity from the question in the graph.")
        sub = {}
    return "\n".join(lines), sub


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("graph", help="whole-graph prefix, e.g. data/processed/pharos_pruned_v2.whole")
    ap.add_argument("question", nargs="?")
    ap.add_argument("--entities", nargs="+", help="skip the LLM and give the entities directly")
    ap.add_argument("--base-url"); ap.add_argument("--model", default="gpt-oss")
    ap.add_argument("--html", help="also write an interactive picture to this file")
    ap.add_argument("--hops", type=int, help="search this many hops (more than two) with the filters below")
    ap.add_argument("--min-conf", type=float, default=0.0); ap.add_argument("--include-pruned", action="store_true")
    ap.add_argument("--types", nargs="+"); ap.add_argument("--max-nodes", type=int, default=60)
    a = ap.parse_args()
    ents = a.entities
    if not ents:
        from bioagent.ingest.harness import openai_llm
        ents = extract_entities(openai_llm(a.base_url, os.environ["LLM_API_KEY"]), a.model, a.question)
        print("entities from the question:", ents)
    text, sub = answer(a.graph, ents, hops=a.hops, kept_only=not a.include_pruned, min_conf=a.min_conf, types=a.types, max_nodes=a.max_nodes)
    print(text)
    if a.html and sub.get("edge_rows"):
        from bioagent.qa.visual import to_html
        to_html(sub["edge_rows"], load(a.graph)[0], " / ".join(ents), a.html)
        print("picture written to", a.html)
