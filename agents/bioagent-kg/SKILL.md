---
name: bioagent-kg
description: Query a Biolink-aligned Pharos biomedical knowledge graph (proteins, diseases, ligands, GO terms) where every link has a kept/pruned verdict and a reason. Use when asked how two genes, diseases or drugs connect, what is known about a protein, or whether a link is trustworthy.
license: MIT
---

# Bio-agent knowledge graph

All facts come from the graph; never answer from memory. Run these from the repository root
(`pip install -r requirements-serve.txt` and `export PYTHONPATH=src` first). The sample graph is `sample/sample.whole`;
the full pruned graph is `data/processed/pharos_pruned_v3.whole` (the default when `--graph` is left out).

## Commands

- What is known about a node: `python -m bioagent --graph sample/sample.whole ask --entities BRCA1`
- How two things connect: `python -m bioagent --graph sample/sample.whole explain EGFR "non-small cell lung carcinoma"`
- A picture: add `--html out.html` to `ask`. It has a confidence cut-off slider.
- More than two hops, with filters: `... ask --entities A B --hops 3 --min-conf 0.8 --types Protein Disease` (paths of up to 3 hops, kept edges only unless `--include-pruned`).
- The user's own table: `... ingest-csv table.csv --out mine`, then `python -m bioagent --graph mine ask --entities NAME`. Columns: subject, object, optional predicate, score (0-1), pmid, source. Report the verdict and reason printed for each row.
- Running web service with JSON endpoints: `python -m bioagent --graph sample/sample.whole serve --port 8000`, then
  `GET /api/ask?q=BRCA1`, `/api/explain?a=A&b=B`, `/api/node?q=NAME`, `/api/stats`, `/healthz`.

## How to answer

1. Name nodes closely: `lung cancer` and `non-small cell lung carcinoma` are different nodes. If a name does not
   resolve, say so and offer the closest match shown by the tool; do not guess.
2. Report the verdict with each link: `keep` or `prune`, its confidence, and the reason (for example a rule such as
   `pubmed_rescue_rejected`). Pruned links are the tool's judgement that the link is probably not real; say so, do not hide them.
3. Quote the source and evidence fields the tool prints. Say "not in the graph" when nothing is returned.
4. Never put API keys in commands, files or output.
