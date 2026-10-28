"""Tier 1/2 of pruning v2: PubMed co-mention count for every weak-pruned protein-disease edge (no LLM).
Count-only queries, appended to a JSONL so a restarted job resumes. NCBI key is read from env NCBI_API_KEY.

  python -u scripts/pubmed_counts.py --out data/processed/pubmed_counts.jsonl [--limit N]
"""
import argparse, json, os, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from bioagent.clean.judge import EUTILS, _get

ap = argparse.ArgumentParser()
ap.add_argument("--graph", default="data/processed/pharos_pruned.whole")
ap.add_argument("--out", default="data/processed/pubmed_counts.jsonl")
ap.add_argument("--limit", type=int)
ap.add_argument("--workers", type=int, default=5)
a = ap.parse_args()
pause = 0.12 if os.environ.get("NCBI_API_KEY") else 0.4

nodes = pd.read_parquet(f"{a.graph}.nodes.parquet", columns=["id", "name"])
name = dict(zip(nodes.id, nodes.name))
e = pd.read_parquet(f"{a.graph}.edges.parquet", columns=["subject", "object", "evidence", "rule"])
e = e[(e.evidence == "pharos:disease_association") & (e.rule == "disease_weak_only")]
pairs = sorted({(name[s], name[o]) for s, o in zip(e.subject, e.object)})
if a.limit: pairs = pairs[:a.limit]
done = set()
if os.path.exists(a.out):
    done = {(r["gene"], r["disease"]) for r in map(json.loads, open(a.out))}
todo = [p for p in pairs if p not in done]
print(f"{len(pairs)} pairs, {len(done)} done, {len(todo)} to do", flush=True)
def count(p):
    g, d = p
    try:
        es = _get(f"{EUTILS}/esearch.fcgi", {"db": "pubmed", "term": f'"{g}"[tiab] AND "{d}"[tiab]', "retmode": "json", "retmax": 0})["esearchresult"]
        n = int(es.get("count", 0))
    except Exception as ex:
        print(f"error {g}/{d}: {type(ex).__name__}", flush=True); n = None
    time.sleep(pause)
    return g, d, n

# requests take ~0.5 s each, so a few threads are needed to approach NCBI's 10 requests/s limit
with open(a.out, "a") as f, ThreadPoolExecutor(a.workers) as ex:
    for i, (g, d, n) in enumerate(ex.map(count, todo)):
        if n is not None:
            f.write(json.dumps({"gene": g, "disease": d, "count": n}) + "\n")
        if i % 2000 == 0:
            f.flush(); print(f"{i}/{len(todo)}", flush=True)
