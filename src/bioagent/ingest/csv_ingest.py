"""Bring your own data: add a table of experimentally measured relationships to the knowledge graph.

  python -m bioagent ingest-csv my_table.csv                # writes my_table.whole.{nodes,edges}.parquet
  python -m bioagent --graph my_table.whole ask --entities "my protein"

The table needs two columns, `subject` and `object` (a name or an identifier such as UniProtKB:P00533). Optional columns:
`predicate` (Biolink name, default related_to), `subject_category` / `object_category` (protein, gene, disease, drug, ...),
`score` (0 to 1), `pmid`, `source` (free text, e.g. the assay or database). Any other column is kept as extra evidence.
Comma, tab or semicolon separated.

What happens to each row:
  1. Each name is looked up in the graph (exact id or name, case-insensitive). A name that is not found becomes a new node
     (a CURIE you typed is kept; otherwise USER:<name>) and is flagged.
  2. The row becomes an edge with full provenance (source `user:<file>`, evidence, score, method `user_upload`, timestamp).
  3. The edge gets a keep/prune verdict, a confidence and a plain-language reason from the rules below, so it is explained
     exactly like the Pharos edges. The values are named constants so they can be tuned.
"""
import io
import json
import os
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from bioagent.clean.prune import KEEP_THRESHOLD

BASE_NO_SCORE = 0.5        # row without a score
PMID_BONUS = 0.15          # row cites at least one PubMed id
CONFIRMED_BONUS = 0.2      # the graph already keeps an edge between the same two nodes (independent confirmation)
PRUNED_PENALTY = 0.2       # the graph pruned an edge between the same two nodes
NEIGHBOUR_BONUS = ((3, 0.10), (1, 0.05))   # (at least n shared kept neighbours, bonus)
NEW_ENTITY_PENALTY = 0.15  # an endpoint is not in the graph, so nothing else can corroborate it
MIN_CONF, MAX_CONF = 0.05, 0.95
MAX_ROWS = 5000

ALIASES = {
    "subject": ("subject", "head", "from", "entity_a"),
    "object": ("object", "tail", "to", "entity_b"),
    "predicate": ("predicate", "relation", "relationship", "edge_type"),
    "subject_category": ("subject_category", "subject_type", "head_type", "from_type"),
    "object_category": ("object_category", "object_type", "tail_type", "to_type"),
    "score": ("score", "confidence", "weight"),
    "pmid": ("pmid", "pmids", "pubmed", "pubmed_id", "reference"),
    "source": ("source", "database", "assay"),
}
CATEGORY = {"protein": "Protein", "gene": "Gene", "disease": "Disease", "drug": "SmallMolecule", "compound": "SmallMolecule",
            "chemical": "SmallMolecule", "small molecule": "SmallMolecule", "ligand": "SmallMolecule",
            "go": "BiologicalProcess", "process": "BiologicalProcess", "biological process": "BiologicalProcess",
            "function": "MolecularActivity", "molecular activity": "MolecularActivity", "component": "CellularComponent",
            "cellular component": "CellularComponent", "phenotype": "PhenotypicFeature", "pathway": "Pathway"}
PREDICATES = {"related_to", "associated_with", "interacts_with", "physically_interacts_with", "gene_associated_with_condition",
              "actively_involved_in", "capable_of", "located_in", "treats", "affects", "regulates", "has_gene_product",
              "causes", "contributes_to", "participates_in", "expressed_in", "subclass_of"}
CURIE = re.compile(r"^[A-Za-z][A-Za-z0-9._]*:[^\s:][^\s]*$")


def _category(x):
    if x is None or (isinstance(x, float) and x != x) or not str(x).strip():
        return None
    s = str(x).strip()
    if s.lower().startswith("biolink:"):
        return "biolink:" + s.split(":", 1)[1]
    return "biolink:" + CATEGORY.get(s.lower(), s[:1].upper() + s[1:])


def _slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:60] or "unnamed"


def read_table(text_or_path):
    """CSV/TSV text or a file path -> DataFrame (separator guessed)."""
    src = text_or_path if os.path.isfile(text_or_path) else io.StringIO(text_or_path)
    return pd.read_csv(src, sep=None, engine="python", dtype=str, keep_default_na=False)


