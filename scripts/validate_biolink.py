"""Check the exported graph against the Biolink model YAML: every class and predicate exists and is not deprecated, and for
every (subject class, predicate, object class) combination the subject/object classes fit the predicate's domain/range.
  python scripts/validate_biolink.py exports/pruned.kgx [data/external/biolink-model.yaml]
"""
import sys
import pandas as pd
from bioagent.standards.model import Biolink

d = sys.argv[1]
bl = Biolink(sys.argv[2] if len(sys.argv) > 2 else "data/external/biolink-model.yaml")
print("Biolink model version:", bl.version)
nodes = pd.read_csv(f"{d}/nodes.tsv", sep="\t", usecols=["id", "category"])
edges = pd.read_csv(f"{d}/edges.tsv", sep="\t", usecols=["subject", "predicate", "object"])
cat = dict(zip(nodes.id, nodes.category))
bad = 0
for c in sorted(nodes.category.unique()):
    ok = bl.check_class(c); bad += not ok
    print(f"class {c:38s} {'ok' if ok else 'INVALID/DEPRECATED'}")
et = pd.DataFrame({"s": edges.subject.map(cat), "p": edges.predicate, "o": edges.object.map(cat)}).value_counts().reset_index(name="n")
for r in et.itertuples():
    p, dm, rg = bl.check_edge(r.s, r.p, r.o); bad += not (p and dm and rg)
    print(f"{r.s.replace('biolink:',''):18s} {r.p.replace('biolink:',''):34s} {r.o.replace('biolink:',''):18s} {r.n:>8d}  "
          f"predicate {'ok' if p else 'INVALID'}, domain {'ok' if dm else 'MISMATCH'}, range {'ok' if rg else 'MISMATCH'}")
print("problems:", bad)
