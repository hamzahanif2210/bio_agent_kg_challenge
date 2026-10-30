"""Pruning rule tests on tiny synthetic data. Run: python tests/test_prune.py"""
import json
import pandas as pd
from bioagent.clean.prune import Resources, prune_edges

def E(s, o, ev, conf=float("nan"), attrs=None):
    return dict(subject=s, predicate="biolink:related_to", object=o, source="pharos", evidence=ev, confidence=conf,
                timestamp="t", method="m", attributes=json.dumps(attrs or {}))

res = Resources(
    go_obsolete={"GO:OLD": "GO:NEW"},
    go_parents={"GO:CHILD": {"GO:PARENT"}, "GO:PARENT": {"GO:ROOT"}},
    mondo_obsolete={"MONDO:OLD": None},
    uniprot_go={"P1": {"GO:CHILD"}, "P2": set()},
    ot=pd.DataFrame({"uniprot": ["P1"], "mondo": ["MONDO:OT"], "score": [0.8]}),
)
rows = {
 "ppi_hi":      E("UniProtKB:P1", "UniProtKB:P2", "pharos:ppi:STRINGDB", 0.9),
 "ppi_lo":      E("UniProtKB:P1", "UniProtKB:P3", "pharos:ppi:STRINGDB", 0.2),
 "ppi_rev_a":   E("UniProtKB:P4", "UniProtKB:P5", "pharos:ppi:STRINGDB", 0.1),
 "ppi_rev_b":   E("UniProtKB:P5", "UniProtKB:P4", "pharos:ppi:STRINGDB", 0.9),
 "ppi_bioplex": E("UniProtKB:P1", "UniProtKB:P6", "pharos:ppi:BioPlex"),
 "ppi_multi":   E("UniProtKB:P1", "UniProtKB:P7", "pharos:ppi:BioPlex,STRINGDB", 0.2),
 "dis_obs":     E("UniProtKB:P1", "MONDO:OLD", "pharos:disease_association", attrs={"assoc_types": ["CTD", "Monarch"]}),
 "dis_ot":      E("UniProtKB:P1", "MONDO:OT", "pharos:disease_association", attrs={"assoc_types": ["Expression Atlas"]}),
 "dis_multi":   E("UniProtKB:P1", "MONDO:A", "pharos:disease_association", attrs={"assoc_types": ["CTD", "Monarch", "DisGeNET"]}),
 "dis_scored":  E("UniProtKB:P1", "MONDO:B", "pharos:disease_association", 0.3, {"assoc_types": ["DisGeNET"]}),
 "dis_curated": E("UniProtKB:P1", "MONDO:C", "pharos:disease_association", attrs={"assoc_types": ["CTD"]}),
 "dis_weak":    E("UniProtKB:P1", "MONDO:D", "pharos:disease_association", attrs={"assoc_types": ["Expression Atlas"]}),
 "go_obs":      E("UniProtKB:P1", "GO:OLD", "pharos:go"),
 "go_direct":   E("UniProtKB:P1", "GO:CHILD", "pharos:go"),
 "go_inherit":  E("UniProtKB:P1", "GO:ROOT", "pharos:go"),
 "go_unsupp":   E("UniProtKB:P1", "GO:OTHER", "pharos:go"),
 "go_unchk":    E("UniProtKB:P9", "GO:CHILD", "pharos:go"),
 "ligand":      E("PHAROS.LIGAND:L1", "UniProtKB:P1", "pharos:ligand_activity"),
}
edges = pd.DataFrame(list(rows.values()), index=list(rows))
v = prune_edges(edges, res)
exp = {"ppi_hi": ("keep", "ppi_score"), "ppi_lo": ("prune", "ppi_score"), "ppi_rev_a": ("keep", "ppi_score"),
       "ppi_rev_b": ("keep", "ppi_score"), "ppi_bioplex": ("keep", "ppi_score"), "ppi_multi": ("keep", "ppi_score"),
       "dis_obs": ("prune", "disease_obsolete"), "dis_ot": ("keep", "disease_open_targets"),
       "dis_multi": ("keep", "disease_multi_db"), "dis_scored": ("keep", "disease_scored"),
       "dis_curated": ("keep", "disease_single_curated"), "dis_weak": ("prune", "disease_weak_only"),
       "go_obs": ("prune", "go_obsolete"), "go_direct": ("keep", "go_direct"), "go_inherit": ("keep", "go_inherited"),
       "go_unsupp": ("prune", "go_unsupported"), "go_unchk": ("keep", "go_unchecked"), "ligand": ("keep", "ligand_default")}
for k, (verdict, rule) in exp.items():
    assert (v.verdict[k], v.rule[k]) == (verdict, rule), (k, v.loc[k].to_dict())
assert v.verdict_confidence["ppi_rev_a"] == v.verdict_confidence["ppi_rev_b"] == 0.9   # pair-consistent
assert v.verdict_confidence["ppi_multi"] > 0.7                                          # noisy-or combine
from bioagent.clean.prune import KEEP_THRESHOLD
assert ((v.verdict == "keep") == (v.verdict_confidence >= KEEP_THRESHOLD)).all(), v   # verdict must match the threshold
assert v.verdict.notna().all() and v.reason.str.len().min() > 10 and len(v) == len(edges)
# CRAPome: a BioPlex-only edge touching a frequent contaminant is pruned; STRING-backed edges and clean partners are not
import dataclasses
cres = dataclasses.replace(res, crapome={"P6": 0.8, "P8": 0.8, "P9": 0.1})
cedges = pd.DataFrame([rows["ppi_bioplex"], E("UniProtKB:P1", "UniProtKB:P9", "pharos:ppi:BioPlex"),
                       E("UniProtKB:P1", "UniProtKB:P8", "pharos:ppi:BioPlex,STRINGDB", 0.6)])
cv = prune_edges(cedges, cres)
assert list(cv.verdict) == ["prune", "keep", "keep"] and cv.rule.iloc[0] == "ppi_crapome" and "CRAPome" in cv.reason.iloc[0]
assert prune_edges(cedges, res).verdict.iloc[0] == "keep"          # without a CRAPome table nothing changes
print(v[["verdict", "verdict_confidence", "rule"]].to_string())
print("ALL PASSED")
