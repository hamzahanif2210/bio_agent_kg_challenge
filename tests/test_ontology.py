import os, tempfile
import pandas as pd
from bioagent.enrich.ontology import hierarchy_edges

obo = """[Term]
id: GO:C
name: child
is_a: GO:P

[Term]
id: GO:P
name: parent
relationship: part_of GO:R

[Term]
id: GO:R
name: root

[Term]
id: GO:OLD
name: old
is_obsolete: true
"""
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "go.obo"); open(p, "w").write(obo)
    nodes = pd.DataFrame({"id": ["GO:C", "UniProtKB:P1"], "category": ["biolink:BiologicalProcess", "biolink:Protein"], "name": ["child", "p"], "source": "pharos"})
    n, e = hierarchy_edges(nodes, p, "GO:", "go", "t")
    assert set(zip(e.subject, e.object)) == {("GO:C", "GO:P"), ("GO:P", "GO:R")}          # whole chain up to the root
    assert set(n.id) == {"GO:P", "GO:R"} and n.set_index("id").name["GO:P"] == "parent"
    assert (e.predicate == "biolink:subclass_of").all() and e.evidence.iloc[0] == "go:is_a"
print("ALL PASSED")
