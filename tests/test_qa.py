import pandas as pd
from bioagent.qa.ask import Index, answer, extract_entities, neighbours

nodes = pd.DataFrame({"id": ["UniProtKB:P1", "UniProtKB:P2", "MONDO:1", "MONDO:2"],
                      "name": ["EGFR", "GRB2", "lung cancer", "non-small cell lung carcinoma"],
                      "category": ["biolink:Protein"] * 2 + ["biolink:Disease"] * 2})
def e(s, o, ev, v="keep", c=0.9):
    return dict(subject=s, predicate="biolink:related_to", object=o, source="pharos", evidence=ev, confidence=c, method="m",
                timestamp="t", attributes="{}", verdict=v, verdict_confidence=c, reason="r", rule="x", needs_review=False)
edges = pd.DataFrame([e("UniProtKB:P1", "MONDO:2", "pharos:disease_association"), e("UniProtKB:P1", "UniProtKB:P2", "pharos:ppi:X"),
                      e("UniProtKB:P2", "MONDO:2", "pharos:disease_association", "prune", 0.1)])
fake = lambda model, system, msgs, tools, mt: {"content": [{"type": "text", "text": 'sure {"entities": ["EGFR", " lung cancer "]}'}]}
assert extract_entities(fake, "m", "q") == ["EGFR", "lung cancer"]
bad = lambda *a: {"content": [{"type": "text", "text": "no json"}]}
assert extract_entities(bad, "m", "q") == []
idx = Index(nodes, edges)
assert idx.find("egfr")[0] == "exact" and idx.find("carcinoma")[1][0]["id"] == "MONDO:2"
assert idx.find("zzz")[1] == []
nb = neighbours(edges, nodes, "UniProtKB:P2")                  # the pruned edge must not appear
assert "biolink:Disease" not in nb and nb["biolink:Protein"][0]["id"] == "UniProtKB:P1"
text, sub = answer("x", ["EGFR", "carcinoma"], graph=(nodes, edges))   # partial match -> still resolves
assert "non-small cell lung carcinoma" in text and "Direct connection" in text
text, sub = answer("x", ["EGFR"], graph=(nodes, edges)); assert "GRB2" in text
text, _ = answer("x", ["nothing here"], graph=(nodes, edges)); assert "could not find" in text
print("ALL PASSED")
