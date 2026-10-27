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

seen = []
def fake(model, system, messages, tools, max_tokens):
    seen.append((tools, messages[0]["role"]))
    return {"content": [{"type": "text", "text": json.dumps({"verdict": "prune", "confidence": 0.1, "reason": "x"})}],
            "usage": {"input_tokens": 100, "output_tokens": 20}}
r = judge(fake, "m", "G", None, "D", None, {"count": 0, "titles": []})
assert r["verdict"] == "prune" and r["tokens"] == 120 and seen[0][0] == []
print("ALL PASSED")
