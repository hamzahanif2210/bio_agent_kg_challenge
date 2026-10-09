"""No-API tests: scripted LLM + fake Pharos fetch. Run: python tests/test_harness.py"""
import tempfile
import numpy as np
import pandas as pd
from bioagent.eval.split import pair_keys
from bioagent.ingest import harness, pharos, tools
from bioagent.ingest.harness import KGStore, run_agent

FAKE = {"uniprot": "P00001", "sym": "AAA", "name": "a", "tdl": "Tbio",
        "diseases": [{"name": "d1", "mondoID": "MONDO:1"}],
        "ligands": [{"ligid": "L1", "name": "lig", "isdrug": False}],
        "ppis": [{"type": "STRINGDB", "target": {"uniprot": "P00002"}}],
        "go": [{"goid": "GO:1", "term": "t", "type": "F"}]}
pharos.fetch_target = lambda x: FAKE if x == "AAA" else None


def scripted(steps):
    it = iter(steps)
    def llm(model, system, messages, tools_, max_tokens):
        return next(it)
    return llm


def tool_use(name, inp, i):
    return {"content": [{"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}],
            "stop_reason": "tool_use", "usage": {"input_tokens": 10, "output_tokens": 5}}


DONE = {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 5}}


def go(store, steps, **kw):
    with tempfile.TemporaryDirectory() as d:
        return run_agent("task", tools.TOOLS, store, scripted(steps), cache_dir=d, log_path=d + "/l.jsonl", **kw)


# 1. happy path: fetch, unknown target, unknown tool, then finish
s = KGStore()
r = go(s, [tool_use("pharos_get_target", {"target": "AAA"}, 1),
           tool_use("pharos_get_target", {"target": "ZZZ"}, 2),
           tool_use("nope", {}, 3), DONE])
assert r["stop"] == "done" and r["final_text"] == "ok", r
n, e = s.frames()
assert len(e) == 4 and e.confidence.between(0, 1).all() and e.source.eq("pharos").all(), e
assert set(e.columns) >= {"evidence", "method", "timestamp"}
print("happy path ok:", r["kg"])

# 2. leak guard: block the PPI pair; it must not enter the store
probe = pd.DataFrame({"subject": ["UniProtKB:P00001"], "object": ["UniProtKB:P00002"]})
s = KGStore(blocked_keys=pair_keys(probe))
go(s, [tool_use("pharos_get_target", {"target": "AAA"}, 1), DONE])
n, e = s.frames()
assert len(e) == 3 and s.stats["leak"] == 1 and not (e.evidence.str.contains("ppi")).any(), (e, s.stats)
print("leak guard ok:", s.stats)

# 3. validation: non-Biolink predicate and bad confidence are rejected
s = KGStore()
nodes = pd.DataFrame([{"id": "A", "category": "biolink:Protein", "name": "a", "source": "x"},
                      {"id": "B", "category": "biolink:Protein", "name": "b", "source": "x"}])
base = dict(subject="A", object="B", source="x", evidence="e", method="m", timestamp="t")
bad = pd.DataFrame([dict(base, predicate="related_to", confidence=1.0),
                    dict(base, predicate="biolink:related_to", confidence=2.0),
                    dict(base, predicate="biolink:related_to", confidence=0.5)])
s.add(nodes, bad)
assert s.stats["invalid"] == 2 and s.stats["added"] == 1, s.stats
print("validation ok:", s.stats)

# 4. token cap stops the loop
s = KGStore()
big = tool_use("kg_status", {}, 1)
big["usage"] = {"input_tokens": 500, "output_tokens": 0}
r = go(s, [big, DONE], max_total_tokens=100)
assert r["stop"] == "token_cap", r
print("token cap ok")

# 5. cache: second identical run makes no LLM calls
with tempfile.TemporaryDirectory() as d:
    calls = []
    def counting(*a):
        calls.append(1); return DONE
    run_agent("t", tools.TOOLS, KGStore(), counting, cache_dir=d)
    run_agent("t", tools.TOOLS, KGStore(), counting, cache_dir=d)
    assert len(calls) == 1, calls
print("cache ok")
print("ALL PASSED")
