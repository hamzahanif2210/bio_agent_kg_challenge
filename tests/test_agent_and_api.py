import json, sys, tempfile, threading, urllib.request
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import compile_agent
from bioagent.provenance.explain import load
from bioagent.qa.serve import make_handler

# the one SKILL.md is valid and installs for every harness
assert compile_agent.check((compile_agent.SRC / "SKILL.md").read_text()) == "bioagent-kg"
tmp = Path(tempfile.mkdtemp())
for t in ("pi", "openclaw", "nemoclaw", "hermes"):
    compile_agent.DEST[t] = (tmp / t, tmp / t)
    compile_agent.main([t])
    assert (tmp / t / "bioagent-kg" / "SKILL.md").exists()

# JSON endpoints on the sample graph
prefix = str(ROOT / "sample" / "sample.whole")
srv = HTTPServer(("127.0.0.1", 0), make_handler(load(prefix, standard=True), prefix, None, "x"))
threading.Thread(target=srv.serve_forever, daemon=True).start()
get = lambda p: json.load(urllib.request.urlopen(f"http://127.0.0.1:{srv.server_port}{p}"))
assert get("/healthz")["ok"]
st = get("/api/stats"); assert st["kept"] + st["pruned"] == st["edges"]
assert get("/api/node?q=EGFR")["id"] == "UniProtKB:P00533"
assert "BRCA1" in get("/api/ask?q=BRCA1")["answer"]
srv.shutdown()
print("ok")
