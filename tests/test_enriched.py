import numpy as np, pandas as pd, torch, tempfile, os
from bioagent.export.formats import to_pyg

nodes = pd.DataFrame({"id": ["UniProtKB:P1", "UniProtKB:P2", "MONDO:1"], "category": ["biolink:Protein"] * 2 + ["biolink:Disease"], "name": list("abc"), "source": ["pharos"] * 3})
edges = pd.DataFrame({"subject": ["UniProtKB:P1"], "predicate": ["biolink:associated_with"], "object": ["MONDO:1"], "confidence": [0.5], "verdict": ["keep"]})
feats = {"seq": (np.array(["UniProtKB:P2"]), np.ones((1, 4), np.float32))}
p = os.path.join(tempfile.mkdtemp(), "g.pt")
d = torch.load(p, weights_only=False) if to_pyg(nodes, edges, p, feats) is not None else None
x = d["data"]["Protein"].x_seq
assert x.shape == (2, 4) and x[0].sum() == 0 and x[1].sum() == 4          # row order follows node_ids; P1 has no feature -> zeros
assert d["node_ids"]["Protein"] == ["UniProtKB:P1", "UniProtKB:P2"] and d["node_feature_names"] == ["seq"]
assert "x_seq" not in d["data"]["Disease"]
print("ALL PASSED")
