"""Make a review sheet for a biologist: random edges from each pruning outcome, with the evidence we used, and empty columns
for their judgement. Output: data/processed/review_sheet.csv

  python scripts/review_sheet.py [N_PER_GROUP]
"""
import sys
import pandas as pd

n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
g = "data/processed/pharos_pruned_v3.whole"
nodes = pd.read_parquet(f"{g}.nodes.parquet", columns=["id", "name"]); name = dict(zip(nodes.id, nodes.name))
groups = ["llm_rescue", "llm_prune", "pubmed_rescue", "pubmed_none", "disease_obsolete", "go_unsupported", "ppi_crapome", "disease_open_targets"]
# row filter keeps memory small enough for a 4 GB interactive job
e = pd.read_parquet(f"{g}.edges.parquet", columns=["subject", "object", "evidence", "rule", "verdict", "verdict_confidence", "reason", "pubmed_count", "judge_p_real"],
                    filters=[("rule", "in", groups)])
parts = [e[e.rule == r].sample(n, random_state=0) for r in groups]
s = pd.concat(parts)
s["protein_or_gene"], s["target"] = s.subject.map(name), s.object.map(name)
s["our_verdict"] = s.verdict
s = s[["rule", "protein_or_gene", "target", "evidence", "our_verdict", "verdict_confidence", "pubmed_count", "judge_p_real", "reason"]]
s["reviewer_agrees (yes/no/unsure)"], s["reviewer_note"] = "", ""
s.to_csv("data/processed/review_sheet.csv", index=False)
print(s.groupby("rule").size())
