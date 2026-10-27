"""Judge tests with a fake LLM (no network). Run: python tests/test_judge.py"""
import json
from bioagent.clean.judge import build_prompt, judge, parse_verdict, SYSTEM

p = build_prompt("EGFR", "Receptor tyrosine kinase", "glioblastoma", "A malignant brain tumor.", {"count": 2862, "titles": ["EGFR in glioblastoma"]})
assert "EGFR" in p and "2862" in p and "- EGFR in glioblastoma" in p
for banned in ("keep", "prune", "Open Targets", "Expression Atlas", "pharos", "rule"):   # no label leakage into the prompt
    assert banned not in p, banned
assert "ONLY the evidence" in SYSTEM and "uncertain" in SYSTEM

assert parse_verdict('Sure: {"verdict": "keep", "confidence": 0.9, "evidence_used": ["pubmed_count"], "reason": "many papers"} thanks')["verdict"] == "keep"
assert parse_verdict("no json here")["verdict"] == "uncertain"
assert parse_verdict('{"verdict": "maybe"}')["verdict"] == "uncertain"
assert parse_verdict('{"verdict": "prune", "confidence": 7}')["confidence"] == 1.0
assert parse_verdict('{"verdict": "prune", "confidence": 0.9}')["p_real"] == 0.1 and parse_verdict('{"verdict": "keep", "confidence": 0.9}')["p_real"] == 0.9
assert parse_verdict('{"verdict": "uncertain", "confidence": 0.9}')["p_real"] == 0.5

seen = []
def fake(model, system, messages, tools, max_tokens):
    seen.append((tools, messages[0]["role"]))
    return {"content": [{"type": "text", "text": json.dumps({"verdict": "prune", "confidence": 0.1, "reason": "x"})}],
            "usage": {"input_tokens": 100, "output_tokens": 20}}
r = judge(fake, "m", "G", None, "D", None, {"count": 0, "titles": []})
assert r["verdict"] == "prune" and r["tokens"] == 120 and seen[0][0] == []
# a cut-off / empty reply is retried with a doubled budget
budgets = []
def flaky(model, system, messages, tools, max_tokens):
    budgets.append(max_tokens)
    if len(budgets) == 1:
        return {"content": [], "stop_reason": "max_tokens", "usage": {"input_tokens": 50, "output_tokens": 300}}
    return {"content": [{"type": "text", "text": '{"verdict": "keep", "confidence": 0.8, "reason": "ok"}'}],
            "stop_reason": "end_turn", "usage": {"input_tokens": 50, "output_tokens": 40}}
r = judge(flaky, "m", "G", None, "D", None, {"count": 1, "titles": []}, max_tokens=500)
assert r["verdict"] == "keep" and budgets == [500, 1000] and r["tokens"] == 440, (r, budgets)

# connection errors are retried by the HTTP helper
import requests as rq
from bioagent.ingest import harness
n = {"c": 0}
class Resp:
    status_code = 200; headers = {}
    def raise_for_status(self): pass
    def json(self): return {"ok": True}
def post(*a, **k):
    n["c"] += 1
    if n["c"] < 3: raise rq.ConnectionError("dropped")
    return Resp()
orig_post, orig_sleep = rq.post, harness.time.sleep
rq.post, harness.time.sleep = post, lambda s: None
assert harness._http_post("http://x", {}, {}) == {"ok": True} and n["c"] == 3
rq.post, harness.time.sleep = orig_post, orig_sleep
print("ALL PASSED")