def ingest_table(df, nodes, edges, label="upload.csv", max_rows=MAX_ROWS):
    """Returns (nodes, edges, report): the graph with the new rows added, and a report of what happened to each row.
    The graph passed in is not modified."""
    warnings = []
    cols = {str(c).strip().lower(): c for c in df.columns}
    pick = lambda k: next((cols[a] for a in ALIASES[k] if a in cols), None)
    c_sub, c_obj = pick("subject"), pick("object")
    if not c_sub or not c_obj:
        raise ValueError(f"the table needs a 'subject' and an 'object' column (found: {', '.join(map(str, df.columns))})")
    c_pred, c_score, c_pmid, c_src = pick("predicate"), pick("score"), pick("pmid"), pick("source")
    c_scat, c_ocat = pick("subject_category"), pick("object_category")
    known = {c for c in (c_sub, c_obj, c_pred, c_score, c_pmid, c_src, c_scat, c_ocat) if c}
    if len(df) > max_rows:
        warnings.append(f"only the first {max_rows} of {len(df)} rows were used")
        df = df.head(max_rows)

    by_id = set(nodes.id)
    lname = nodes.name.astype(str).str.lower()
    first, dup = {}, set(lname[lname.duplicated(keep=False)])
    for n, i in zip(lname, nodes.id):
        first.setdefault(n, i)
    degree = []   # computed only if a name is ambiguous

    def lookup(text):
        if text in by_id:
            return text
        low = text.lower()
        if low not in first:
            return None
        if low in dup:
            if not degree:
                degree.append(pd.concat([edges.subject, edges.object]).value_counts())
            cand = nodes.id[lname == low].tolist()
            return max(cand, key=lambda i: degree[0].get(i, 0))
        return first[low]

    new_nodes, resolved = {}, {}

    def resolve(text, cat):
        key = (text, cat)
        if key in resolved:
            return resolved[key]
        nid = lookup(text)
        if nid is None:
            nid = text if CURIE.match(text) else "USER:" + _slug(text)
            if nid in by_id:                      # a typed CURIE that already exists
                resolved[key] = (nid, True)
                return resolved[key]
            old = new_nodes.get(nid)
            if old is None or (old[1] == "biolink:NamedThing" and cat):
                new_nodes[nid] = (text, cat or "biolink:NamedThing")
            resolved[key] = (nid, False)
        else:
            resolved[key] = (nid, True)
        return resolved[key]

    parsed = []
    for i, r in enumerate(df.to_dict("records")):
        s, o = str(r[c_sub]).strip(), str(r[c_obj]).strip()
        if not s or not o:
            warnings.append(f"row {i + 2}: empty subject or object, skipped")
            continue
        if s.lower() == o.lower():
            warnings.append(f"row {i + 2}: subject and object are the same, skipped")
            continue
        pred = str(r[c_pred]).strip() if c_pred else ""
        p = re.sub(r"\s+", "_", pred.lower().replace("biolink:", "")) if pred else "related_to"
        if p not in PREDICATES:
            if pred:
                warnings.append(f"row {i + 2}: predicate '{pred}' is not in the supported Biolink list, used related_to")
            p = "related_to"
        score = None
        if c_score and str(r[c_score]).strip():
            try:
                v = float(str(r[c_score]).replace(",", "."))
                if 0 <= v <= 1:
                    score = v
                else:
                    warnings.append(f"row {i + 2}: score {v} is outside 0 to 1, ignored (rescale to 0-1)")
            except ValueError:
                warnings.append(f"row {i + 2}: score '{r[c_score]}' is not a number, ignored")
        pm = re.findall(r"\d{5,9}", str(r[c_pmid])) if c_pmid else []
        sid, s_in = resolve(s, _category(r[c_scat]) if c_scat else None)
        oid, o_in = resolve(o, _category(r[c_ocat]) if c_ocat else None)
        extra = {str(k): v for k, v in r.items() if k not in known and str(v).strip()}
        parsed.append(dict(i=i + 2, s=s, o=o, sid=sid, oid=oid, s_in=s_in, o_in=o_in, pred=p, score=score, pmid=pm,
                           src=str(r[c_src]).strip() if c_src else "", extra=extra))

    # what the graph already says about these nodes
    ids = {x for p in parsed for x in (p["sid"], p["oid"]) if x in by_id}
    pair, nbrs = {}, {}
    if ids and len(edges):
        sub = edges[edges.subject.isin(ids) | edges.object.isin(ids)]
        verd = sub.verdict if "verdict" in sub.columns else pd.Series("keep", index=sub.index)
        evid = sub.evidence if "evidence" in sub.columns else pd.Series("", index=sub.index)
        for a, b, v, ev in zip(sub.subject, sub.object, verd, evid):
            k = frozenset((a, b))
            if v == "keep" and pair.get(k, ("", ""))[0] != "keep":
                pair[k] = ("keep", ev)
            elif k not in pair:
                pair[k] = (v, ev)
            if v == "keep":
                nbrs.setdefault(a, set()).add(b)
                nbrs.setdefault(b, set()).add(a)

    now = datetime.now(timezone.utc).isoformat()
    rows, seen = [], set()
    for p in parsed:
        key = (p["sid"], p["pred"], p["oid"], tuple(p["pmid"]))
        if key in seen:
            continue
        seen.add(key)
        parts = [(p["score"] if p["score"] is not None else BASE_NO_SCORE,
                  f"measured score {p['score']:.2f}" if p["score"] is not None else f"no score given (starting value {BASE_NO_SCORE})")]
        conf, why = parts[0]
        rule = "user_measured"
        if p["pmid"]:
            conf += PMID_BONUS; why += f"; cites PMID {', '.join(p['pmid'][:3])} (+{PMID_BONUS})"; rule = "user_cited"
        status = pair.get(frozenset((p["sid"], p["oid"])))
        if status and status[0] == "keep":
            conf += CONFIRMED_BONUS; why += f"; the graph already keeps a link between them ({status[1]}) (+{CONFIRMED_BONUS})"; rule = "user_confirmed"
        elif status:
            conf -= PRUNED_PENALTY; why += f"; the graph pruned a link between them (-{PRUNED_PENALTY})"
        shared = len(nbrs.get(p["sid"], set()) & nbrs.get(p["oid"], set()))
        bonus = next((b for n, b in NEIGHBOUR_BONUS if shared >= n), 0.0)
        if bonus:
            conf += bonus; why += f"; {shared} shared kept neighbour(s) in the graph (+{bonus})"
        missing = [t for t, ok in ((p["s"], p["s_in"]), (p["o"], p["o_in"])) if not ok]
        if missing:
            conf -= NEW_ENTITY_PENALTY; why += f"; {', '.join(missing)} not in the graph, so nothing can corroborate it (-{NEW_ENTITY_PENALTY})"
        conf = round(float(min(MAX_CONF, max(MIN_CONF, conf))), 3)
        verdict = "keep" if conf >= KEEP_THRESHOLD else "prune"
        if verdict == "prune":
            rule = "user_unsupported"
        reason = f"{why}; confidence {conf:.2f} ({'at or above' if verdict == 'keep' else 'below'} the {KEEP_THRESHOLD} cut-off)"
        attrs = {"source_label": p["src"] or None, "pmid": p["pmid"] or None, **p["extra"]}
        rows.append({"subject": p["sid"], "predicate": "biolink:" + p["pred"], "object": p["oid"], "source": f"user:{label}",
                     "evidence": ("user:pmid:" + ",".join(p["pmid"][:3])) if p["pmid"] else "user:csv",
                     "confidence": p["score"] if p["score"] is not None else np.nan, "method": "user_upload", "timestamp": now,
                     "attributes": json.dumps({k: v for k, v in attrs.items() if v is not None}), "verdict": verdict,
                     "verdict_confidence": conf, "reason": reason, "rule": rule,
                     "needs_review": bool(missing) or (not p["pmid"] and not (status and status[0] == "keep")),
                     "row_": p["i"], "s_": p["s"], "o_": p["o"]})

    new_edges = pd.DataFrame(rows)
    nn = pd.DataFrame([{"id": i, "category": c, "name": n, "source": f"user:{label}"} for i, (n, c) in new_nodes.items()],
                      columns=["id", "category", "name", "source"])
    # nodes that ended up with no edge (every row about them was skipped or deduplicated) are not added
    if len(new_edges):
        used = set(new_edges.subject) | set(new_edges.object)
        nn = nn[nn.id.isin(used)]
    add = new_edges.drop(columns=["row_", "s_", "o_"]) if len(new_edges) else new_edges
    if "original_predicate" in edges.columns and len(add):
        add = add.assign(original_predicate=add.predicate)
    merged_edges = pd.concat([edges, add], ignore_index=True) if len(add) else edges
    merged_nodes = pd.concat([nodes, nn], ignore_index=True) if len(nn) else nodes
    report = {"label": label, "rows_read": len(df), "edges_added": len(add),
              "kept": int((new_edges.verdict == "keep").sum()) if len(new_edges) else 0,
              "pruned": int((new_edges.verdict == "prune").sum()) if len(new_edges) else 0,
              "new_nodes": nn.to_dict("records"), "warnings": warnings,
              "rows": [] if not len(new_edges) else [
                  {"row": r.row_, "subject": r.s_, "object": r.o_, "predicate": r.predicate, "verdict": r.verdict,
                   "confidence": r.verdict_confidence, "rule": r.rule, "reason": r.reason} for r in new_edges.itertuples()]}
    return merged_nodes, merged_edges, report


def ingest_csv(text_or_path, nodes, edges, label=None):
    label = label or (os.path.basename(text_or_path) if os.path.isfile(text_or_path) else "upload.csv")
    return ingest_table(read_table(text_or_path), nodes, edges, label)


def format_report(rep, limit=25):
    out = [f"{rep['label']}: {rep['rows_read']} rows read, {rep['edges_added']} edges added "
           f"({rep['kept']} kept, {rep['pruned']} pruned), {len(rep['new_nodes'])} new node(s)."]
    out += [f"  warning: {w}" for w in rep["warnings"][:limit]]
    for r in rep["rows"][:limit]:
        out.append(f"  row {r['row']}: {r['subject']} -{r['predicate'].replace('biolink:', '')}-> {r['object']}: "
                   f"{r['verdict'].upper()} {r['confidence']:.2f} [{r['rule']}] {r['reason']}")
    if len(rep["rows"]) > limit:
        out.append(f"  ... and {len(rep['rows']) - limit} more rows")
    return "\n".join(out)


def save(nodes, edges, prefix):
    nodes.to_parquet(f"{prefix}.nodes.parquet")
    edges.to_parquet(f"{prefix}.edges.parquet")
