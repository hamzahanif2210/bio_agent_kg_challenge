"""Gene-protein split: add Gene nodes (Ensembl) and `has_gene_product` edges to the proteins, and move protein-disease
associations from the protein to its gene, which makes `gene_associated_with_condition` valid in Biolink (domain `gene`).

  python -m bioagent.standards.genes data/processed/pharos_pruned_v3.whole /scratch/hamza95/bio_kg_data data/processed/pharos_genes.whole

Mapping UniProt (Swiss-Prot) -> Ensembl gene id and symbol comes from the Open Targets target table. A protein with no
mapping keeps its disease edges on the protein (the exporter then uses `associated_with` for them).
The original subject of a moved edge is kept in column `original_subject`.
"""
import glob
import sys

import pandas as pd


def uniprot_to_gene(src_dir):
    """DataFrame uniprot, ensembl, symbol (Swiss-Prot proteins only; first gene when several map)."""
    tg = pd.concat(pd.read_parquet(f, columns=["id", "approvedSymbol", "proteinIds"])
                   for f in glob.glob(f"{src_dir}/opentargets_26.09/target/*.parquet"))
    rows = [(p["id"], ens, sym) for ens, sym, pids in zip(tg.id, tg.approvedSymbol, tg.proteinIds)
            for p in (pids if pids is not None else []) if p["source"] == "uniprot_swissprot"]
    return pd.DataFrame(rows, columns=["uniprot", "ensembl", "symbol"]).drop_duplicates("uniprot")


def add_genes(nodes, edges, mapping):
    """mapping: DataFrame uniprot, ensembl, symbol. Returns (nodes, edges) with Gene nodes and moved disease edges."""
    m = mapping.assign(pid="UniProtKB:" + mapping.uniprot, gid="ENSEMBL:" + mapping.ensembl)
    m = m[m.pid.isin(set(nodes.id))]
    gene_of = dict(zip(m.pid, m.gid))
    gnodes = pd.DataFrame({"id": m.gid, "category": "biolink:Gene", "name": m.symbol, "source": "opentargets"}).drop_duplicates("id")
    ts, template = edges.timestamp.iloc[0], edges.iloc[0]
    link = pd.DataFrame({"subject": m.gid, "predicate": "biolink:has_gene_product", "object": m.pid, "source": "opentargets",
                         "evidence": "opentargets:target_protein_mapping", "confidence": float("nan"), "timestamp": ts,
                         "method": "gene_protein_split", "attributes": "{}"})
    e = edges.copy()
    e["original_subject"] = None
    disease = (e.evidence == "pharos:disease_association") & e.subject.isin(gene_of)
    e.loc[disease, "original_subject"] = e.subject[disease]
    e.loc[disease, "subject"] = e.subject[disease].map(gene_of)
    for c in e.columns:                       # verdict columns for the new link edges: structural facts, kept
        if c not in link.columns:
            link[c] = {"verdict": "keep", "verdict_confidence": 1.0, "reason": "Ensembl gene encodes this UniProt protein (Open Targets)",
                       "rule": "gene_product_link", "needs_review": False}.get(c)
    return (pd.concat([nodes, gnodes[~gnodes.id.isin(set(nodes.id))]], ignore_index=True),
            pd.concat([e, link[e.columns]], ignore_index=True))


if __name__ == "__main__":
    graph, src, out = sys.argv[1:4]
    nodes, edges = pd.read_parquet(f"{graph}.nodes.parquet"), pd.read_parquet(f"{graph}.edges.parquet")
    n2, e2 = add_genes(nodes, edges, uniprot_to_gene(src))
    n2.to_parquet(f"{out}.nodes.parquet"); e2.to_parquet(f"{out}.edges.parquet")
    kept = e2[e2.verdict == "keep"]
    used = set(kept.subject) | set(kept.object)
    kept.to_parquet(f"{out.replace('.whole', '.pruned')}.edges.parquet")
    n2[n2.id.isin(used)].to_parquet(f"{out.replace('.whole', '.pruned')}.nodes.parquet")
    print(f"{(n2.category == 'biolink:Gene').sum()} gene nodes; {int(e2.original_subject.notna().sum())} disease edges moved to genes; "
          f"{len(e2)} edges total")
