"""Rule-based pruning, version 1 (no LLM).

For every edge of the Pharos graph this gives:
  verdict             "keep" or "prune"
  verdict_confidence  our estimate (0..1) that the edge is CORRECT; prune iff < KEEP_THRESHOLD
  reason              plain-language explanation
  rule                id of the rule that decided
  needs_review        True when the evidence is thin and a later, evidence-retrieving
                      LLM step should re-decide (v2)

The numeric priors below are heuristics, not calibrated against the organizers' gold set;
they are named constants so they can be tuned once we can measure.
Evidence used: Pharos' own scores and supporting-database lists, Open Targets (independent
second opinion), GO / MONDO obsolescence and the GO hierarchy, UniProt GO annotations.
"""
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

KEEP_THRESHOLD = 0.4        # also STRING's "medium confidence" cut-off
PRIOR_BIOPLEX = 0.7         # experimental AP-MS; Pharos gives no score
PRIOR_REACTOME = 0.8        # curated pathway interaction; Pharos gives no score
MULTI_DB_CONF = {2: 0.6, 3: 0.7, 4: 0.8}   # disease edges backed by n independent databases (>=5 -> 0.9)
SCORE_OK = 0.3              # a scored disease association at or above this is kept (DisGeNET-style cut-off)
OT_STRONG = 0.3             # Open Targets direct association score that independently confirms an edge
CURATED_DISEASE_DBS = {"CTD", "DrugCentral Indication", "Monarch", "UniProt Disease"}


@dataclass
class Resources:
    go_obsolete: dict    # GO id -> replaced_by id or None
    go_parents: dict     # GO id -> set of parent GO ids (is_a, part_of)
    mondo_obsolete: dict  # MONDO id -> replaced_by id or None
    uniprot_go: dict     # UniProt accession -> set of GO ids (direct annotations)
    ot: pd.DataFrame     # columns: uniprot, mondo, score (Open Targets direct association score)


def parse_obo(path, prefix):
    """Returns (obsolete {id: replaced_by|None}, parents {id: set(ids)})."""
    obsolete, parents, cur = {}, {}, None
    for line in open(path):
        line = line.strip()
        if line.startswith("id: " + prefix):
            cur = line[4:]
        elif line == "[Term]":
            cur = None
        elif cur and line.startswith("is_obsolete: true"):
            obsolete.setdefault(cur, None)
        elif cur and line.startswith("replaced_by: "):
            obsolete[cur] = line.split()[1]
        elif cur and line.startswith("is_a: "):
            parents.setdefault(cur, set()).add(line.split()[1])
        elif cur and line.startswith("relationship: part_of "):
            parents.setdefault(cur, set()).add(line.split()[2])
    return obsolete, parents


def ancestors(term, parents, memo):
    if term in memo:
        return memo[term]
    seen, stack = set(), [term]
    while stack:
        t = stack.pop()
        for p in parents.get(t, ()):
            if p not in seen:
                seen.add(p)
                stack.append(p)
    memo[term] = seen
    return seen


def _prune_ppi(edges, mask):
    ev = edges.evidence[mask]
    src = ev.str.split(":", n=2).str[2]
    has_string, has_bp, has_re = (src.str.contains(s) for s in ("STRINGDB", "BioPlex", "Reactome"))
    s = edges.confidence[mask]
    fail = 1.0 - np.where(has_string & s.notna(), s, 0.0)
    fail = fail * np.where(has_bp, 1 - PRIOR_BIOPLEX, 1.0) * np.where(has_re, 1 - PRIOR_REACTOME, 1.0)
    conf = pd.Series(1.0 - fail, index=ev.index)
    # one verdict per unordered pair (A-B and B-A rows must agree): use the best row
    a, b = edges.subject[mask].to_numpy(), edges.object[mask].to_numpy()
    lo, hi = np.where(a < b, a, b), np.where(a < b, b, a)
    key = pd.Series(lo, index=ev.index).str.cat(pd.Series(hi, index=ev.index), sep="|")
    conf = conf.groupby(key).transform("max")
    verdict = np.where(conf >= KEEP_THRESHOLD, "keep", "prune")
    reason = [f"protein interaction supported by {sc}; combined confidence {c:.2f} "
              f"({'at or above' if c >= KEEP_THRESHOLD else 'below'} the {KEEP_THRESHOLD} cut-off)"
              for sc, c in zip(src, conf)]
    return pd.DataFrame({"verdict": verdict, "verdict_confidence": conf.round(3), "reason": reason,
                         "rule": "ppi_score", "needs_review": False}, index=ev.index)


