import pandas as pd
from bioagent.clean.apply_judge import apply_judge

def row(o, rule="disease_weak_only"):
    return dict(subject="P1", object=o, rule=rule, verdict="prune", verdict_confidence=0.2, reason="weak", needs_review=True)
whole = pd.DataFrame([row("D1"), row("D2"), row("D3"), row("D4"), row("D5"), row("D1", "go_direct")])
judged = pd.DataFrame({"subject": ["P1"] * 5, "object": ["D1", "D2", "D3", "D4", "D1"], "verdict": ["keep", "keep", "prune", "uncertain", "keep"],
                       "p_real": [0.95, 0.7, 0.05, 0.5, 0.99], "reason": ["a", "b", "c", "d", "later duplicate"]})
w = apply_judge(whole, judged, "m")
assert list(w.verdict) == ["keep", "prune", "prune", "prune", "prune", "prune"]
assert list(w.rule) == ["llm_rescue", "disease_weak_only", "llm_prune", "disease_weak_only", "disease_weak_only", "go_direct"]
assert w.loc[0, "verdict_confidence"] == 0.99 and "later duplicate" in w.loc[0, "reason"]      # last judgment per pair wins
assert w.loc[2, "verdict_confidence"] == 0.95 and not w.loc[2, "needs_review"]              # pruned with confidence 1 - p_real
assert w.loc[1, "needs_review"] and w.loc[4, "judge_model"] is None and w.loc[5, "judge_model"] is None   # unjudged / other rules untouched
print("ALL PASSED")
