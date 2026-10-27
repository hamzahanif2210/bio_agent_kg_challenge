"""Demo: explanations on the real pruned-pipeline graph."""
from bioagent.provenance.explain import explain, format_explanation, load
g = load("data/processed/pharos_pruned.whole")
for a, b in [("EGFR", "non-small cell lung carcinoma"), ("EGFR", "TP53"), ("EGFR", "BRCA1")]:
    print("=" * 100); print(f"Q: why does {a} connect to {b}?"); print("=" * 100)
    try:
        print(format_explanation(explain(None, a, b, max_paths=3, graph=g)))
    except KeyError as e:
        print("could not resolve:", e)
