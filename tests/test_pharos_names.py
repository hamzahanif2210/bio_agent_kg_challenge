"""Protein node names must be gene symbols even when the protein first appears as a partner. Run: python tests/test_pharos_names.py"""
from bioagent.ingest.pharos import to_kg
a = {"uniprot": "P1", "sym": "AAA", "name": "a", "tdl": "T", "diseases": [], "ligands": [], "go": [],
     "ppis": [{"type": "STRINGDB", "score": 0.9, "p_int": None, "target": {"uniprot": "P2"}}]}
b = {"uniprot": "P2", "sym": "BBB", "name": "b", "tdl": "T", "diseases": [], "ligands": [], "go": [], "ppis": []}
for order in ([a, b], [b, a]):
    n, e = to_kg(order)
    names = dict(zip(n.id, n.name))
    assert names["UniProtKB:P1"] == "AAA" and names["UniProtKB:P2"] == "BBB", names
print("ALL PASSED")
