"""Pruning v2: an LLM re-decides a protein-disease edge from RETRIEVED evidence.

The model is shown only evidence we retrieved (PubMed co-mentions, the protein's UniProt
function text, the MONDO disease definition). It is not shown our rule verdict or the
database labels, and is told to answer "uncertain" when the evidence does not decide.
"""
import hashlib
import json
import re
import time
from pathlib import Path

import requests

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CACHE = Path(__file__).resolve().parents[3] / "data" / "cache" / "pubmed"

SYSTEM = (
    "You are a careful biomedical curator. You judge whether a protein (gene product) is genuinely associated "
    "with a disease, using ONLY the evidence provided in the message. Do not rely on memory. "
    "A literature co-mention count by itself is weak evidence unless the titles show a real link. "
    "If the evidence does not decide, answer \"uncertain\". Reply with one JSON object only: "
    '{"verdict": "keep" | "prune" | "uncertain", "confidence": number 0-1 that the association is real, '
    '"evidence_used": [list of: "pubmed_count", "pubmed_titles", "protein_function", "disease_definition"], '
    '"reason": "one sentence"}'
)


def _get(url, params, tries=4):
    for i in range(tries):
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 429 and i < tries - 1:
            time.sleep(2 ** i)
            continue
        r.raise_for_status()
        return r.json()


def pubmed_cooccurrence(gene, disease, n_titles=3, pause=0.4):
    """(count of PubMed title/abstract hits for gene AND disease, up to n_titles titles). Cached on disk."""
    term = f'"{gene}"[tiab] AND "{disease}"[tiab]'
    f = CACHE / (hashlib.sha1(term.encode()).hexdigest() + ".json")
    if f.exists():
        return json.loads(f.read_text())
    CACHE.mkdir(parents=True, exist_ok=True)
    time.sleep(pause)
    es = _get(f"{EUTILS}/esearch.fcgi", {"db": "pubmed", "term": term, "retmode": "json", "retmax": n_titles, "sort": "relevance"})["esearchresult"]
    count, ids = int(es.get("count", 0)), es.get("idlist", [])
    titles = []
    if ids:
        time.sleep(pause)
        sm = _get(f"{EUTILS}/esummary.fcgi", {"db": "pubmed", "id": ",".join(ids), "retmode": "json"})["result"]
        titles = [sm[i]["title"] for i in ids if i in sm]
    out = {"count": count, "titles": titles}
    f.write_text(json.dumps(out))
    return out


def mondo_definitions(obo_path):
    defs, cur = {}, None
    for line in open(obo_path):
        if line.startswith("id: MONDO:"):
            cur = line[4:].strip()
        elif cur and line.startswith("def: "):
            m = re.match(r'def: "(.*?)"', line)
            if m:
                defs[cur] = m.group(1)
    return defs


def build_prompt(gene, protein_function, disease, definition, pubmed):
    lines = [f"Protein: {gene}", f"Disease: {disease}"]
    lines.append(f"Protein function (UniProt): {protein_function[:400] if protein_function else 'not available'}")
    lines.append(f"Disease definition (MONDO): {definition[:300] if definition else 'not available'}")
    lines.append(f"PubMed articles mentioning both in title/abstract: {pubmed['count']}")
    if pubmed["titles"]:
        lines.append("Most relevant titles:\n" + "\n".join(f"- {t}" for t in pubmed["titles"]))
    lines.append("\nIs this protein-disease association supported by the evidence above?")
    return "\n".join(lines)


def parse_verdict(text):
    try:
        d = json.loads(text[text.index("{"): text.rindex("}") + 1])
        v = d.get("verdict")
        if v not in ("keep", "prune", "uncertain"):
            raise ValueError
        c = float(d.get("confidence", 0.5))
        return {"verdict": v, "confidence": min(max(c, 0.0), 1.0), "evidence_used": d.get("evidence_used", []),
                "reason": str(d.get("reason", ""))[:300]}
    except Exception:
        return {"verdict": "uncertain", "confidence": 0.5, "evidence_used": [], "reason": "unparseable model reply: " + text[:120]}


def judge(llm, model, gene, protein_function, disease, definition, pubmed, max_tokens=300):
    prompt = build_prompt(gene, protein_function, disease, definition, pubmed)
    r = llm(model, SYSTEM, [{"role": "user", "content": prompt}], [], max_tokens)
    text = " ".join(b["text"] for b in r["content"] if b["type"] == "text")
    out = parse_verdict(text)
    out["tokens"] = (r.get("usage") or {}).get("input_tokens", 0) + (r.get("usage") or {}).get("output_tokens", 0)
    return out
