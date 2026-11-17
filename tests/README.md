# tests

Plain Python scripts, no pytest needed. Run all of them from the repository root:

```bash
export PYTHONPATH=src
for t in tests/test_*.py; do python $t || echo FAIL $t; done
```

`test_enriched.py` and `test_export.py` need PyTorch; the rest run with `requirements-serve.txt`. They cover the harness, pruning rules, judge, PubMed tiers, ontology and gene split, explain, ask, multi-hop, CSV ingest, the web server and its upload, and the agent skill.
