"""Edge lineage: answer "why does A connect to B?" in plain language.

Works on the pruned-pipeline output (`<prefix>.whole.{nodes,edges}.parquet`, i.e. every edge
with verdict columns) or any graph in the shared format (verdict columns are then omitted).

  python -m bioagent.provenance.explain data/processed/pharos_pruned.whole "EGFR" "non-small cell lung carcinoma"

A and B can be node ids (UniProtKB:P00533, MONDO:0005233) or exact names (case-insensitive).
"""
import json
import sys

import pandas as pd

SHOW = ["subject", "predicate", "object", "source", "evidence", "confidence", "method", "timestamp",
        "attributes", "verdict", "verdict_confidence", "reason", "rule", "needs_review", "n_reported"]


def load(prefix, standard=False):
    """(nodes, edges). standard=True shows the specific Biolink predicates (as in the exports) instead of the generic ones."""
    # `whole` graphs are written as <prefix>.nodes.parquet / <prefix>.edges.parquet
    nodes, edges = pd.read_parquet(f"{prefix}.nodes.parquet"), pd.read_parquet(f"{prefix}.edges.parquet")
    if standard:
        from bioagent.standards.biolink import specialise
        edges = specialise(nodes, edges)
    return nodes, edges


def resolve(nodes, x):
    """Node id for an id or an exact (case-insensitive) name; raises if missing or ambiguous."""
    hit = nodes[nodes.id == x]
    if hit.empty:
        hit = nodes[nodes.name.astype(str).str.lower() == x.lower()]
    if hit.empty:
        raise KeyError(f"no node with id or name '{x}'")
    if len(hit) > 1:
        raise KeyError(f"'{x}' is ambiguous: {', '.join(hit.id.head(8))}")
    return hit.id.iloc[0]


def _rows(df):
    cols = [c for c in SHOW if c in df.columns]
    return df[cols].to_dict("records")


def explain(prefix, a, b, max_paths=5, graph=None):
    """Returns a dict: both nodes, direct edges (with provenance and verdicts), and the best
    two-step paths through a shared neighbour. `graph` = (nodes, edges) to avoid reloading."""
    nodes, e = graph if graph is not None else load(prefix, standard=True)
    ida, idb = resolve(nodes, a), resolve(nodes, b)
    name = dict(zip(nodes.id, nodes.name))
    cat = dict(zip(nodes.id, nodes.category))
    direct = e[((e.subject == ida) & (e.object == idb)) | ((e.subject == idb) & (e.object == ida))]
    # A-B and B-A rows with the same predicate/evidence/source are one fact reported twice: keep the best
    sc = "verdict_confidence" if "verdict_confidence" in direct.columns else "confidence"
    n_rows = direct.groupby(["predicate", "evidence", "source"]).size()
    direct = (direct.sort_values(sc, ascending=False, na_position="last")
                    .drop_duplicates(["predicate", "evidence", "source"]).copy())
    direct["n_reported"] = [int(n_rows[(p, ev, so)]) for p, ev, so in zip(direct.predicate, direct.evidence, direct.source)]

    ea = e[(e.subject == ida) | (e.object == ida)]
    eb = e[(e.subject == idb) | (e.object == idb)]

    def other(df, me):
        return df.object.where(df.subject == me, df.subject)

    na, nb = other(ea, ida), other(eb, idb)
    shared = (set(na) & set(nb)) - {ida, idb}
    has_v = "verdict_confidence" in e.columns
    score_col = "verdict_confidence" if has_v else "confidence"
    paths = []
    if shared:
        ea2 = ea.assign(_n=na)[lambda d: d._n.isin(shared)]
        eb2 = eb.assign(_n=nb)[lambda d: d._n.isin(shared)]
        # best (highest-confidence) edge on each side per shared neighbour
        ba = ea2.sort_values(score_col, ascending=False, na_position="last").drop_duplicates("_n").set_index("_n")
        bb = eb2.sort_values(score_col, ascending=False, na_position="last").drop_duplicates("_n").set_index("_n")
        for n in ba.index:
            ca, cb = ba.at[n, score_col], bb.at[n, score_col]
            strength = min(ca, cb) if pd.notna(ca) and pd.notna(cb) else float("nan")
            paths.append({"via": n, "via_name": name.get(n), "via_category": cat.get(n), "strength": strength,
                          "first_edge": _rows(ba.loc[[n]].reset_index(drop=True))[0],
                          "second_edge": _rows(bb.loc[[n]].reset_index(drop=True))[0]})
        paths.sort(key=lambda p: (-(p["strength"] if p["strength"] == p["strength"] else -1)))
    return {"a": {"id": ida, "name": name.get(ida), "category": cat.get(ida)},
            "b": {"id": idb, "name": name.get(idb), "category": cat.get(idb)},
            "direct_edges": _rows(direct), "n_shared_neighbours": len(shared), "paths": paths[:max_paths]}


def _edge_line(r, flip=False):
    parts = [f"{r['predicate']} (source: {r['source']}, evidence: {r['evidence']}"]
    if pd.notna(r.get("confidence")):
        parts[0] += f", source score {r['confidence']:.2f}"
    parts[0] += ")"
    if r.get("verdict"):
        parts.append(f"verdict {r['verdict'].upper()} at confidence {r['verdict_confidence']:.2f}: {r['reason']}")
    if r.get("needs_review"):
        parts.append("flagged for later review")
    if r.get("n_reported", 1) > 1:
        parts.append(f"reported {r['n_reported']} times (once per direction)")
    return "; ".join(parts)


def format_explanation(x):
    a, b = x["a"], x["b"]
    out = [f"A = {a['name']} [{a['id']}]  ({a['category']})", f"B = {b['name']} [{b['id']}]  ({b['category']})", ""]
    if x["direct_edges"]:
        out.append(f"Direct connection: {len(x['direct_edges'])} edge(s)")
        for r in x["direct_edges"]:
            out.append("  - " + _edge_line(r))
            attrs = json.loads(r["attributes"]) if r.get("attributes") else {}
            if attrs:
                out.append(f"    extra evidence: {attrs}")
    else:
        out.append("No direct edge between A and B.")
    out.append("")
    if x["paths"]:
        out.append(f"Indirect connections: {x['n_shared_neighbours']} shared neighbour(s); best {len(x['paths'])}:")
        for p in x["paths"]:
            s = "n/a" if p["strength"] != p["strength"] else f"{p['strength']:.2f}"
            out.append(f"  - via {p['via_name']} [{p['via']}] ({p['via_category']}), path strength {s}")
            out.append(f"      A-{p['via_name']}: " + _edge_line(p["first_edge"]))
            out.append(f"      {p['via_name']}-B: " + _edge_line(p["second_edge"]))
    else:
        out.append("No shared neighbours, so no two-step connection.")
    return "\n".join(out)


if __name__ == "__main__":
    print(format_explanation(explain(sys.argv[1], sys.argv[2], sys.argv[3])))
