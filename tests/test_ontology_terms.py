import pandas as pd
from bioagent.standards.ontology import annotate_edges, annotate_nodes, iri

n = annotate_nodes(pd.DataFrame({"id": ["ENSEMBL:E1", "ENSEMBL:E2", "UniProtKB:P1", "MONDO:0005233", "GO:0008150", "PHAROS.LIGAND:X"],
    "category": ["biolink:Gene"] * 2 + ["biolink:Protein", "biolink:Disease", "biolink:BiologicalProcess", "biolink:SmallMolecule"],
    "biotype": ["protein_coding", "lncRNA", None, None, None, None]}))
assert list(n.ontology_class[:3]) == ["SO:0001217", "SO:0000704", "PR:000000001"]     # specific class only when protein coding
assert n.ontology_class_iri[2] == "http://purl.obolibrary.org/obo/PR_000000001"
assert n.iri[3] == "http://purl.obolibrary.org/obo/MONDO_0005233" and n.iri[2] == "https://identifiers.org/uniprot:P1"
e = annotate_edges(pd.DataFrame({"predicate": ["biolink:has_gene_product", "biolink:associated_with"]}))
assert e.predicate_iri[0] == "http://purl.obolibrary.org/obo/RO_0002205" and pd.isna(e.predicate_ontology[1])    # no invented mapping
assert iri("unknown:1") is None
print("ALL PASSED")
