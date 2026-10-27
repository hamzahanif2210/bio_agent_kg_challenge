"""Source tools for the ingest agent. Each tool fetches from a real source,
maps to Biolink with provenance, adds the result to the KGStore, and returns
only a short text summary to the LLM. To add a source: write a function with
the signature fn(store, **kwargs) -> str and register a Tool below."""
from collections import Counter

from bioagent.ingest import pharos
from bioagent.ingest.harness import Tool


def pharos_get_target(store, target):
    t = pharos.fetch_target(target)
    if not t or not t.get("uniprot"):
        return f"No Pharos target found for '{target}'."
    nodes, edges = pharos.to_kg([t])
    delta = store.add(nodes, edges)
    kinds = Counter(edges.evidence)
    partners = sorted((p for p in t.get("ppis") or [] if (p.get("target") or {}).get("uniprot")),
                      key=lambda p: -(p.get("score") or 0))[:5]
    top_partners = ", ".join(f"{p['target']['uniprot']} (score {p['score']:.2f})" if p.get("score") is not None
                             else p["target"]["uniprot"] for p in partners)
    top_diseases = ", ".join(d["name"] for d in (t.get("diseases") or [])[:5])
    return (f"Target {t.get('sym')} ({t['uniprot']}, {t.get('tdl')}): "
            f"{len(edges)} Pharos edges fetched {dict(kinds)}. "
            f"Top interaction partners (UniProt accessions, usable as `target`): {top_partners or 'none'}. "
            f"Example diseases: {top_diseases or 'none'}. "
            f"Store changes: {delta}.")


def kg_status(store):
    return str(store.summary())


TOOLS = [
    Tool("pharos_get_target",
         "Fetch one protein target from the Pharos database (NIH) by gene symbol or UniProt "
         "accession and add its linked diseases (MONDO), ligands/drugs, protein-protein "
         "interactions and GO terms to the knowledge graph. Each edge keeps its source and evidence.",
         {"type": "object",
          "properties": {"target": {"type": "string",
                                    "description": "Gene symbol (e.g. EGFR) or UniProt accession (e.g. P00533)"}},
          "required": ["target"]},
         pharos_get_target),
    Tool("kg_status",
         "Report how many nodes and edges are in the knowledge graph so far, and how many were "
         "dropped as duplicates, held-out leaks or invalid.",
         {"type": "object", "properties": {}},
         kg_status),
]
