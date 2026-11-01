import threading, urllib.request, urllib.parse, pandas as pd
from http.server import HTTPServer
from bioagent.qa.serve import make_handler, entities_from

assert entities_from("EGFR, non-small cell lung carcinoma") == ["EGFR", "non-small cell lung carcinoma"]
nodes = pd.DataFrame({"id": ["P1", "D1"], "name": ["EGFR", "lung cancer"], "category": ["biolink:Protein", "biolink:Disease"]})
edges = pd.DataFrame({"subject": ["P1"], "object": ["D1"], "predicate": ["biolink:associated_with"], "evidence": ["x"], "verdict": ["keep"],
                      "verdict_confidence": [0.9], "reason": ["r"], "confidence": [0.9], "source": ["s"]})
srv = HTTPServer(("127.0.0.1", 0), make_handler((nodes, edges), "unused", None, "m"))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}"
page = urllib.request.urlopen(base + "/?" + urllib.parse.urlencode({"q": "EGFR"})).read().decode()
assert "EGFR" in page and "<iframe" in page
pic = urllib.request.urlopen(base + "/pic/0").read().decode()
assert "vis-network" in pic and "lung cancer" in pic
evil = urllib.request.urlopen(base + "/?" + urllib.parse.urlencode({"q": "<script>alert(1)</script>"})).read().decode()
assert "<script>alert(1)" not in evil
srv.shutdown(); print("ALL PASSED")