def _prune_disease(edges, mask, res):
    d = edges[mask]
    ot = res.ot.groupby(["uniprot", "mondo"]).score.max()
    out = []
    for subj, obj, conf, attrs in zip(d.subject, d.object, d.confidence, d.attributes):
        a = json.loads(attrs) if attrs else {}
        types = a.get("assoc_types") or []
        n = len(types)
        up = subj.replace("UniProtKB:", "")
        ots = ot.get((up, obj), np.nan)
        if obj in res.mondo_obsolete:
            rep = res.mondo_obsolete[obj]
            out.append(("prune", 0.05, f"disease term {obj} is obsolete in MONDO" + (f" (replaced by {rep})" if rep else ""), "disease_obsolete", False))
        elif ots == ots and ots >= OT_STRONG:
            c = max(float(ots), MULTI_DB_CONF.get(n, 0.9) if n >= 2 else 0.0, 0.5)
            out.append(("keep", round(c, 3), f"Open Targets independently reports this association (score {ots:.2f})", "disease_open_targets", False))
        elif n >= 2:
            c = MULTI_DB_CONF.get(n, 0.9)
            out.append(("keep", c, f"supported by {n} independent databases ({', '.join(types[:4])})", "disease_multi_db", False))
        elif conf == conf and conf >= SCORE_OK:
            out.append(("keep", round(max(float(conf), KEEP_THRESHOLD), 3), f"single database ({types[0] if types else 'unknown'}) with score {conf:.2f}", "disease_scored", False))
        elif n == 1 and types[0] in CURATED_DISEASE_DBS:
            out.append(("keep", 0.5, f"single curated database ({types[0]}); no independent confirmation", "disease_single_curated", True))
        else:
            db = types[0] if types else "no recorded source"
            out.append(("prune", 0.2, f"only weak or indirect evidence ({db}); not confirmed by Open Targets", "disease_weak_only", True))
    return pd.DataFrame(out, index=d.index, columns=["verdict", "verdict_confidence", "reason", "rule", "needs_review"])


def _prune_go(edges, mask, res):
    g = edges[mask]
    memo, prop = {}, {}
    out = []
    for subj, go in zip(g.subject, g.object):
        up = subj.replace("UniProtKB:", "")
        if go in res.go_obsolete:
            rep = res.go_obsolete[go]
            out.append(("prune", 0.05, f"GO term {go} is obsolete" + (f" (replaced by {rep})" if rep else ""), "go_obsolete", False))
            continue
        direct = res.uniprot_go.get(up)
        if direct is None:
            out.append(("keep", 0.6, "protein not in the UniProt reviewed set; cannot check this annotation", "go_unchecked", True))
        elif go in direct:
            out.append(("keep", 0.9, "UniProt annotates this GO term directly", "go_direct", False))
        else:
            if up not in prop:
                prop[up] = set().union(*[ancestors(t, res.go_parents, memo) for t in direct]) if direct else set()
            if go in prop[up]:
                out.append(("keep", 0.85, "implied by a more specific UniProt annotation (GO hierarchy)", "go_inherited", False))
            else:
                out.append(("prune", 0.35, "not among UniProt's annotations or their parent terms", "go_unsupported", True))
    return pd.DataFrame(out, index=g.index, columns=["verdict", "verdict_confidence", "reason", "rule", "needs_review"])


def prune_edges(edges, res):
    """edges: Pharos graph edge table (with evidence/confidence/attributes). Returns verdict table, same index."""
    ev = edges.evidence
    parts = [
        _prune_ppi(edges, ev.str.startswith("pharos:ppi:").to_numpy()),
        _prune_disease(edges, (ev == "pharos:disease_association").to_numpy(), res),
        _prune_go(edges, (ev == "pharos:go").to_numpy(), res),
    ]
    lig = (ev == "pharos:ligand_activity").to_numpy()
    parts.append(pd.DataFrame({"verdict": "keep", "verdict_confidence": 0.5,
                               "reason": "no per-edge evidence available (activity values not fetched); kept by default",
                               "rule": "ligand_default", "needs_review": True}, index=edges.index[lig]))
    v = pd.concat(parts)
    other = edges.index.difference(v.index)
    if len(other):
        v = pd.concat([v, pd.DataFrame({"verdict": "keep", "verdict_confidence": 0.5, "reason": "no rule for this edge type",
                                        "rule": "default", "needs_review": True}, index=other)])
    return v.reindex(edges.index)


def load_resources(src_dir):
    """Load GO/MONDO/UniProt/Open Targets from the downloaded sources directory."""
    import glob
    go_obs, go_par = parse_obo(f"{src_dir}/go/go-basic.obo", "GO:")
    mo_obs, _ = parse_obo(f"{src_dir}/mondo/mondo.obo", "MONDO:")
    up = pd.read_csv(f"{src_dir}/uniprot/human_reviewed.tsv", sep="\t", usecols=["Entry", "Gene Ontology IDs"])
    uniprot_go = {r[0]: ({x.strip() for x in str(r[1]).split(";")} if isinstance(r[1], str) else set())
                  for r in up.itertuples(index=False)}
    ot_dir = f"{src_dir}/opentargets_26.09"
    tg = pd.concat(pd.read_parquet(f, columns=["id", "proteinIds"]) for f in glob.glob(f"{ot_dir}/target/*.parquet"))
    rows = [(p["id"], ens) for ens, pids in zip(tg.id, tg.proteinIds) for p in (pids if pids is not None else [])
            if p["source"] == "uniprot_swissprot"]
    u2e = pd.DataFrame(rows, columns=["uniprot", "ensembl"]).drop_duplicates()
    ot = pd.concat(pd.read_parquet(f, columns=["targetId", "diseaseId", "associationScore"])
                   for f in glob.glob(f"{ot_dir}/association_overall_direct/*.parquet"))
    ot = ot[ot.diseaseId.str.startswith("MONDO_")].copy()
    ot["mondo"] = ot.diseaseId.str.replace("_", ":", n=1)
    ot = ot.merge(u2e, left_on="targetId", right_on="ensembl")[["uniprot", "mondo", "associationScore"]]
    return Resources(go_obs, go_par, mo_obs, uniprot_go, ot.rename(columns={"associationScore": "score"}))
