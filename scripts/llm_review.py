"""Blind LLM review of the pruning review sheet. The model sees only the two entities and the kind of claim, never our verdict
or reason, and answers from its own knowledge. Key from env LLM_API_KEY (never printed).

  python -u scripts/llm_review.py --model qwen3 --out runs/review_qwen3.json
"""
import argparse, json, os, re, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import requests
from bioagent.ingest.harness import _http_post, openai_llm

ap = argparse.ArgumentParser()
ap.add_argument("--base-url", default="https://ellm.nrp-nautilus.io/v1"); ap.add_argument("--model", required=True)
ap.add_argument("--sheet", default="data/processed/review_sheet.csv"); ap.add_argument("--out", required=True)
ap.add_argument("--effort", default="high"); ap.add_argument("--workers", type=int, default=4)
a = ap.parse_args()

SYSTEM = ("You are an expert biologist reviewing claims from a biomedical knowledge graph. Judge each claim from your own knowledge. "
          'Reply with JSON only: {"answer": "plausible" | "implausible" | "unsure", "confidence": 0 to 1 (your confidence in that answer), '
          '"reason": "one sentence"}.')


def claim(r):
    ev, g, t = r["evidence"], r["protein_or_gene"], r["target"]
    if ev == "pharos:disease_association":
        return f"Is the human gene/protein {g} associated with the disease or phenotype '{t}' (e.g. causal variants, risk, or disease mechanism)?"
    if ev == "pharos:go":
        return f"Is the human protein {g} annotated with, or does it plausibly have, the Gene Ontology term '{t}'?"
    if ev.startswith("pharos:ppi"):
        return f"Do the human proteins {g} and {t} physically interact in cells?"
    return f"Is there a real biological relationship between {g} and {t}?"


url = a.base_url.rstrip("/") + "/chat/completions"
headers = {"Authorization": f"Bearer {os.environ['LLM_API_KEY']}", "Content-Type": "application/json"}
state = {"effort": True}


def post(body):
    if state["effort"]:
        try:
            return _http_post(url, headers, {**body, "reasoning_effort": a.effort})
        except requests.HTTPError as ex:
            if ex.response is None or ex.response.status_code not in (400, 422):
                raise
            state["effort"] = False; print("model rejects reasoning_effort; continuing without it", flush=True)
    return _http_post(url, headers, body)


llm = openai_llm(a.base_url, os.environ["LLM_API_KEY"], post=post)


def run(item):
    i, r = item
    t0, budget, tokens = time.time(), 4000, 0
    while True:
        try:
            resp = llm(a.model, SYSTEM, [{"role": "user", "content": claim(r)}], [], budget)
        except Exception as ex:
            return {"row": i, "answer": "error", "reason": f"{type(ex).__name__}: {str(ex)[:100]}", "seconds": round(time.time() - t0, 1)}
        text = " ".join(b["text"] for b in resp["content"] if b["type"] == "text")
        u = resp.get("usage") or {}
        tokens += u.get("input_tokens", 0) + u.get("output_tokens", 0)
        if (resp.get("stop_reason") == "max_tokens" or not text.strip()) and budget < 16000:
            budget *= 2; continue
        break
    m = re.search(r"\{.*\}", text, re.S)
    try:
        d = json.loads(m.group(0)); ans = str(d.get("answer", "unsure")).lower()
        ans = ans if ans in ("plausible", "implausible", "unsure") else "unsure"
        return {"row": i, "answer": ans, "confidence": d.get("confidence"), "reason": str(d.get("reason", ""))[:300], "tokens": tokens, "seconds": round(time.time() - t0, 1)}
    except Exception:
        return {"row": i, "answer": "unparseable", "reason": text[:150], "tokens": tokens, "seconds": round(time.time() - t0, 1)}


sheet = pd.read_csv(a.sheet)


def run_and_save(item):
    r = run(item)
    with open(a.out + ".partial.jsonl", "a") as f:        # saved as they arrive, so a timeout loses nothing
        f.write(json.dumps(r) + "\n")
    print(f"row {r['row']} {r['answer']} {r['seconds']}s", flush=True)
    return r


with ThreadPoolExecutor(a.workers) as ex:
    res = list(ex.map(run_and_save, list(sheet.iterrows())))
json.dump({"model": a.model, "effort": a.effort, "results": res}, open(a.out, "w"), indent=1)
d = pd.DataFrame(res); d["rule"] = sheet.rule.to_numpy(); d["ours"] = sheet.our_verdict.to_numpy()
print(pd.crosstab(d.rule, d.answer).to_string())
print("seconds mean", d.seconds.mean().round(1), "tokens mean", d.tokens.mean().round(0) if "tokens" in d else None)
