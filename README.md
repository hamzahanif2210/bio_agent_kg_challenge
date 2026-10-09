# Bio-Agent KG Challenge
Setup: `. env.sh` then `pip install -r requirements.txt`.
Layout: `src/bioagent/{schema,ingest,clean,provenance,eval}`; data in `data/`.
Contract: `schema/kg.py` (nodes + edges Parquet with mandatory provenance cols).
Baseline: `python -m bioagent.eval.baseline data/processed/pharos TARGET_PREDICATE`.
