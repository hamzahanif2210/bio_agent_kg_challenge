"""Pruning v2 pilot. (1) Can the LLM+retrieval judge separate likely-true edges from random pairs?
(2) What does it say about the weak edges our rules prune? Key is read from env LLM_API_KEY (never printed).

  python scripts/judge_sample.py --base-url https://ellm.nrp-nautilus.io/v1 --model kimi --n-silver 40 --n-weak 100
"""
import argparse, json, os, random, time
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from bioagent.clean.judge import judge, mondo_definitions, pubmed_cooccurrence
from bioagent.ingest.harness import openai_llm

ap = argparse.ArgumentParser()
ap.add_argument("--base-url", required=True); ap.add_argument("--model", default="kimi")
ap.add_argument("--n-silver", type=int, default=40); ap.add_argument("--n-weak", type=int, default=100)
ap.add_argument("--graph", default="data/processed/pharos_pruned.whole")
ap.add_argument("--src", default="/scratch/hamza95/bio_kg_data"); ap.add_argument("--out", default="runs/judge_v2.json")
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()
rng = random.Random(a.seed)

nodes = pd.read_parquet(f"{a.graph}.nodes.parquet", columns=["id", "name", "category"])
e = pd.read_parquet(f"{a.graph}.edges.parquet", columns=["subject", "object", "evidence", "rule", "verdict", "verdict_confidence"])
e = e[e.evidence == "pharos:disease_association"]
name = dict(zip(nodes.id, nodes.name))
up = pd.read_csv(f"{a.src}/uniprot/human_reviewed.tsv", sep="\t", usecols=["Entry", "Function [CC]"])
func = {r[0]: str(r[1]).replace("FUNCTION: ", "") for r in up.itertuples(index=False) if isinstance(r[1], str)}
defs = mondo_definitions(f"{a.src}/mondo/mondo.obo")

pos = e[(e.rule == "disease_open_targets") & (e.verdict_confidence >= 0.8)].sample(a.n_silver, random_state=a.seed)
all_pairs = set(zip(e.subject, e.object)); dis = list(nodes[nodes.category == "biolink:Disease"].id)
neg = []
for s in pos.subject:                      # same proteins, paired with a random disease they have no edge to
    while True:
        d = rng.choice(dis)
        if (s, d) not in all_pairs: neg.append((s, d)); break
weak = e[e.rule == "disease_weak_only"].sample(a.n_weak, random_state=a.seed)
items = ([("silver_true", s, o) for s, o in zip(pos.subject, pos.object)] + [("silver_false", s, o) for s, o in neg]
         + [("weak_pruned_by_rules", s, o) for s, o in zip(weak.subject, weak.object)])
rng.shuffle(items)
llm = openai_llm(a.base_url, os.environ["LLM_API_KEY"])

rec = []
for i, (grp, s, o) in enumerate(items):
    acc = s.replace("UniProtKB:", ""); gene, dname = name[s], name[o]
    pm = pubmed_cooccurrence(gene, dname)
    t0 = time.time()
    try:
        j = judge(llm, a.model, gene, func.get(acc), dname, defs.get(o), pm)
    except Exception as ex:
        j = {"verdict": "error", "confidence": 0.5, "reason": f"{type(ex).__name__}: {str(ex)[:100]}", "tokens": 0, "evidence_used": []}
    rec.append({"group": grp, "protein": gene, "disease": dname, "pubmed_count": pm["count"], **j, "seconds": round(time.time() - t0, 1)})
    if i % 20 == 0: print(f"{i}/{len(items)} done", flush=True)
    json.dump(rec, open(a.out, "w"), indent=1)

df = pd.DataFrame(rec)
print("\n=== verdicts by group"); print(pd.crosstab(df.group, df.verdict).to_string())
sil = df[df.group.isin(["silver_true", "silver_false"])].copy(); sil["y"] = (sil.group == "silver_true").astype(int)
ok = sil[sil.verdict.isin(["keep", "prune"])]
print(f"\nsilver set: {len(sil)} edges ({sil.y.sum()} likely-true, {len(sil)-sil.y.sum()} random pairs)")
print(f"  decided (not uncertain/error): {len(ok)}; accuracy when decided: {((ok.verdict == 'keep') == ok.y.astype(bool)).mean():.3f}")
print(f"  accuracy counting uncertain as wrong: {((sil.verdict == 'keep') == sil.y.astype(bool)).mean():.3f}")
print(f"  AUROC of judge p_real: {roc_auc_score(sil.y, sil.p_real):.3f} | AUROC of log(PubMed count) alone: {roc_auc_score(sil.y, np.log1p(sil.pubmed_count)):.3f}")
w = df[df.group == "weak_pruned_by_rules"]
print(f"\nweak edges the rules prune (n={len(w)}): judge keep {np.mean(w.verdict=='keep'):.2f}, prune {np.mean(w.verdict=='prune'):.2f}, "
      f"uncertain/error {np.mean(~w.verdict.isin(['keep','prune'])):.2f}; mean PubMed co-mentions {w.pubmed_count.mean():.0f}, zero-mention share {np.mean(w.pubmed_count==0):.2f}")
print(f"tokens total {int(df.tokens.sum())}, mean {df.tokens.mean():.0f}/edge; seconds mean {df.seconds.mean():.1f}/edge")
