"""Silver-standard check of the pruning verdicts against evidence the rules did not use.

  python scripts/silver_eval.py [--graph data/processed/pharos_pruned_v3.whole] [--out runs/silver_eval.json]

There is no gold set, so we ask a narrower question: do kept edges have independent support more often than pruned edges, and
which pruned groups still contain strongly supported edges (candidates for rescue)?
  disease edges: support = any curated Open Targets datasource (ClinVar/EVA, Orphanet, Gene2Phenotype, ClinGen, Genomics England,
                 Cancer Gene Census, UniProt literature/variants, gene burden, IntOGen) with score >= 0.5. The rules used the overall
                 Open Targets score and PubMed counts, so for the groups decided by those the check is partly circular; the groups
                 decided without Open Targets (pubmed_none, disease_weak_only, llm_*, pubmed_rescue*) are the informative ones.
  ppi edges:     support = the pair is in IntAct or SIGNOR (Open Targets interaction table), which the rules did not use.
"""
import argparse, glob, json
import numpy as np, pandas as pd
from bioagent.standards.genes import uniprot_to_gene

ap = argparse.ArgumentParser()
ap.add_argument("--graph", default="data/processed/pharos_pruned_v3.whole"); ap.add_argument("--src", default="/scratch/hamza95/bio_kg_data")
ap.add_argument("--out", default="runs/silver_eval.json")
a = ap.parse_args()
OT = f"{a.src}/opentargets_26.09"
CURATED = {"eva", "orphanet", "gene2phenotype", "clingen", "genomics_england", "cancer_gene_census", "uniprot_literature",
           "uniprot_variants", "gene_burden", "intogen", "eva_somatic"}
e = pd.read_parquet(f"{a.graph}.edges.parquet", columns=["subject", "object", "evidence", "rule", "verdict"])
m = uniprot_to_gene(a.src); u2g = dict(zip("UniProtKB:" + m.uniprot, m.ensembl))
res = {}

# ---- disease
x2m, mondo, cur = {}, set(), None
for line in open(f"{a.src}/mondo/mondo.obo"):
    if line.startswith("id: MONDO:"): cur = line[4:].strip(); mondo.add(cur)
    elif cur and line.startswith("xref: "): x2m.setdefault(line.split()[1].strip(), cur)
to_mondo = lambda i: (i.replace("_", ":", 1) if i.replace("_", ":", 1) in mondo else x2m.get(i.replace("_", ":", 1)))
d = e[e.evidence == "pharos:disease_association"].copy()
d["g"] = d.subject.map(u2g)
ds = pd.concat(pd.read_parquet(f, columns=["diseaseId", "targetId", "aggregationType", "aggregationValue", "associationScore"])
               for f in glob.glob(f"{OT}/association_by_datasource_direct/*.parquet"))
ds = ds[(ds.aggregationType == "datasourceId") & ds.aggregationValue.isin(CURATED) & (ds.associationScore >= 0.5)]
ds["mondo"] = ds.diseaseId.map(to_mondo)
sup = set(zip(ds.targetId, ds.mondo.dropna()))
d["support"] = [(g, o) in sup for g, o in zip(d.g, d.object)]
d["mappable"] = d.g.notna()
t = d[d.mappable].groupby(["verdict", "rule"]).agg(edges=("support", "size"), supported=("support", "sum")).reset_index()
t["pct_supported"] = (100 * t.supported / t.edges).round(1)
res["disease"] = t.to_dict("records")
res["disease_overall"] = d[d.mappable].groupby("verdict").support.agg(["size", "sum", "mean"]).round(4).reset_index().to_dict("records")

# ---- ppi
ix = pd.concat(pd.read_parquet(f, columns=["sourceDatabase", "targetA", "targetB"]) for f in glob.glob(f"{OT}/interaction/*.parquet"))
ix = ix[ix.sourceDatabase.isin(["intact", "signor"])]
ix = ix.dropna(subset=["targetA", "targetB"])
pairs = {tuple(sorted(t)) for t in zip(ix.targetA.tolist(), ix.targetB.tolist())}
p = e[e.evidence.str.startswith("pharos:ppi:")].copy()
p["a"], p["b"] = p.subject.map(u2g), p.object.map(u2g)
p = p[p.a.notna() & p.b.notna()]
p["support"] = [tuple(sorted((x, y))) in pairs for x, y in zip(p.a, p.b)]
t = p.groupby(["evidence", "verdict", "rule"]).agg(edges=("support", "size"), supported=("support", "sum")).reset_index()
t["pct_supported"] = (100 * t.supported / t.edges).round(1)
res["ppi"] = t.to_dict("records")
res["ppi_overall"] = p.groupby("verdict").support.agg(["size", "sum", "mean"]).round(4).reset_index().to_dict("records")
json.dump(res, open(a.out, "w"), indent=1, default=int)
for k in ("disease", "ppi"):
    print(k); print(pd.DataFrame(res[k]).to_string(index=False))
print(pd.DataFrame(res["disease_overall"]).to_string(index=False)); print(pd.DataFrame(res["ppi_overall"]).to_string(index=False))
