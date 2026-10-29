import pandas as pd
from bioagent.clean.pubmed_tiers import apply_tiers

nodes = pd.DataFrame({"id": ["UniProtKB:P1", "MONDO:1", "MONDO:2", "MONDO:3", "MONDO:4"], "name": ["G", "d0", "d5", "d50", "d4"]})
def row(o, rule="disease_weak_only", v="prune"):
    return dict(subject="UniProtKB:P1", object=o, rule=rule, verdict=v, verdict_confidence=0.2, reason="weak", needs_review=True)
whole = pd.DataFrame([row("MONDO:1"), row("MONDO:2"), row("MONDO:3"), row("MONDO:4", "go_direct", "keep")])
counts = pd.DataFrame({"gene": ["G"] * 3, "disease": ["d0", "d5", "d50"], "count": [0, 5, 50]})
w = apply_tiers(whole, nodes, counts)
assert list(w.rule) == ["pubmed_none", "disease_weak_only", "pubmed_rescue", "go_direct"]
assert list(w.verdict) == ["prune", "prune", "keep", "keep"]
assert w.loc[1, "needs_review"] and not w.loc[0, "needs_review"]      # 1-9 stays flagged for the judge
assert 0.6 <= w.loc[2, "verdict_confidence"] <= 0.8 and w.loc[2, "verdict_confidence"] >= 0.4
assert w.pubmed_count.iloc[:3].tolist() == [0, 5, 50] and w.pubmed_count.isna().iloc[3]
print("ALL PASSED")
