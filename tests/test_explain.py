"""Explanation tests on a tiny synthetic graph. Run: python tests/test_explain.py"""
import json
import pandas as pd
from bioagent.provenance.explain import explain, format_explanation, resolve

nodes = pd.DataFrame([
    {"id": "P:A", "category": "biolink:Protein", "name": "AAA", "source": "t"},
    {"id": "P:B", "category": "biolink:Protein", "name": "BBB", "source": "t"},
    {"id": "P:C", "category": "biolink:Protein", "name": "CCC", "source": "t"},
    {"id": "D:1", "category": "biolink:Disease", "name": "Disease One", "source": "t"},
    {"id": "D:2", "category": "biolink:Disease", "name": "Disease Two", "source": "t"}])
def E(s, o, ev, conf, v, vc, reason):
    return dict(subject=s, predicate="biolink:related_to", object=o, source="pharos", evidence=ev, confidence=conf,
                timestamp="t", method="m", attributes=json.dumps({"n_assoc": 2}), verdict=v, verdict_confidence=vc,
                reason=reason, rule="r", needs_review=False)
edges = pd.DataFrame([
    E("P:A", "D:1", "pharos:disease_association", 0.5, "keep", 0.7, "two databases agree"),
    E("P:B", "D:1", "pharos:disease_association", float("nan"), "prune", 0.2, "weak evidence"),
    E("P:C", "D:1", "pharos:disease_association", 0.9, "keep", 0.9, "strong"),
    E("P:A", "P:C", "pharos:ppi:STRINGDB", 0.8, "keep", 0.8, "STRING 0.8"),
    E("P:C", "P:A", "pharos:ppi:STRINGDB", 0.6, "keep", 0.6, "STRING 0.6"),
    E("P:B", "D:2", "pharos:disease_association", 0.5, "keep", 0.5, "x")])
g = (nodes, edges)

assert resolve(nodes, "aaa") == "P:A" and resolve(nodes, "D:1") == "D:1"
x = explain(None, "AAA", "Disease One", graph=g)
assert len(x["direct_edges"]) == 1 and x["direct_edges"][0]["verdict"] == "keep"
assert x["n_shared_neighbours"] == 1 and x["paths"][0]["via"] == "P:C"   # A-C-D1, strength min(0.8, 0.9)
assert abs(x["paths"][0]["strength"] - 0.8) < 1e-9
y = explain(None, "AAA", "BBB", graph=g)                                  # no direct edge; via D:1 only
assert y["direct_edges"] == [] and y["paths"][0]["via"] == "D:1"
assert abs(y["paths"][0]["strength"] - 0.2) < 1e-9                        # limited by the pruned edge
z = explain(None, "BBB", "Disease Two", graph=g)
assert len(z["direct_edges"]) == 1 and z["paths"] == []
try:
    resolve(nodes, "nope"); raise SystemExit("should have failed")
except KeyError:
    pass
print(format_explanation(y)); print("ALL PASSED")
