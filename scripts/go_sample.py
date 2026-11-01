"""Review sheet for the GO rule: 100 'go_unsupported' edges (we prune) and 50 'go_direct' edges (UniProt annotates them: known true).
The controls show how lenient each reviewer is on GO claims.  Output: data/processed/review_go.csv"""
import pandas as pd
g = "data/processed/pharos_pruned_v3.whole"
nodes = pd.read_parquet(f"{g}.nodes.parquet", columns=["id", "name"]); name = dict(zip(nodes.id, nodes.name))
e = pd.read_parquet(f"{g}.edges.parquet", columns=["subject", "object", "evidence", "rule", "verdict", "verdict_confidence", "reason"],
                    filters=[("rule", "in", ["go_unsupported", "go_direct"])])
s = pd.concat([e[e.rule == "go_unsupported"].sample(100, random_state=1), e[e.rule == "go_direct"].sample(50, random_state=1)])
s["protein_or_gene"], s["target"], s["our_verdict"] = s.subject.map(name), s.object.map(name), s.verdict
s[["rule", "protein_or_gene", "target", "evidence", "our_verdict", "verdict_confidence", "reason"]].sample(frac=1, random_state=0).to_csv("data/processed/review_go.csv", index=False)
print(s.rule.value_counts())
