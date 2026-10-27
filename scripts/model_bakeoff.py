"""Compare LLMs on small tool-use tasks with our harness. The key is read from a file or env var
and never printed.

  python scripts/model_bakeoff.py --base-url https://ellm.nrp-nautilus.io/v1 --key-file PATH \
      --models glm-5 kimi gpt-oss --out runs/bakeoff_nrp.json
"""
import argparse, json, os, tempfile, time
from bioagent.ingest.harness import KGStore, openai_llm, run_agent
from bioagent.ingest.run import SYSTEM
from bioagent.ingest.tools import TOOLS

TASKS = {
    "two_targets": ("Add the human proteins EGFR and TP53 from Pharos to the graph, then check the graph status and summarize.",
                    {"EGFR", "TP53"}, None),
    "three_targets": ("Build a small graph about lung cancer driver genes: fetch EGFR, KRAS and BRAF, then report the status.",
                      {"EGFR", "KRAS", "BRAF"}, None),
    "error_recovery": ("Fetch ZZZNOTAGENE and EGFR from Pharos. Tell me exactly which one could not be found.",
                       {"EGFR"}, "ZZZNOTAGENE"),
}


def score(log_path, want, must_mention, res):
    calls, errors = [], 0
    for line in open(log_path):
        for c in json.loads(line)["tool_calls"]:
            calls.append(c)
            errors += bool(c["error"])
    fetched = {str(c["input"].get("target", "")).upper() for c in calls if c["name"] == "pharos_get_target"}
    got = want <= fetched
    ok = got and res["stop"] == "done" and res["kg"]["edges"] > 0
    if must_mention:
        ok = ok and must_mention.lower() in res["final_text"].lower()
    return {"ok": bool(ok), "fetched": sorted(fetched), "tool_calls": len(calls), "tool_errors": errors,
            "edges": res["kg"]["edges"], "stop": res["stop"], "tokens": res["tokens"], "final_text": res["final_text"][:300]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--key-file")
    ap.add_argument("--key-env", default="LLM_API_KEY")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    key = open(a.key_file).read().strip() if a.key_file else os.environ[a.key_env]
    llm = openai_llm(a.base_url, key)
    results = []
    for model in a.models:
        for tname, (task, want, mention) in TASKS.items():
            t0 = time.time()
            with tempfile.TemporaryDirectory() as d:
                log = f"{d}/log.jsonl"
                try:
                    res = run_agent(task, TOOLS, KGStore(), llm, model=model, system=SYSTEM, max_steps=8,
                                    max_total_tokens=40000, cache_dir=f"{d}/c", log_path=log)
                    r = score(log, want, mention, res)
                except Exception as e:  # record, never crash the comparison
                    r = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
            r.update(model=model, task=tname, seconds=round(time.time() - t0, 1))
            results.append(r)
            print(f"{model:18s} {tname:15s} ok={r['ok']!s:5s} calls={r.get('tool_calls','-')} tok={r.get('tokens','-')} "
                  f"{r['seconds']}s {r.get('error','')}", flush=True)
            json.dump(results, open(a.out, "w"), indent=1)
