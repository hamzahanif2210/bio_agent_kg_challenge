"""Multi-hop questions with filters. `explain` stops at two hops; these go further and can be narrowed.

  neighbourhood(): everything within N hops of one node (best-supported links first, capped so the picture stays readable)
  connect():       the shortest paths of up to N hops between two nodes, strongest first

Filters (all optional): kept_only (drop pruned edges), min_conf (verdict confidence at or above), types (node classes the
walk may pass through, e.g. ["Protein", "Disease"]). The two nodes you ask about are never filtered out.
"""
from itertools import islice

import networkx as nx
import numpy as np
import pandas as pd

from bioagent.provenance.explain import _edge_line


def _sc(e):
    return "verdict_confidence" if "verdict_confidence" in e.columns else "confidence"


def filtered(edges, kept_only=True, min_conf=0.0):
    e = edges
    if kept_only and "verdict" in e.columns:
        e = e[e.verdict == "keep"]
    if min_conf:
        e = e[e[_sc(e)].fillna(0) >= min_conf]
    return e


def _types(types):
    return {("" if str(t).lower().startswith("biolink:") else "biolink:") + str(t).strip().lower() for t in types if str(t).strip()} or None


def _cat(nodes):
    return nodes.drop_duplicates("id").set_index("id").category.astype(str).str.lower()


def _orient(sub, frontier):
    fr = set(frontier)
    f = sub.subject.where(sub.subject.isin(fr), sub.object)
    return sub.assign(frm=f, to=sub.object.where(f == sub.subject, sub.subject))


def _dedupe_pairs(e, sc, limit=400):
    e = e.sort_values(sc, ascending=False, na_position="last")
    lo = np.where(e.subject < e.object, e.subject, e.object)
    hi = np.where(e.subject < e.object, e.object, e.subject)
    return e[~pd.Series(lo + "|" + hi, index=e.index).duplicated()].head(limit)


def neighbourhood(nodes, edges, seed, hops=2, kept_only=True, min_conf=0.0, types=None, top=6, max_nodes=60):
    """Nodes within `hops` of `seed`: each node keeps its `top` best-supported new neighbours per hop, `max_nodes` in all."""
    e = filtered(edges, kept_only, min_conf)
    sc = _sc(e)
    tset = _types(types) if types else None
    cat = _cat(nodes) if tset else None
    visited, frontier, depth, via = {seed}, [seed], {seed: 0}, {}
    truncated = False
    for h in range(1, hops + 1):
        sub = e[e.subject.isin(frontier) | e.object.isin(frontier)]
        if sub.empty:
            break
        sub = _orient(sub, frontier)
        sub = sub[~sub["to"].isin(visited)]
        if tset:
            sub = sub[sub["to"].map(cat).isin(tset)]
        sub = sub.sort_values(sc, ascending=False, na_position="last").drop_duplicates(["frm", "to"])
        capped = sub.groupby("frm", sort=False).head(top)
        truncated |= len(capped) < len(sub)
        room = max_nodes - len(visited)
        best = capped.groupby("to")[sc].max().sort_values(ascending=False, na_position="last")
        truncated |= len(best) > room
        best = best.head(max(room, 0))
        if best.empty:
            break
        for r in capped[capped["to"].isin(best.index)].drop_duplicates("to").to_dict("records"):
            via[r["to"]] = r
        new = list(best.index)
        visited.update(new)
        depth.update({n: h for n in new})
        frontier = new
    inner = e[e.subject.isin(visited) & e.object.isin(visited)]
    return {"center": seed, "hops": hops, "depth": depth, "via": via, "truncated": truncated,
            "edge_rows": _dedupe_pairs(inner, sc).to_dict("records")}


def _ball(e, seed, radius, sc, per_node=200):
    seen, frontier = {seed}, [seed]
    for _ in range(radius):
        sub = e[e.subject.isin(frontier) | e.object.isin(frontier)]
        if sub.empty:
            break
        sub = _orient(sub, frontier)
        sub = sub[~sub["to"].isin(seen)].sort_values(sc, ascending=False, na_position="last")
        new = set(sub.drop_duplicates(["frm", "to"]).groupby("frm", sort=False).head(per_node)["to"])
        seen |= new
        frontier = list(new)
    return seen


