import numpy as np
import pandas as pd
from bioagent.ingest.update import apply_update, diff_edges, owned_by

def e(s, o, ev, c=float("nan")):
    return dict(subject=s, predicate="p", object=o, source="pharos", evidence=ev, confidence=c, timestamp="t", method="m", attributes="{}")
old = pd.DataFrame([e("UniProtKB:A", "UniProtKB:B", "pharos:ppi:STRINGDB", 0.5), e("UniProtKB:A", "GO:1", "pharos:go"),
                    e("UniProtKB:A", "MONDO:1", "pharos:disease_association", 0.4), e("L:1", "UniProtKB:A", "pharos:ligand_activity"),
                    e("UniProtKB:Z", "GO:1", "pharos:go")])           # Z is a different target and must not be touched
fresh = pd.DataFrame([e("UniProtKB:A", "UniProtKB:B", "pharos:ppi:STRINGDB", 0.9),       # re-scored
                      e("UniProtKB:A", "GO:1", "pharos:go"),                             # unchanged
                      e("UniProtKB:A", "GO:2", "pharos:go"),                             # new
                      e("L:1", "UniProtKB:A", "pharos:ligand_activity")])                # disease edge disappeared
tids = {"UniProtKB:A"}
assert owned_by(old, tids).tolist() == [True, True, True, True, False]
added, removed, rescored = diff_edges(old[owned_by(old, tids)], fresh)
assert added.object.tolist() == ["GO:2"] and removed.object.tolist() == ["MONDO:1"] and rescored.confidence.tolist() == [0.9]
nodes = pd.DataFrame({"id": ["UniProtKB:A"], "category": "biolink:Protein", "name": "a", "source": "pharos"})
fnodes = pd.DataFrame({"id": ["UniProtKB:A", "GO:2"], "category": ["biolink:Protein", "biolink:BiologicalProcess"], "name": ["a", "g"], "source": "pharos"})
n2, e2, _ = apply_update(nodes, old, fnodes, fresh, tids)
assert len(e2) == 5 and "MONDO:1" not in set(e2.object) and "GO:2" in set(e2.object) and "GO:2" in set(n2.id)
assert e2[(e2.object == "UniProtKB:B")].confidence.iloc[0] == 0.9 and e2[(e2.subject == "UniProtKB:Z")].shape[0] == 1
print("ALL PASSED")
