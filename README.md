# Bio-Agent Knowledge Graph Construction Challenge

An AI agent that autonomously builds an enriched, ontology-aligned knowledge graph (KG) from public Pharos data, optimized for link prediction.

## The challenge

Knowledge graphs are powerful for biology but hard for most researchers to build and use. The organizers (Bio-Agent KG Construction Challenge, topic *Structured Data Integration & Link Prediction*) ask teams to build **AI agents that construct, maintain and query KGs autonomously**.

**Key question:** given a set of experimentally measured relationships, can an agent build a contextualized KG that **outperforms existing public KGs (e.g. Pharos) at predicting held-out links** with GNNs/GCNs?

### What we must deliver

An agent (or swarm of agents) that takes public datasets from [Pharos](https://pharos.nih.gov/about) and builds an enriched graph, pulling in disease, drug, gene, protein and ontology context from other public KGs and databases. The agent should run this loop:

1. **Ingest:** combine heterogeneous sources into one graph.
2. **Filter:** turn a plain-language research question into a graph query and return only the relevant subgraph.
3. **Clean:** prune erroneous or contextually wrong links (hallucinations), e.g. by re-weighting edge confidence with literature or a GNN.
4. **Limit:** keep the queryable graph a manageable size (the organizers call this probably unnecessary).
5. **Maintain:** update automatically as new literature or data appears (the organizers hope this is "not too complicated").

### How it is judged

The agent builds the graph; GNN/GCN/embedding models are then run to predict held-out edges, and performance is compared with the same ML on the existing Pharos graph.

| Criterion | Weight | What it asks |
|---|---|---|
| Usability | 40% | Can a non-KG expert use the agent? Does it make the value of KGs obvious, including multi-hop questions? |
| Accuracy and pruning | 30% | How well does it remove erroneous or irrelevant data? |
| Explainability | 20% | Can it trace the lineage of any edge (why does A connect to B)? |
| Adherence to standards | 10% | Nodes and edges map to real ontology classes and properties (Biolink, OBO URIs); few, specific classes. |

### Key dates

- Kickoff Oct 6, 2026 (done)
- **Progress report by email: Oct 27, 2026**
- **Challenge ends: Nov 17, 2026**
- Judging Nov 17 to Dec 8; results Dec 15
- Prize (open-source track): USD 5,000 AWS credits

**New to the project? Start with [docs/what_we_need_to_do.md](docs/what_we_need_to_do.md)**, a plain-language guide to the goal, the scoring, the work packages and the calendar.

## Our progress (as of 2026-10-26)

| Area | Status |
|---|---|
| Shared graph format (nodes/edges Parquet with provenance columns) | Done (`schema/kg.py`) |
| Full Pharos graph from the live API | Done: 397,636 nodes, 3,091,048 edges |
| Leakage-safe evaluation (unordered-pair split, hard negatives, enrichment leak check) | Done (`eval/`) |
| Baseline to beat (GraphSAGE on Pharos, 3 seeds, 4 edge types) | Done, see table below |
| Ingest agent harness with a Pharos tool (cache, logs, caps, validation, leak guard) | Done; tested with a scripted model (`tests/test_harness.py`) |
| Ingest agent run against the real Claude API | **Not yet** (needs `ANTHROPIC_API_KEY`) |
| Additional source tools (UniProt, Open Targets, GO/MONDO, OptimusKG, Monarch) | **Not started** |
| Clean / prune agent | **Not started** (placeholder) |
| Filter (natural language to subgraph query) | **Not started** |
| Maintain (auto-update) | **Not started** |
| Edge explanation (`provenance/explain.py`) | Basic lookup only |
| Enriched graph beating the baseline | **Not yet** (no enrichment source added) |
| Answers from the organizers (split, metric, GNN, submission format) | **Not yet asked** |

**Next steps:** (1) run the ingest agent for real on a small task; (2) add a first enrichment source and test it with the leak check; (3) measure whether the enriched graph beats the baseline on the hard-negative metric; (4) build the Clean step; (5) send the open questions below to the organizers.

## Approach

The agent follows the challenge loop:

| Step | Goal | Module |
|---|---|---|
| **Ingest** | Pull disease, drug, gene, protein and ontology context from public sources; map to Biolink classes and OBO URIs | `src/bioagent/ingest/` |
| **Filter** | Turn a natural-language question into a graph query for the relevant subgraph | *planned* |
| **Clean** | Score edge confidence and prune erroneous or contextually wrong links | `src/bioagent/clean/` |
| **Limit** | Cap graph size for performance | `src/bioagent/clean/` |
| **Maintain** | Re-run to pick up new literature/data | *planned* |

Every edge carries provenance (source, evidence, confidence, method, timestamp), so any link can be traced back with `provenance/explain.py`.

## Repository layout

```
src/bioagent/
  schema/kg.py          Shared KG contract (nodes + edges, Parquet)
  ingest/harness.py     Tool-calling loop: KGStore (validation + leak guard), LLM cache, step/token caps, JSONL log
  ingest/tools.py       Source tools for the agent (Pharos first; add new sources here)
  ingest/run.py         CLI: python -m bioagent.ingest.run "task" --out PREFIX (needs ANTHROPIC_API_KEY)
  ingest/pharos.py      Pharos GraphQL loader (bulk and single target)
  clean/prune.py        Edge scoring and pruning (TODO)
  provenance/explain.py "Why does A connect to B?" lineage lookup
  eval/split.py         Fixed held-out edge split + leak guard
  eval/baseline.py      GraphSAGE link-prediction evaluator
scripts/*.sbatch             Slurm jobs: fetch_pharos_full (graph), baseline_array (evaluation)
scripts/summarize_runs.py    Baseline results table (mean +/- std over seeds)
tests/test_harness.py        Harness tests (no API key needed)
data/{raw,processed}/        Local data (git-ignored)
runs/                        Experiment outputs (git-ignored)
env.sh                       Activates the environment and sets PYTHONPATH
```

## Graph format (the shared contract)

Graphs are stored as two Parquet files: `<prefix>.nodes.parquet` and `<prefix>.edges.parquet`.

- **nodes:** `id` (CURIE), `category` (Biolink class), `name`, `source`
- **edges:** `subject`, `predicate` (Biolink), `object`, `source`, `evidence`, `confidence`, `timestamp`, `method`

Use `read_kg` / `write_kg` from `bioagent.schema.kg`; they reject tables missing any required column.

## Setup

Developed on a Digital Research Alliance of Canada cluster (Python 3.13).

```bash
. env.sh
pip install -r requirements.txt
```

Notes:
- `pyarrow` is not in `requirements.txt`: the cluster wheelhouse only has a non-installable stub. It is needed for Parquet I/O, so load the cluster's Arrow module or install it another way before reading or writing graphs.
- The ingest agent uses the Claude API. Export `ANTHROPIC_API_KEY` in your shell. Never commit it.

## Evaluation protocol

1. Fix the target edge type to predict and split its edges with `eval/split.py` (seeded). Test and validation edges are withheld.
2. Build the graph from **training edges only**. The agent must never see held-out edges (`train_only` guards this).
3. Train the same GNN on the baseline (Pharos) graph and on the agent-built graph, and compare AUROC and average precision:

```bash
python -m bioagent.eval.baseline data/processed/pharos TARGET_PREDICATE
```

The organizers' exact split, metric and baseline are still to be confirmed.

### Baseline to beat (full Pharos graph)

GraphSAGE with learned embeddings (no node features), 100 epochs, mean ± std over 3 seeds, test AUROC. Produced by `sbatch scripts/baseline_array.sbatch data/processed/pharos_full pharosfull` and summarized by `python scripts/summarize_runs.py pharosfull`. Graph: 397,636 nodes, 3,091,048 edges, fetched from the Pharos GraphQL API on 2026-10-09 with full nested lists (`top:5000`; the API default of 10 per list truncates the graph badly).

| Target edges | Test pairs | Random neg. | Same-type neg. | Hard neg. (type + degree) |
|---|---|---|---|---|
| protein-disease | 24,814 | 0.940 ± 0.005 | 0.975 ± 0.001 | **0.525 ± 0.000** |
| protein-GO term | 25,871 | 0.919 ± 0.005 | 0.904 ± 0.002 | **0.590 ± 0.003** |
| ligand-protein | 46,322 | 0.457 ± 0.018 | 0.620 ± 0.019 | **0.626 ± 0.011** |
| protein-protein | 106,047 | 0.769 ± 0.017 | 0.795 ± 0.011 | **0.686 ± 0.037** |

Trust the hard-negative column. Protein-disease drops from 0.975 to 0.525 once negatives match in degree, so the model mostly learns node popularity; protein-GO behaves the same way. Protein-protein is the most informative target (0.686 under hard negatives, many test pairs), though its seed spread is larger. The ligand-protein random-negative score is below 0.5, which we have not yet explained. These numbers use our own GNN; the organizers' protocol is still unconfirmed. An earlier run on a truncated graph (10 items per list) gave different numbers and should be ignored.

### Leakage rules (from the literature survey, `documents/muse-1.md`)

Published biomedical link-prediction scores are often inflated. Our results only count if we follow these:

- **No reverse-edge leakage:** an edge and its reverse (B→A for A→B) must never fall in different splits. *(Implemented in `eval/split.py`: splits are by unordered pair.)*
- **No enrichment leakage:** any edge pulled from an external KG (OptimusKG, Monarch, Open Targets...) must be checked against the held-out set and dropped if it duplicates a held-out edge, including near-duplicates and reverse relations.
- **Hard negatives:** random negatives overstate performance (GNNs reported near 0.99 AUC fell to about 0.51 under degree-matched negatives). Also report degree-matched or two-hop negatives, and AUPRC as well as AUROC. *(Implemented in `eval/baseline.py`: random, same-type and degree-matched negatives are all reported.)*
- Always record the split, negative-sampling scheme and seed with every reported number.

## Design principles

- **The LLM proposes; sources decide.** The LLM may map, rate and propose edges, but every edge must trace to a retrievable source. No edges from model memory (that is the hallucination the challenge wants pruned).
- **Provenance on every edge:** source, evidence (PMID and a verbatim quote where available), confidence, method, timestamp.
- **No fine-tuning at first.** Use an off-the-shelf model with tools and a fixed output schema; retrieval is used for verification in the Clean step.
- **Thin harness:** a small tool-calling loop with a tool registry, schema-checked output, step/cost caps and a cache of every LLM call. No heavy agent framework.
- **Control cost:** run expensive per-edge LLM judging only on low-confidence edges.
- **Standards:** Biolink classes and predicates, validated with `kgx validate`; use as few, and as specific, classes as possible.

## Techniques to try

Ideas from the survey, roughly in priority order. All are unverified claims from a third-party report; check the source before relying on them.

1. Leakage-proof evaluation harness (undirected-aware split, enrichment overlap check, hard negatives).
2. Bulk ingest of OptimusKG, Open Targets and Monarch as Biolink-typed edges with provenance. Add one source at a time and keep it only if it helps.
3. Natural-language interface built from curated, parameterized query templates plus a query checker, rather than free text-to-Cypher (the survey cites 98% vs 85% accuracy).
4. Clean step: per-edge LLM judge grounded in retrieved evidence, with multi-model consensus for low-confidence edges.
5. Link-prediction boosters: an ablation of which enrichment edge types help, LLM text embeddings as node features, and node-type-aware negative sampling.
6. Maintain step: never delete contradicted edges; invalidate them with `valid_from` / `valid_to` columns.
7. Explainability: log supporting paths and a leave-one-edge-out attribution per predicted link; try short ontology-grounded explanation paths (NeRD-style, see `docs/literature.md`).
8. Use a hybrid (retrieval plus graph) for the natural-language interface, not raw KG lookup alone: a 2026 study reports KG-only retrieval at 50.9% vs 96.4% for RAG-only.

## Data sources and licenses

| Source | Use | Notes |
|---|---|---|
| Pharos (GraphQL API) | Baseline graph and seed data | License to confirm |
| OptimusKG | Large Biolink-aligned edge set | Some upstream terms are non-commercial |
| Open Targets | Scored target-disease evidence | CC0 |
| Monarch KG | Phenotype-disease edges | CC0 |
| PrimeKG | Skip | Superseded by OptimusKG |

Check each source for overlap with held-out edges and for redistribution terms before including it in the submission.

## Open questions for the organizers

- How are held-out edges chosen (random, time-split, cold-start), and which edge types?
- Is enrichment from KGs that may contain the held-out edges allowed, and how is leakage policed?
- Which GNN, settings and metrics are used for scoring, and what is the exact Pharos baseline?
- Are there graph size limits, and what format is required for submission and per-edge provenance?
- How are usability, explainability and standards scored (rubric, judges or automated checks)?

## Judging criteria

| Criterion | Weight |
|---|---|
| Usability for non-KG experts | 40% |
| Accuracy and pruning | 30% |
| Explainability (edge lineage) | 20% |
| Adherence to standards (Biolink, OBO) | 10% |

## Resources

- Literature and resource survey (unverified, from `documents/muse-1.md`): [docs/literature.md](docs/literature.md)
- [Pharos](https://pharos.nih.gov/about) · [Monarch KG registry](https://kghub.org/kg-registry/)
- [OptimusKG](https://github.com/mims-harvard/OptimusKG) · [TreeTag](https://github.com/valleyofdawn/TreeTag) · [PyG](https://github.com/pyg-team/pytorch_geometric)
- [AWS Neptune agent samples](https://github.com/aws-samples/amazon-neptune-samples/tree/master/neptune-prototyping-with-agents)

## License

MIT, see [LICENSE](LICENSE). Downloaded third-party data (Pharos, Open Targets, UniProt, GO, MONDO, Monarch, OptimusKG) keeps its own license and is not part of this repository.
