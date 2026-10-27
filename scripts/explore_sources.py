"""One-off exploration for the pruning rules: how well can external sources check Pharos edges?"""
import glob, json, re
import pandas as pd
import pyarrow.parquet as pq
from bioagent.schema.kg import read_kg

D = "/scratch/hamza95/bio_kg_data"
n, e = read_kg("data/processed/pharos_evidence")

print("=== Open Targets schemas")
for ds in ("association_overall_direct", "target", "disease"):
    f = sorted(glob.glob(f"{D}/opentargets_26.09/{ds}/*.parquet"))[0]
    print(ds, [(x.name, str(x.type)[:40]) for x in pq.read_schema(f)][:14])

print("\n=== Disease edges: supporting database types")
d = e[e.evidence == "pharos:disease_association"].copy()
a = pd.DataFrame([json.loads(x) for x in d.attributes], index=d.index)
d["types"] = a.assoc_types.map(lambda t: tuple(t) if t else ())
d["ntypes"] = d.types.map(len)
print(d.ntypes.value_counts().sort_index().to_string())
single = d[d.ntypes == 1].types.map(lambda t: t[0]).value_counts()
print("single-type edges by database:\n", single.to_string())

print("\n=== Open Targets cross-check coverage for Pharos disease edges")
tg = pd.concat(pd.read_parquet(f, columns=["id", "proteinIds"]) for f in glob.glob(f"{D}/opentargets_26.09/target/*.parquet"))
rows = []
for ens, pids in zip(tg.id, tg.proteinIds):
    for p in (pids if pids is not None else []):
        if p["source"] == "uniprot_swissprot":
            rows.append((p["id"], ens))
u2e = pd.DataFrame(rows, columns=["uniprot", "ensembl"]).drop_duplicates()
print("uniprot->ensembl pairs:", len(u2e))
ot = pd.concat(pd.read_parquet(f, columns=["targetId", "diseaseId", "associationScore"]) for f in glob.glob(f"{D}/opentargets_26.09/association_overall_direct/*.parquet"))
print("OT assoc rows:", len(ot), flush=True)
ot["disease"] = ot.diseaseId.str.replace("_", ":", n=1)
print("OT disease id prefixes:", ot.disease.str.split(":").str[0].value_counts().head(6).to_dict())
d["uniprot"] = d.subject.str.replace("UniProtKB:", "", regex=False)
m = d.merge(u2e, on="uniprot", how="left")
print("Pharos disease edges with an Ensembl id:", round(m.ensembl.notna().mean(), 3))
mm = m.merge(ot[["targetId", "disease", "associationScore"]].rename(columns={"associationScore": "score"}), left_on=["ensembl", "object"], right_on=["targetId", "disease"], how="left")
print("Pharos disease edges confirmed by OT (any score):", round(mm.score.notna().mean(), 3))
print("  with OT score >= 0.3:", round((mm.score >= 0.3).mean(), 3), " >= 0.5:", round((mm.score >= 0.5).mean(), 3))
mm["ntypes"] = mm.types.map(len)
print("confirmed share by #types:\n", mm.groupby("ntypes").score.apply(lambda s: round((s >= 0.3).mean(), 3)).to_string())

print("\n=== GO edges vs UniProt's own GO annotations and obsolete terms")
up = pd.read_csv(f"{D}/uniprot/human_reviewed.tsv", sep="\t", usecols=["Entry", "Gene Ontology IDs"]).dropna()
pairs = {(r.Entry, g.strip()) for r in up.itertuples() for g in r[2].split(";")}
g = e[e.evidence == "pharos:go"]
cov = [(s.replace("UniProtKB:", ""), o) in pairs for s, o in zip(g.subject, g.object)]
print("Pharos GO edges also in UniProt GO list:", round(sum(cov) / len(cov), 3), "of", len(g))
obs = set(); cur = None
for line in open(f"{D}/go/go-basic.obo"):
    if line.startswith("id: GO:"): cur = line[4:].strip()
    elif line.startswith("is_obsolete: true") and cur: obs.add(cur)
print("obsolete GO terms in file:", len(obs), "; Pharos GO edges to obsolete terms:", int(g.object.isin(obs).sum()))
mo = set(); cur = None
for line in open(f"{D}/mondo/mondo.obo"):
    if line.startswith("id: MONDO:"): cur = line[4:].strip()
    elif line.startswith("is_obsolete: true") and cur: mo.add(cur)
print("obsolete MONDO terms:", len(mo), "; Pharos disease edges to obsolete:", int(d.object.isin(mo).sum()))
