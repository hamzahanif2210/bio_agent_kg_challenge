import pandas as pd
from bioagent.standards.genes import add_genes
from bioagent.standards.biolink import specialise

nodes = pd.DataFrame({"id": ["UniProtKB:P1", "UniProtKB:P2", "MONDO:1"], "category": ["biolink:Protein"] * 2 + ["biolink:Disease"],
                      "name": ["a", "b", "c"], "source": "pharos"})
def e(s, o, ev):
    return dict(subject=s, predicate="biolink:related_to", object=o, source="pharos", evidence=ev, confidence=0.5, timestamp="t",
                method="m", attributes="{}", verdict="keep", verdict_confidence=0.9, reason="r", rule="x", needs_review=False)
edges = pd.DataFrame([e("UniProtKB:P1", "MONDO:1", "pharos:disease_association"), e("UniProtKB:P2", "MONDO:1", "pharos:disease_association")])
mapping = pd.DataFrame({"uniprot": ["P1", "PX"], "ensembl": ["ENSG1", "ENSG9"], "symbol": ["G1", "G9"]})   # PX is not in the graph
n2, e2 = add_genes(nodes, edges, mapping)
assert (n2.category == "biolink:Gene").sum() == 1 and "ENSEMBL:ENSG9" not in set(n2.id)
assert list(e2.subject[:2]) == ["ENSEMBL:ENSG1", "UniProtKB:P2"] and e2.original_subject.iloc[0] == "UniProtKB:P1"
link = e2[e2.predicate == "biolink:has_gene_product"]
assert len(link) == 1 and link.object.iloc[0] == "UniProtKB:P1" and link.verdict.iloc[0] == "keep"
s = specialise(n2, e2)
assert list(s.predicate[:2]) == ["biolink:gene_associated_with_condition", "biolink:associated_with"]   # unmapped protein falls back
print("ALL PASSED")
