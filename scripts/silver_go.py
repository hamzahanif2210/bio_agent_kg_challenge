"""Silver check of GO verdicts against GOA (goa_human.gaf), which the rules did not read directly.

  python scripts/silver_go.py [--graph ...] [--out runs/silver_go.json]

The rules compared each GO edge with the UniProt reviewed entry. GOA is the source UniProt's GO lines come from, so this is only
partly independent: it is informative for the groups the rules called unsupported (go_unsupported), where GOA support suggests a
wrong demotion. A term counts as supported if GOA annotates the protein to it or to a more specific descendant.
  strict = experimental evidence codes only (EXP IDA IPI IMP IGI IEP HTP HDA HMP HGI HEP); any = every code.
"""
import argparse, collections, gzip, json
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--graph", default="data/processed/pharos_pruned_v3.whole"); ap.add_argument("--src", default="/scratch/hamza95/bio_kg_data")
ap.add_argument("--out", default="runs/silver_go.json")
a = ap.parse_args()
EXP = {"EXP", "IDA", "IPI", "IMP", "IGI", "IEP", "HTP", "HDA", "HMP", "HGI", "HEP"}
parents, cur = collections.defaultdict(set), None
for line in open(f"{a.src}/go/go-basic.obo"):
    if line.startswith("id: GO:"): cur = line[4:].strip()
    elif cur and line.startswith("is_a: "): parents[cur].add(line.split()[1])
    elif cur and line.startswith("relationship: part_of "): parents[cur].add(line.split()[2])
memo = {}
def up(t):
    if t not in memo:
        s = {t}
        for p in parents.get(t, ()): s |= up(p)
        memo[t] = s
    return memo[t]
strict, anyc = collections.defaultdict(set), collections.defaultdict(set)
for line in gzip.open(f"{a.src}/go/goa_human.gaf.gz", "rt"):
    if line[0] == "!": continue
    f = line.split("\t")
    if "NOT" in f[3]: continue
    k = "UniProtKB:" + f[1]
    anc = up(f[4]); anyc[k] |= anc
    if f[6] in EXP: strict[k] |= anc
e = pd.read_parquet(f"{a.graph}.edges.parquet", columns=["subject", "object", "evidence", "rule", "verdict"])
g = e[e.object.astype(str).str.startswith("GO:")].copy()
g["any"] = [o in anyc.get(s, ()) for s, o in zip(g.subject, g.object)]
g["strict"] = [o in strict.get(s, ()) for s, o in zip(g.subject, g.object)]
t = g.groupby(["verdict", "rule"]).agg(edges=("any", "size"), any_supported=("any", "sum"), exp_supported=("strict", "sum")).reset_index()
t["pct_any"] = (100 * t.any_supported / t.edges).round(1); t["pct_exp"] = (100 * t.exp_supported / t.edges).round(1)
o = g.groupby("verdict").agg(edges=("any", "size"), pct_any=("any", "mean"), pct_exp=("strict", "mean")).round(4).reset_index()
json.dump({"by_rule": t.to_dict("records"), "overall": o.to_dict("records")}, open(a.out, "w"), indent=1)
print(t.to_string()); print(o.to_string())
