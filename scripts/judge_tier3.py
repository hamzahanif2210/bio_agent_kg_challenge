"""Pruning v2 tier 3: LLM judge (with retrieved evidence) on weak disease edges with 1-9 PubMed co-mentions,
highest count first, up to --budget distinct protein-disease pairs. Parallel, resumable JSONL output.
Key is read from env LLM_API_KEY (never printed).

  python -u scripts/judge_tier3.py --model gpt-oss --budget 5000 --workers 6
"""
import argparse, json, os, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from bioagent.clean.judge import judge, mondo_definitions, pubmed_cooccurrence
from bioagent.ingest.harness import openai_llm

ap = argparse.ArgumentParser()
ap.add_argument("--base-url", default="https://ellm.nrp-nautilus.io/v1"); ap.add_argument("--model", default="gpt-oss")
ap.add_argument("--budget", type=int, default=5000); ap.add_argument("--workers", type=int, default=6)
ap.add_argument("--graph", default="data/processed/pharos_pruned_v2")
ap.add_argument("--src", default="/scratch/hamza95/bio_kg_data"); ap.add_argument("--out", default="data/processed/judge_tier3.jsonl")
a = ap.parse_args()

nodes = pd.read_parquet(f"{a.graph}.whole.nodes.parquet", columns=["id", "name"]); name = dict(zip(nodes.id, nodes.name))
e = pd.read_parquet(f"{a.graph}.whole.edges.parquet", columns=["subject", "object", "rule", "pubmed_count"])
e = e[(e.rule == "disease_weak_only") & e.pubmed_count.between(1, 9)].sort_values("pubmed_count", ascending=False, kind="stable")
e = e.drop_duplicates(["subject", "object"]).head(a.budget)
up = pd.read_csv(f"{a.src}/uniprot/human_reviewed.tsv", sep="\t", usecols=["Entry", "Function [CC]"])
func = {r[0]: str(r[1]).replace("FUNCTION: ", "") for r in up.itertuples(index=False) if isinstance(r[1], str)}
defs = mondo_definitions(f"{a.src}/mondo/mondo.obo")
done = set()
if os.path.exists(a.out):
    done = {(r["subject"], r["object"]) for r in map(json.loads, open(a.out))}
todo = [(s, o) for s, o in zip(e.subject, e.object) if (s, o) not in done]
print(f"{len(e)} selected, {len(done)} done, {len(todo)} to do", flush=True)
llm = openai_llm(a.base_url, os.environ["LLM_API_KEY"])

def run(p):
    s, o = p; t0 = time.time()
    try:
        pm = pubmed_cooccurrence(name[s], name[o])
        j = judge(llm, a.model, name[s], func.get(s.replace("UniProtKB:", "")), name[o], defs.get(o), pm)
        j["pubmed_count"] = pm["count"]
    except Exception as ex:
        j = {"verdict": "error", "confidence": 0.5, "p_real": 0.5, "reason": f"{type(ex).__name__}: {str(ex)[:100]}", "tokens": 0}
    return {"subject": s, "object": o, **j, "seconds": round(time.time() - t0, 1)}

with open(a.out, "a") as f, ThreadPoolExecutor(a.workers) as ex:
    for i, r in enumerate(ex.map(run, todo)):
        f.write(json.dumps(r) + "\n"); f.flush()
        if i % 100 == 0: print(f"{i}/{len(todo)}", flush=True)
