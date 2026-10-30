"""Pruning v2, tier 3: fold the LLM judge's verdicts into the graph.

  python -m bioagent.clean.apply_judge data/processed/pharos_pruned_v2 data/processed/judge_tier3.jsonl data/processed/pharos_pruned_v3 gpt-oss

Only edges still on rule `disease_weak_only` (1-9 PubMed co-mentions, pruned by the v1 rules) can change:
  judge keep, p_real >= RESCUE_P   flipped to keep           (rule llm_rescue)
  judge prune                      stays pruned, reason cites the judge (rule llm_prune)
  anything else (uncertain, low-confidence keep, error)   unchanged, still flagged needs_review
Adds columns judge_model and judge_p_real (empty where the judge did not run).
"""
import json
import sys

import numpy as np
import pandas as pd

RESCUE_P = 0.8


def apply_judge(whole, judged, model):
    w = whole.copy()
    w["judge_model"], w["judge_p_real"] = None, np.nan
    j = judged.drop_duplicates(["subject", "object"], keep="last").set_index(["subject", "object"])
    idx = w.index[w.rule == "disease_weak_only"]
    keys = pd.MultiIndex.from_arrays([w.subject[idx], w.object[idx]])
    hit = keys.isin(j.index)
    idx, keys = idx[hit], keys[hit]
    r = j.loc[keys]
    verdict, p, reason = r.verdict.to_numpy(), r.p_real.to_numpy(dtype=float), r.reason.astype(str).to_numpy()
    w.loc[idx, "judge_model"], w.loc[idx, "judge_p_real"] = model, p
    resc = (verdict == "keep") & (p >= RESCUE_P)
    prune = verdict == "prune"
    for sel, rule, v in ((resc, "llm_rescue", "keep"), (prune, "llm_prune", "prune")):
        i = idx[sel]
        w.loc[i, "verdict"], w.loc[i, "rule"], w.loc[i, "needs_review"] = v, rule, False
        w.loc[i, "reason"] = [f"LLM judge ({model}) with PubMed/UniProt/MONDO evidence says {v}: {x}" for x in reason[sel]]
    w.loc[idx[resc], "verdict_confidence"] = np.round(p[resc], 3)
    w.loc[idx[prune], "verdict_confidence"] = np.round(1 - p[prune], 3)   # confidence the edge is correct
    return w


if __name__ == "__main__":
    graph, judged_path, out, model = sys.argv[1:5]
    nodes = pd.read_parquet(f"{graph}.whole.nodes.parquet")
    whole = pd.read_parquet(f"{graph}.whole.edges.parquet")
    w = apply_judge(whole, pd.read_json(judged_path, lines=True), model)
    kept = w[w.verdict == "keep"]
    used = set(kept.subject) | set(kept.object)
    w.to_parquet(f"{out}.whole.edges.parquet"); nodes.to_parquet(f"{out}.whole.nodes.parquet")
    kept.to_parquet(f"{out}.pruned.edges.parquet"); nodes[nodes.id.isin(used)].to_parquet(f"{out}.pruned.nodes.parquet")
    summ = w.groupby(["evidence", "rule", "verdict"]).agg(edges=("subject", "size"), needs_review=("needs_review", "sum")).reset_index()
    print(summ[summ.evidence == "pharos:disease_association"].to_string(index=False))
    json.dump({"whole_edges": len(w), "kept_edges": len(kept), "pruned_edges": len(w) - len(kept),
               "by_rule": summ.to_dict("records")}, open(f"{out}.summary.json", "w"), indent=1, default=int)
    print(f"whole: {len(w)}; kept: {len(kept)}; pruned: {len(w)-len(kept)}")
    w[w.rule == "llm_rescue"].sample(min(20, int((w.rule == "llm_rescue").sum())), random_state=0).to_csv(f"{out}.spotcheck.csv", index=False)