def connect(nodes, edges, a, b, hops=3, kept_only=True, min_conf=0.0, types=None, max_paths=5):
    """Shortest paths of at most `hops` edges between a and b (shorter first, then stronger). Strength = weakest edge."""
    e = filtered(edges, kept_only, min_conf)
    sc = _sc(e)
    ra, rb = -(-hops // 2), hops // 2
    ball = _ball(e, a, ra, sc) | _ball(e, b, rb, sc)
    sub = e[e.subject.isin(ball) & e.object.isin(ball)]
    best = _dedupe_pairs(sub, sc, limit=10 ** 7)
    G = nx.Graph()
    edge_of = {}
    for r in best.to_dict("records"):
        G.add_edge(r["subject"], r["object"])
        edge_of[frozenset((r["subject"], r["object"]))] = r
    tset = _types(types) if types else None
    cat = _cat(nodes) if tset else None
    paths = []
    if a in G and b in G:
        for L in range(1, hops + 1):
            for p in islice((p for p in nx.all_simple_paths(G, a, b, cutoff=L) if len(p) == L + 1), 300):
                if tset and any(cat.get(n) not in tset for n in p[1:-1]):
                    continue
                rows = [edge_of[frozenset(x)] for x in zip(p, p[1:])]
                vals = [r.get(sc) for r in rows]
                vals = [v for v in vals if v is not None and v == v]
                paths.append({"nodes": p, "edges": rows, "hops": L, "strength": min(vals) if vals else float("nan")})
    paths.sort(key=lambda x: (x["hops"], -(x["strength"] if x["strength"] == x["strength"] else -1)))
    return {"a": a, "b": b, "hops": hops, "paths": paths[:max_paths], "n_paths": len(paths)}


def describe_filters(kept_only, min_conf, types):
    bits = ["kept edges only" if kept_only else "kept and pruned edges"]
    if min_conf:
        bits.append(f"confidence >= {min_conf:g}")
    if types:
        bits.append("passing through " + "/".join(t.replace("biolink:", "") for t in types))
    return ", ".join(bits)


def format_neighbourhood(r, nodes, filt, per_hop=10):
    name = dict(zip(nodes.id, nodes.name))
    cat = dict(zip(nodes.id, nodes.category))
    c = r["center"]
    out = [f"Within {r['hops']} hop(s) of {name.get(c, c)} [{c}] ({filt}): {len(r['depth']) - 1} node(s)"
           + ("; list capped to the best-supported ones" if r["truncated"] else "")]
    for h in range(1, r["hops"] + 1):
        ns = [n for n, d in r["depth"].items() if d == h]
        if not ns:
            continue
        out.append(f"  Hop {h} ({len(ns)} node(s))")
        for n in ns[:per_hop]:
            v = r["via"][n]
            s = v.get("verdict_confidence", v.get("confidence"))
            sc = "" if s is None or s != s else f", {s:.2f}"
            out.append(f"    - {name.get(n, n)} [{n}] ({str(cat.get(n, '')).replace('biolink:', '')}) via {name.get(v['frm'], v['frm'])}: "
                       f"{str(v['predicate']).replace('biolink:', '')}, {v['evidence']}{sc}")
        if len(ns) > per_hop:
            out.append(f"    ... and {len(ns) - per_hop} more")
    return "\n".join(out)


def format_paths(r, nodes, filt):
    name = dict(zip(nodes.id, nodes.name))
    a, b = name.get(r["a"], r["a"]), name.get(r["b"], r["b"])
    if not r["paths"]:
        return f"No path of up to {r['hops']} hop(s) between {a} and {b} ({filt}). Try more hops or a lower confidence."
    out = [f"{r['n_paths']} path(s) of up to {r['hops']} hop(s) between {a} and {b} ({filt}); best {len(r['paths'])}:"]
    for i, p in enumerate(r["paths"], 1):
        s = "n/a" if p["strength"] != p["strength"] else f"{p['strength']:.2f}"
        chain = " - ".join(str(name.get(n, n)) for n in p["nodes"])
        out.append(f"  {i}. {chain}   ({p['hops']} hop(s), weakest link {s})")
        for x, y, row in zip(p["nodes"], p["nodes"][1:], p["edges"]):
            out.append(f"       {name.get(x, x)} - {name.get(y, y)}: {_edge_line(row)}")
    return "\n".join(out)
