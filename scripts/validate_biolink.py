"""Check the exported graph against the Biolink model with the Biolink Model Toolkit (bmt): every class and predicate
must exist and be non-deprecated, and each edge type's subject/object classes must fit the predicate's domain/range.
Reads exports/<name>.kgx/{nodes,edges}.tsv.   python scripts/validate_biolink.py exports/pruned.kgx
"""
import sys
import pandas as pd
from bmt import Toolkit

d = sys.argv[1]
tk = Toolkit()
print("Biolink model version:", tk.get_model_version())
nodes = pd.read_csv(f"{d}/nodes.tsv", sep="\t", usecols=["id", "category"])
edges = pd.read_csv(f"{d}/edges.tsv", sep="\t", usecols=["subject", "predicate", "object"])
cat = dict(zip(nodes.id, nodes.category))
bad = 0
for c in sorted(nodes.category.unique()):
    el = tk.get_element(c)
    ok = el is not None and not getattr(el, "deprecated", None)
    bad += not ok
    print(f"class {c:38s} {'ok' if ok else 'INVALID/DEPRECATED'}")
et = pd.DataFrame({"s": edges.subject.map(cat), "p": edges.predicate, "o": edges.object.map(cat)}).value_counts().reset_index(name="n")
for r in et.itertuples():
    el = tk.get_element(r.p)
    if el is None or not tk.is_predicate(r.p) or getattr(el, "deprecated", None):
        print(f"predicate {r.p}: INVALID/DEPRECATED ({r.n} edges)"); bad += 1; continue
    dom, rng = tk.get_slot_domain(r.p, formatted=True), tk.get_slot_range(r.p, formatted=True)
    ds, rs = set(tk.get_descendants(x, formatted=True, reflexive=True) for x in dom) if False else (set(), set())
    for x in dom: ds |= set(tk.get_descendants(x, formatted=True, reflexive=True))
    for x in rng: rs |= set(tk.get_descendants(x, formatted=True, reflexive=True))
    s_ok, o_ok = (not ds) or r.s in ds, (not rs) or r.o in rs
    bad += not (s_ok and o_ok)
    print(f"{r.s.replace('biolink:',''):18s} {r.p.replace('biolink:',''):34s} {r.o.replace('biolink:',''):18s} {r.n:>8d}  "
          f"domain {'ok' if s_ok else 'MISMATCH'}, range {'ok' if o_ok else 'MISMATCH'}")
print("problems:", bad)
