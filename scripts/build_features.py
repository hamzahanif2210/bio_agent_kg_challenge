"""Node features for the link-prediction experiments. Writes data/features/{text,seq}.npz (ids, X float16).

  python scripts/build_features.py [--ref data/processed/pharos_evidence] [--src /scratch/hamza95/bio_kg_data]

text: TF-IDF of the node's name plus its definition (MONDO / GO definition, UniProt function and protein names), reduced
      to 64 dimensions with truncated SVD. Ligands have only a name (character n-grams).
seq : amino-acid and dipeptide composition (420 values) of the UniProt sequence, log-scaled; proteins only.
The UniProt sequences are downloaded once from rest.uniprot.org (TLS verified) and cached in data/external/.
"""
import argparse, os, re
import numpy as np, pandas as pd, requests
from scipy.sparse import hstack
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from bioagent.clean.judge import mondo_definitions

ap = argparse.ArgumentParser()
ap.add_argument("--ref", default="data/processed/pharos_evidence"); ap.add_argument("--src", default="/scratch/hamza95/bio_kg_data")
ap.add_argument("--out", default="data/features")
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
nodes = pd.read_parquet(f"{a.ref}.nodes.parquet", columns=["id", "category", "name"])

# ---------- text
defs = mondo_definitions(f"{a.src}/mondo/mondo.obo")
cur = None
for line in open(f"{a.src}/go/go-basic.obo"):
    if line.startswith("id: GO:"): cur = line[4:].strip()
    elif cur and line.startswith("def: "):
        m = re.match(r'def: "(.*?)"', line)
        if m: defs[cur] = m.group(1)
up = pd.read_csv(f"{a.src}/uniprot/human_reviewed.tsv", sep="\t", usecols=["Entry", "Protein names", "Function [CC]"])
for r in up.itertuples(index=False):
    defs["UniProtKB:" + r[0]] = " ".join(str(x) for x in r[1:] if isinstance(x, str)).replace("FUNCTION: ", "")
doc = [f"{n} {defs.get(i, '')}" for i, n in zip(nodes.id, nodes.name)]
lig = (nodes.category == "biolink:SmallMolecule").to_numpy()
w = TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=60000, sublinear_tf=True, dtype=np.float32).fit_transform([d for d, l in zip(doc, lig) if not l])
c = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 4), min_df=5, max_features=60000, sublinear_tf=True, dtype=np.float32).fit_transform(nodes.name[lig].astype(str))
out = np.zeros((len(nodes), 64), np.float32)
for mat, sel, nm in ((w, ~lig, "words"), (c, lig, "chars")):
    z = TruncatedSVD(64, random_state=0).fit_transform(mat)
    z /= np.linalg.norm(z, axis=1, keepdims=True) + 1e-9
    out[sel] = z; print("text svd done:", nm, mat.shape, flush=True)
np.savez(f"{a.out}/text.npz", ids=nodes.id.to_numpy(), X=out.astype(np.float16))

# ---------- sequence composition
cache = "data/external/uniprot_seq.tsv"
if not os.path.exists(cache):
    r = requests.get("https://rest.uniprot.org/uniprotkb/stream", timeout=600, stream=True,
                     params={"query": "reviewed:true AND organism_id:9606", "fields": "accession,sequence", "format": "tsv"})
    r.raise_for_status(); open(cache, "wb").write(r.content)
sq = pd.read_csv(cache, sep="\t"); sq.columns = ["acc", "seq"]
AA = "ACDEFGHIKLMNPQRSTVWY"; idx = {x: i for i, x in enumerate(AA)}
def feat(s):
    v = np.zeros(420, np.float32); s = [idx[x] for x in s if x in idx]
    if not s: return v
    v[:20] = np.bincount(s, minlength=20) / len(s)
    if len(s) > 1: v[20:] = np.bincount(np.array(s[:-1]) * 20 + np.array(s[1:]), minlength=400) / (len(s) - 1)
    return v
ids = ["UniProtKB:" + x for x in sq.acc]; have = set(nodes.id); keep = [i for i, x in enumerate(ids) if x in have]
X = np.stack([feat(sq.seq.iloc[i]) for i in keep]); X = np.log1p(X * 100); X = (X - X.mean(0)) / (X.std(0) + 1e-6)
np.savez(f"{a.out}/seq.npz", ids=np.array([ids[i] for i in keep]), X=X.astype(np.float16))
print("seq features:", X.shape, flush=True)
