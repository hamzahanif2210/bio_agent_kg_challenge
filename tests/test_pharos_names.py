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

# cached target records from an older format must be refetched, current ones reused
import json, tempfile
from pathlib import Path
from bioagent.ingest import pharos
with tempfile.TemporaryDirectory() as d:
    pharos.TARGET_CACHE = Path(d)
    (Path(d) / "OLD.json").write_text(json.dumps({"uniprot": "P1", "ppis": []}))               # no _schema: stale
    (Path(d) / "NEW.json").write_text(json.dumps({"uniprot": "P2", "_schema": pharos.SCHEMA_VERSION}))
    calls = []
    class R:
        def raise_for_status(self): pass
        def json(self): return {"data": {"target": {"uniprot": "P1", "diseases": [], "ligands": [], "go": [], "ppis": []}}}
    pharos.requests.post = lambda *a, **k: (calls.append(1), R())[1]
    assert pharos.fetch_target("NEW")["uniprot"] == "P2" and not calls
    assert pharos.fetch_target("OLD")["_schema"] == pharos.SCHEMA_VERSION and len(calls) == 1
print("cache versioning ok")
