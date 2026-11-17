import json, threading, urllib.request, urllib.parse, pandas as pd
from http.server import HTTPServer
from bioagent.qa.serve import make_handler

nodes = pd.DataFrame({"id": ["P1", "D1", "P2"], "name": ["EGFR", "lung cancer", "GRB2"], "category": ["biolink:Protein", "biolink:Disease", "biolink:Protein"]})
def e(s, o, v, c):
    return dict(subject=s, predicate="biolink:associated_with", object=o, evidence="x", verdict=v, verdict_confidence=c, reason="r", confidence=c, source="s")
edges = pd.DataFrame([e("P1", "D1", "keep", 0.9), e("P2", "D1", "prune", 0.2), e("P1", "P2", "keep", 0.5)])
srv = HTTPServer(("127.0.0.1", 0), make_handler((nodes, edges), "unused", None, "m"))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}"
get = lambda path: urllib.request.urlopen(base + path).read().decode()
post = lambda path, data, ctype: urllib.request.urlopen(urllib.request.Request(base + path, data=data.encode(), headers={"Content-Type": ctype})).read().decode()

pic = get("/pic/0") if "<iframe" in get("/?q=EGFR") else ""
assert 'type="range"' in pic and "cut-off" in pic and '"vc": 0.9' in pic and '"keep0": true' in pic      # the slider is in the picture
st = json.loads(get("/api/stats?threshold=0.6"))
assert st["kept"] == 2 and st["kept_at_threshold"] == 1 and st["pruned_at_threshold"] == 2

csv = "subject,object,predicate,score,pmid\nEGFR,GRB2,physically_interacts_with,0.7,12345678\nNEWGENE,lung cancer,,0.1,\n"
rep = json.loads(post("/api/upload", csv, "text/csv"))
assert rep["edges_added"] == 2 and rep["kept"] == 1 and rep["pruned"] == 1 and rep["graph_id"]
g = rep["graph_id"]
assert json.loads(get(f"/api/stats?g={g}"))["edges"] == 5 and json.loads(get("/api/stats"))["edges"] == 3     # shared graph unchanged
assert "NEWGENE" in get(f"/api/ask?g={g}&q=NEWGENE") and "no matching node" in get("/api/ask?q=NEWGENE")
page = post("/upload", "csv=" + urllib.parse.quote(csv), "application/x-www-form-urlencoded")
assert "2 edges added" in page and "Look at EGFR" in page
bad = urllib.request.Request(base + "/api/upload", data=b"x,y\n1,2\n", headers={"Content-Type": "text/csv"})
try:
    urllib.request.urlopen(bad); raise SystemExit("should fail")
except urllib.error.HTTPError as ex:
    assert ex.code == 400
ask = json.loads(get("/api/ask?q=EGFR,lung+cancer&hops=3&minconf=0.4"))
assert "path(s)" in ask["answer"] and "weakest link" in ask["answer"]
srv.shutdown(); print("ALL PASSED")
