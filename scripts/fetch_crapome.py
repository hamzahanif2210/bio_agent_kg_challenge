"""Contaminant frequency for the proteins in our BioPlex-only interactions, from the CRAPome web service
(https://reprint-apms.org/?q=ws/proteindetail/<gene>/human/singleStep). For each gene we count in how many distinct control
experiments it was detected; frequency = that count / the number of distinct control experiments seen across all queried genes
(an estimate of the total, since the service has no cheap 'how many experiments' call).

The server sends an incomplete certificate chain, so we fetch the missing intermediate certificate from the address named in
the server's own certificate and verify against the system CA bundle plus that intermediate. Verification stays on.
Output: data/external/crapome_human.tsv (Uniprot, gene, n_experiments, frequency) and a JSONL cache so restarts resume.

  python -u scripts/fetch_crapome.py
"""
import json, os, re, ssl, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import requests

GRAPH = "data/processed/pharos_pruned_v3.whole"
CACHE, OUT, BUNDLE = "data/external/crapome_cache.jsonl", "data/external/crapome_human.tsv", "data/external/reprint_ca_bundle.pem"
URL = "https://reprint-apms.org/?q=ws/proteindetail/{}/human/singleStep"
AIA = "http://crt.sectigo.com/InCommonRSAServerCA2.crt"       # named in the server certificate's Authority Information Access
EXPT = re.compile(r'expt="([^"]+)"')


def make_bundle():
    if os.path.exists(BUNDLE):
        return
    der = requests.get(AIA, timeout=30).content
    pem = subprocess.run(["openssl", "x509", "-inform", "DER"], input=der, capture_output=True, check=True).stdout.decode()
    ca = ssl.get_default_verify_paths().cafile or "/etc/pki/tls/certs/ca-bundle.crt"
    open(BUNDLE, "w").write(open(ca).read() + "\n" + pem)


def fetch(gene, tries=4):
    for i in range(tries):
        try:
            r = requests.get(URL.format(gene), timeout=120, verify=BUNDLE)
            if r.status_code == 200:
                return gene, sorted(set(EXPT.findall(r.text)))
            if r.status_code in (404, 400):
                return gene, []
        except requests.RequestException:
            pass
        time.sleep(2 ** i)
    return gene, None


make_bundle()
nodes = pd.read_parquet(f"{GRAPH}.nodes.parquet", columns=["id", "name"])
e = pd.read_parquet(f"{GRAPH}.edges.parquet", columns=["subject", "object", "evidence"])
e = e[e.evidence == "pharos:ppi:BioPlex"]
ids = set(e.subject) | set(e.object)
sym = dict(zip(nodes.id, nodes.name))
genes = sorted({sym[i] for i in ids if re.match(r"^[A-Za-z0-9-]+$", str(sym.get(i, "")))})
done = {}
if os.path.exists(CACHE):
    for l in open(CACHE):
        r = json.loads(l); done[r["gene"]] = r["expts"]
todo = [g for g in genes if g not in done]
print(f"{len(genes)} genes, {len(done)} cached, {len(todo)} to fetch", flush=True)
with open(CACHE, "a") as f, ThreadPoolExecutor(4) as ex:
    for i, (g, ex_ids) in enumerate(ex.map(fetch, todo)):
        if ex_ids is not None:
            done[g] = ex_ids; f.write(json.dumps({"gene": g, "expts": ex_ids}) + "\n")
        if i % 200 == 0:
            f.flush(); print(f"{i}/{len(todo)}", flush=True)
total = len(set().union(*map(set, done.values()))) if done else 0
print("distinct control experiments seen:", total)
rows = [(i.replace("UniProtKB:", ""), sym[i], len(done[sym[i]]), len(done[sym[i]]) / total) for i in ids if sym.get(i) in done]
pd.DataFrame(rows, columns=["Uniprot", "gene", "n_experiments", "frequency"]).to_csv(OUT, sep="\t", index=False)
print("wrote", OUT, len(rows), "proteins;", sum(r[3] > 0.5 for r in rows), "above 0.5")
