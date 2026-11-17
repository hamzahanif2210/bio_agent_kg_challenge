import os, tempfile
import pandas as pd
from bioagent.ingest.csv_ingest import ingest_csv, ingest_table, read_table, format_report, save
from bioagent.__main__ import main

nodes = pd.DataFrame({"id": ["UniProtKB:P1", "UniProtKB:P2", "UniProtKB:P3", "MONDO:1"], "name": ["EGFR", "GRB2", "KRAS", "lung cancer"],
                      "category": ["biolink:Protein"] * 3 + ["biolink:Disease"], "source": "pharos"})
def e(s, o, v, c, ev="pharos:ppi:X"):
    return dict(subject=s, predicate="biolink:related_to", object=o, source="pharos", evidence=ev, confidence=c, method="m",
                timestamp="t", attributes="{}", verdict=v, verdict_confidence=c, reason="r", rule="x", needs_review=False)
edges = pd.DataFrame([e("UniProtKB:P1", "MONDO:1", "keep", 0.9, "pharos:disease_association"), e("UniProtKB:P1", "UniProtKB:P2", "keep", 0.9),
                      e("UniProtKB:P2", "UniProtKB:P3", "keep", 0.9), e("UniProtKB:P1", "UniProtKB:P3", "keep", 0.9),
                      e("UniProtKB:P2", "MONDO:1", "prune", 0.1, "pharos:disease_association")])

csv = """subject,object,predicate,score,pmid,assay
EGFR,lung cancer,associated_with,0.8,12345678,western
egfr,GRB2,physically interacts with,0.5,,pulldown
GRB2,lung cancer,associated_with,0.5,,
NEWPROT,lung cancer,bogus_relation,0.2,,
UniProtKB:Q99999,lung cancer,,,,
EGFR,EGFR,related_to,0.9,,
EGFR,lung cancer,associated_with,0.8,12345678,dup
EGFR,KRAS,related_to,7,,
"""
n2, e2, rep = ingest_csv(csv, nodes, edges, "t.csv")
assert len(nodes) == 4 and len(edges) == 5                        # inputs untouched
add = e2.iloc[len(edges):].reset_index(drop=True)
assert rep["edges_added"] == len(add) == 6                         # self-edge skipped, exact duplicate row collapsed
r = add[(add.subject == "UniProtKB:P1") & (add.object == "MONDO:1")].iloc[0]
assert r.verdict == "keep" and r.rule == "user_confirmed" and "PMID 12345678" in r.reason and r.source == "user:t.csv"
assert r.predicate == "biolink:associated_with" and "western" in r.attributes
r = add[(add.subject == "UniProtKB:P1") & (add.object == "UniProtKB:P2")].iloc[0]   # name lookup is case-insensitive
assert r.predicate == "biolink:physically_interacts_with" and r.verdict == "keep" and "shared kept neighbour" in r.reason
r = add[(add.subject == "UniProtKB:P2") & (add.object == "MONDO:1")].iloc[0]         # graph pruned this pair: penalty applied
assert "pruned a link" in r.reason and r.verdict_confidence < 0.5
r = add[add.subject == "USER:NEWPROT"].iloc[0]                                        # new entity, weak score, no PMID
assert r.verdict == "prune" and r.rule == "user_unsupported" and r.needs_review and r.predicate == "biolink:related_to"
assert "USER:NEWPROT" in set(n2.id) and "UniProtKB:Q99999" in set(n2.id)
assert any("bogus_relation" in w for w in rep["warnings"]) and any("outside 0 to 1" in w for w in rep["warnings"])
assert any("same" in w for w in rep["warnings"])
assert "PRUNE" in format_report(rep) and rep["kept"] + rep["pruned"] == 6
try:
    ingest_csv("x,y\n1,2\n", nodes, edges); raise SystemExit("should fail")
except ValueError as ex:
    assert "subject" in str(ex)
assert list(read_table("x\ty\n1\t2\n").columns) == ["x", "y"]                         # tab separated also works

with tempfile.TemporaryDirectory() as d:                                              # the command line, end to end
    base = os.path.join(d, "g"); save(nodes, edges, base)
    f = os.path.join(d, "my.csv"); open(f, "w").write(csv)
    main(["--graph", base, "ingest-csv", f])
    n3, e3 = pd.read_parquet(f"{d}/my.whole.nodes.parquet"), pd.read_parquet(f"{d}/my.whole.edges.parquet")
    assert len(e3) == 11 and "USER:NEWPROT" in set(n3.id)
print("ALL PASSED")
