import pandas as pd
from bioagent.qa.ask import answer
from bioagent.qa.hops import neighbourhood, connect, filtered

ids = ["A", "B", "C", "D", "X", "Y"]
nodes = pd.DataFrame({"id": ids, "name": ["alpha", "beta", "gamma", "delta", "xi", "ypsilon"],
                      "category": ["biolink:Protein", "biolink:Protein", "biolink:Protein", "biolink:Disease", "biolink:Protein", "biolink:Protein"]})
def e(s, o, v="keep", c=0.9):
    return dict(subject=s, predicate="biolink:related_to", object=o, source="s", evidence="ev", confidence=c, verdict=v, verdict_confidence=c, reason="r")
# chain A-B-C-D, a weak shortcut A-X-D, a pruned shortcut A-Y-D
edges = pd.DataFrame([e("A", "B"), e("B", "C"), e("C", "D"), e("A", "X", c=0.45), e("X", "D", c=0.45), e("A", "Y", "prune", 0.1), e("Y", "D", "prune", 0.1)])

r = neighbourhood(nodes, edges, "A", hops=1)
assert set(r["depth"]) == {"A", "B", "X"}                                 # pruned neighbour Y excluded
assert set(neighbourhood(nodes, edges, "A", hops=1, kept_only=False)["depth"]) == {"A", "B", "X", "Y"}
assert set(neighbourhood(nodes, edges, "A", hops=3)["depth"]) == {"A", "B", "X", "C", "D"}
assert neighbourhood(nodes, edges, "A", hops=3)["depth"]["D"] == 2        # shortest hop count wins (via X)
assert set(neighbourhood(nodes, edges, "A", hops=3, min_conf=0.6)["depth"]) == {"A", "B", "C", "D"}
assert set(neighbourhood(nodes, edges, "A", hops=3, types=["protein"])["depth"]) == {"A", "B", "X", "C"}   # D is a Disease
assert len(neighbourhood(nodes, edges, "A", hops=3, max_nodes=2)["depth"]) == 2 and neighbourhood(nodes, edges, "A", hops=3, max_nodes=2)["truncated"]
assert all(x["verdict"] == "keep" for x in neighbourhood(nodes, edges, "A", hops=3)["edge_rows"])

c = connect(nodes, edges, "A", "D", hops=3)
assert [p["hops"] for p in c["paths"]] == [2, 3] and c["paths"][0]["nodes"] == ["A", "X", "D"]
assert abs(c["paths"][0]["strength"] - 0.45) < 1e-9 and c["paths"][1]["nodes"] == ["A", "B", "C", "D"]
assert [p["hops"] for p in connect(nodes, edges, "A", "D", hops=2)["paths"]] == [2]
assert [p["nodes"] for p in connect(nodes, edges, "A", "D", hops=3, min_conf=0.6)["paths"]] == [["A", "B", "C", "D"]]
assert connect(nodes, edges, "A", "D", hops=1)["paths"] == []
assert len(connect(nodes, edges, "A", "D", hops=2, kept_only=False)["paths"]) == 2          # pruned path appears when allowed
assert connect(nodes, edges, "A", "D", hops=3, types=["Protein"])["paths"][0]["nodes"] == ["A", "X", "D"]  # end points are never filtered

text, sub = answer("x", ["alpha", "delta"], graph=(nodes, edges), hops=3)
assert "2 path(s)" in text and "alpha - xi - delta" in text and sub["edge_rows"]
text, sub = answer("x", ["alpha"], graph=(nodes, edges), hops=2, min_conf=0.6)
assert "Hop 2" in text and "gamma" in text and "xi" not in text
text, _ = answer("x", ["alpha", "delta"], graph=(nodes, edges))                             # without hops: the old two-hop behaviour
assert "Indirect connections" in text
assert len(filtered(edges, True, 0.0)) == 5
print("ALL PASSED")
