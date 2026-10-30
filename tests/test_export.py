import tempfile
import pandas as pd
import torch
from bioagent.export.formats import to_kgx, to_pyg
from bioagent.standards.biolink import specialise

nodes = pd.DataFrame({"id": ["UniProtKB:P1", "UniProtKB:P2", "MONDO:1", "GO:1", "GO:2", "CHEM:1"],
                      "category": ["biolink:Protein"] * 2 + ["biolink:Disease", "biolink:BiologicalProcess", "biolink:CellularComponent", "biolink:SmallMolecule"],
                      "name": list("abcdef"), "source": "pharos"})
def e(s, p, o, ev, c=float("nan"), v="keep"):
    return dict(subject=s, predicate=p, object=o, source="pharos", evidence=ev, confidence=c, method="m", timestamp="t",
                attributes="{}", verdict=v, verdict_confidence=0.9, reason="r", rule="x", needs_review=False)
edges = pd.DataFrame([e("UniProtKB:P1", "biolink:interacts_with", "UniProtKB:P2", "pharos:ppi:STRINGDB", 0.8),
                      e("UniProtKB:P1", "biolink:interacts_with", "UniProtKB:P2", "pharos:ppi:BioPlex,STRINGDB", 0.5),
                      e("UniProtKB:P1", "biolink:related_to", "MONDO:1", "pharos:disease_association", 0.7),
                      e("UniProtKB:P1", "biolink:related_to", "GO:1", "pharos:go"),
                      e("UniProtKB:P1", "biolink:related_to", "GO:2", "pharos:go", v="prune"),
                      e("CHEM:1", "biolink:interacts_with", "UniProtKB:P1", "pharos:ligand_activity")])
s = specialise(nodes, edges)
assert list(s.predicate) == ["biolink:interacts_with", "biolink:physically_interacts_with", "biolink:associated_with",
                             "biolink:actively_involved_in", "biolink:located_in", "biolink:physically_interacts_with"]
assert list(s.original_predicate) == list(edges.predicate)
with tempfile.TemporaryDirectory() as d:
    to_kgx(nodes, s, d)
    k = pd.read_csv(f"{d}/edges.tsv", sep="\t")
    assert len(k) == 6 and k.id.is_unique and {"subject", "predicate", "object", "primary_knowledge_source"} <= set(k.columns)
    assert pd.read_csv(f"{d}/nodes.tsv", sep="\t").provided_by.iloc[0] == "infores:pharos"
    to_pyg(nodes, s, f"{d}/g.pt")
    o = torch.load(f"{d}/g.pt", weights_only=False)
    data = o["data"]
    assert data["Protein", "associated_with", "Disease"].edge_index.tolist() == [[0], [0]]
    a = data["Protein", "actively_involved_in", "BiologicalProcess"].edge_attr[0].tolist()
    assert a[1] == 0.0 and abs(a[2] - 0.9) < 1e-6 and a[3] == 1.0                      # no source score, kept
    assert data["Protein", "located_in", "CellularComponent"].edge_attr[0, 3] == 0.0      # pruned edge is marked, not dropped
    assert o["node_ids"]["Protein"] == ["UniProtKB:P1", "UniProtKB:P2"]
print("ALL PASSED")
