"""Context edges from public KGs for the link-prediction experiments (Open Targets 26.09 + OptimusKG), mapped onto our node ids.

  python scripts/build_context.py [--src /scratch/hamza95/bio_kg_data] [--out data/context/context]

Writes <out>.edges.parquet (subject, predicate, object, evidence) and <out>.nodes.parquet (id, category, name).
Subjects are always Protein or Disease nodes of the Pharos graph. Sets (evidence column):
  context:pathway          protein  -> Reactome pathway          (OptimusKG)
  context:gene_phenotype   protein  -> HPO phenotype             (OptimusKG)
  context:disease_phenotype disease -> HPO phenotype             (Open Targets, OptimusKG)
  context:location         protein  -> subcellular location      (Open Targets)
  context:anatomy          protein  -> tissue, gold-quality calls (OptimusKG / Bgee)
These do not repeat the Pharos relations being predicted; the evaluation still drops any context pair that equals a held-out pair.
"""
import argparse, glob, json, re
import pandas as pd
from bioagent.standards.genes import uniprot_to_gene

ap = argparse.ArgumentParser()
ap.add_argument("--src", default="/scratch/hamza95/bio_kg_data"); ap.add_argument("--out", default="data/context/context")
ap.add_argument("--ref", default="data/processed/pharos_evidence")
a = ap.parse_args()

ref = pd.read_parquet(f"{a.ref}.nodes.parquet", columns=["id", "category"])
have = set(ref.id)
m = uniprot_to_gene(a.src); m["pid"] = "UniProtKB:" + m.uniprot
m = m[m.pid.isin(have)]
ens2p = m.groupby("ensembl").pid.apply(list).to_dict()
print("proteins with a gene:", len(m), flush=True)

# disease id translation: MONDO xrefs to DOID / EFO / Orphanet / ... -> MONDO
x2m, mondo_ids = {}, set()
cur = None
for line in open(f"{a.src}/mondo/mondo.obo"):
    if line.startswith("id: MONDO:"):
        cur = line[4:].strip(); mondo_ids.add(cur)
    elif cur and line.startswith("xref: "):
        x2m.setdefault(line.split()[1].strip(), cur)
def to_mondo(i):
    i = str(i).replace("_", ":", 1)
    return i if i in mondo_ids else x2m.get(i)
disease_have = {i for i in have if i.startswith("MONDO:")}

rows, nodes = [], {}
def add(sub, pred, obj, ev, ocat, oname=None):
    rows.append((sub, pred, obj, ev)); nodes.setdefault(obj, (ocat, oname or obj))

oe = pd.read_parquet(f"{a.src}/optimuskg/edges.parquet", columns=["from", "to", "label", "relation", "properties"])
gen = oe[oe.label.isin(["PWY-GEN", "PHE-GEN"])]
for r in gen.itertuples():
    pwy_or_phe, g = r._1, r.to
    for p in ens2p.get(g, []):
        if r.label == "PWY-GEN": add(p, "biolink:participates_in", pwy_or_phe, "context:pathway", "biolink:Pathway")
        else: add(p, "biolink:has_phenotype", pwy_or_phe, "context:gene_phenotype", "biolink:PhenotypicFeature")
print("pathway + gene phenotype:", len(rows), flush=True)

dp = oe[oe.label == "DIS-PHE"]
for d, ph in zip(dp["from"], dp["to"]):
    md = to_mondo(d)
    if md in disease_have: add(md, "biolink:has_phenotype", ph, "context:disease_phenotype", "biolink:PhenotypicFeature")
ot = pd.concat(pd.read_parquet(f) for f in glob.glob(f"{a.src}/opentargets_26.09/disease_phenotype/*.parquet"))
for d, ph in zip(ot.disease, ot.phenotype):
    md = to_mondo(d)
    if md in disease_have: add(md, "biolink:has_phenotype", str(ph), "context:disease_phenotype", "biolink:PhenotypicFeature")
print("+ disease phenotype:", len(rows), flush=True)

tg = pd.concat(pd.read_parquet(f, columns=["id", "subcellularLocations"]) for f in glob.glob(f"{a.src}/opentargets_26.09/target/*.parquet"))
for g, locs in zip(tg.id, tg.subcellularLocations):
    for p in ens2p.get(g, []):
        for l in (locs if locs is not None else []):
            lab = l.get("labelSL") or l.get("location")
            if lab: add(p, "biolink:located_in", "SL:" + str(lab), "context:location", "biolink:CellularComponent", str(lab))
print("+ location:", len(rows), flush=True)

an = oe[(oe.label == "ANA-GEN") & (oe.relation == "EXPRESSION_PRESENT")]
gold = an.properties.str.contains("gold quality", regex=False)
for t, g in zip(an["from"][gold], an["to"][gold]):
    for p in ens2p.get(g, []): add(p, "biolink:expressed_in", t, "context:anatomy", "biolink:AnatomicalEntity")
print("+ anatomy:", len(rows), flush=True)

e = pd.DataFrame(rows, columns=["subject", "predicate", "object", "evidence"]).drop_duplicates()
n = pd.DataFrame([(i, c, nm) for i, (c, nm) in nodes.items()], columns=["id", "category", "name"])
e.to_parquet(f"{a.out}.edges.parquet"); n.to_parquet(f"{a.out}.nodes.parquet")
print(e.evidence.value_counts().to_string()); print("context nodes:", len(n))
