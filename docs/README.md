# Methods, results and reference

How the graph was built and pruned, how it is evaluated, and the numbers. Plain-language goals and the calendar are in [what_we_need_to_do.md](what_we_need_to_do.md); the write-up is [WRITEUP.md](WRITEUP.md).


## How the graph was pruned

| Step | What it does | Edges decided |
|---|---|---|
| Rules (v1) | Protein interactions by score and number of supporting databases; disease links by independent confirmation (Open Targets) and database count; GO links by UniProt annotations and the GO hierarchy; obsolete terms | all |
| Obsolete terms | An obsolete GO or MONDO term that names a replacement is a rename, so the edge is moved to the replacement (old id kept in `original_object`); with no replacement it is pruned | 10,006 remapped |
| CRAPome | BioPlex-only interactions with a frequent AP-MS contaminant are pruned | 4,574 pruned |
| PubMed tiers | Weakly supported disease links: no PubMed article mentioning both is a confirmed prune; 10 or more co-mentions is a rescue | 139,301 pruned, 10,078 rescued |
| LLM judge (gpt-oss) | Reads PubMed titles, the protein's UniProt function and the disease definition; a keep needs `p_real` of at least 0.8 | 5,000 judged: 2,595 rescued, 1,052 pruned |

GO links not among UniProt's annotations or their parent terms are kept at low confidence (0.45, rule `go_unsupported`, 68,198 edges, flagged `needs_review`): eight blind LLM reviewers rated most of them plausible, so absence from UniProt is weak evidence only.

Final graph: 3,089,014 edges, of which 2,897,292 are kept and 191,722 pruned. About 30,000 weak disease links with 1 to 9 co-mentions were not judged; they keep the rule-based verdict and are flagged `needs_review`. The numeric priors are heuristics, not calibrated against the organizers' gold set. Every verdict carries `rule`, `reason` and `verdict_confidence`.

## Approach

The agent follows the challenge loop:

| Step | Goal | Module |
|---|---|---|
| **Ingest** | Pull disease, drug, gene, protein and ontology context from public sources; map to Biolink classes and OBO URIs | `src/bioagent/ingest/` |
| **Filter** | Turn a natural-language question into a graph query for the relevant subgraph | `src/bioagent/qa/` |
| **Clean** | Score edge confidence and prune erroneous or contextually wrong links | `src/bioagent/clean/` |
| **Limit** | Cap graph size for performance | `src/bioagent/clean/` |
| **Maintain** | Re-run to pick up new literature/data | `src/bioagent/ingest/update.py` |

Every edge carries provenance (source, evidence, confidence, method, timestamp), so any link can be traced back with `provenance/explain.py`.

### Running the ingest agent with an LLM

Keys live in environment variables only (never in the repo).

```bash
# Alliance Vulcan (OpenAI-compatible; models with tool calling include gpt-oss-120b, qwen35-122b)
export LLM_API_KEY=...        # key from the Alliance Aleph docs (docs.alliancecan.ca/wiki/aleph)
python -m bioagent.ingest.run "Build a graph around EGFR and its interaction partners" --out data/processed/agent_kg \
    --provider openai --base-url https://inference.vulcan.alliancecan.ca/v1 --model gpt-oss-120b

# NRP managed LLMs (OpenAI-compatible; token from https://nrp.ai/llmtoken)
python -m bioagent.ingest.run "..." --out data/processed/agent_kg \
    --provider openai --base-url https://ellm.nrp-nautilus.io/v1 --model qwen3

# Claude API
export ANTHROPIC_API_KEY=...
python -m bioagent.ingest.run "..." --out data/processed/agent_kg
```

Cold models can answer `503 model_scaled_to_zero` on the first request; the client retries automatically.

### LLM choice

Each model ran three small tool-use tasks with our harness (`scripts/model_bakeoff.py`): fetch two genes, fetch three genes, and recover from an unknown gene. Models that passed all three:

| Model | Avg seconds/task | Avg tokens/task |
|---|---|---|
| kimi | 16 | 1,615 |
| glm-5 | 17 | 2,271 |
| deepseek-v4-flash | 14 | 2,825 |
| minimax | 13 | 3,108 |
| gpt-oss | 8 | 2,652 |
| qwen3 | 281 | 3,102 |

Default: **kimi** (fewest tokens), **gpt-oss** when speed matters, **glm-5** as a backup. Run the ingest agent with `sbatch scripts/run_agent_nrp.sbatch "TASK" OUT_PREFIX [MODEL]` (the key is read from a file inside the job).

## Graph format (the shared contract)

Graphs are stored as two Parquet files: `<prefix>.nodes.parquet` and `<prefix>.edges.parquet`.

- **nodes:** `id` (CURIE), `category` (Biolink class), `name`, `source`
- **edges:** `subject`, `predicate` (Biolink), `object`, `source`, `evidence`, `confidence`, `timestamp`, `method`

Use `read_kg` / `write_kg` from `bioagent.schema.kg`; they reject tables missing any required column.

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

### Does pruning or restructuring change link prediction? (hard-negative AUROC, 3 seeds)

| Target edges | Plain Pharos | Pruned v3 (shared test edges) | With gene nodes (own split) |
|---|---|---|---|
| protein-disease | 0.525 ± 0.000 | 0.538 ± 0.004 | 0.529 ± 0.001 |
| protein-GO term | 0.590 ± 0.003 | 0.583 ± 0.003 | 0.589 ± 0.015 |
| ligand-protein | 0.626 ± 0.011 | 0.609 ± 0.012 | 0.624 ± 0.013 |
| protein-protein | 0.686 ± 0.037 | 0.682 ± 0.034 | 0.656 ± 0.013 |

Pruned v3 is trained on the kept edges only but scored on the same hidden edges as plain Pharos (`--ref`), so the two columns answer the same questions (`scripts/baseline_array.sbatch data/processed/pharos_pruned_v3.pruned prunedv3 data/processed/pharos_evidence`). The gene-node graph changes the endpoints of the disease edges, so it cannot share the test set and uses its own split; treat differences below about 0.02 as noise. **Result: none of the differences is clearly larger than the seed spread, so pruning and the gene split neither help nor hurt link prediction with this model.** The graph is cleaner and better explained, but we cannot claim a prediction gain. Link prediction is also a weak yardstick for pruning: the organizers' gold set is the real judge.

**Enrichment tried: GO and MONDO hierarchies** (`enrich/ontology.py`: 30,500 GO and 16,565 MONDO `subclass_of` edges, 5,834 ancestor nodes added to pruned v3; same hidden edges). Hard-negative AUROC against pruned v3: protein-disease 0.535 ± 0.002 (0.538), protein-GO 0.579 ± 0.003 (0.583), ligand-protein 0.608 (0.609), protein-protein 0.681 (0.682). **No gain**: with learned embeddings and no node features the model does not exploit the hierarchy. Enrichment stays in the repo as a tested tool but is not part of the submitted graphs.

### How the evaluation avoids leakage

- **Reverse edges stay together.** An edge and its reverse (B to A for A to B) always land in the same split, because splits are made on unordered pairs (`eval/split.py`).
- **The agent never sees the hidden edges.** The graph is built from training edges only, and a guard in the ingest step rejects any edge from the test set (`train_only`).
- **Outside sources are checked.** An edge brought in from another knowledge graph is compared with the held-out set and dropped if it duplicates one, in either direction (`leaked()` in `eval/split.py`; the feature runs report how many were dropped).
- **Hard negatives.** Random negatives make scores look much better than they are, so we also report negatives matched on node type and on degree (`eval/baseline.py`), and AP as well as AUROC.
- **Every number is reproducible.** Each reported result records its split, negative sampling scheme and seed.

## Design principles

- **The LLM proposes; sources decide.** The LLM may map, rate and propose edges, but every edge must trace to a retrievable source. No edges from model memory (that is the hallucination the challenge wants pruned).
- **Provenance on every edge:** source, evidence (PMID and a verbatim quote where available), confidence, method, timestamp.
- **No fine-tuning at first.** Use an off-the-shelf model with tools and a fixed output schema; retrieval is used for verification in the Clean step.
- **Thin harness:** a small tool-calling loop with a tool registry, schema-checked output, step/cost caps and a cache of every LLM call. No heavy agent framework.
- **Control cost:** run expensive per-edge LLM judging only on low-confidence edges.
- **Standards:** Biolink classes and predicates, validated with `kgx validate`; use as few, and as specific, classes as possible.

## Data sources and licenses

| Source | Use | Notes |
|---|---|---|
| Pharos (GraphQL API) | Baseline graph and seed data | License to confirm |
| OptimusKG | Large Biolink-aligned edge set | Some upstream terms are non-commercial |
| Open Targets | Scored target-disease evidence | CC0 |
| Monarch KG | Phenotype-disease edges | CC0 |
| PrimeKG | Skip | Superseded by OptimusKG |

Check each source for overlap with held-out edges and for redistribution terms before including it in the submission.

## Resources

- Literature and resource survey (unverified, from `documents/muse-1.md`): [docs/literature.md](literature.md)
- [Pharos](https://pharos.nih.gov/about) · [Monarch KG registry](https://kghub.org/kg-registry/)
- [OptimusKG](https://github.com/mims-harvard/OptimusKG) · [TreeTag](https://github.com/valleyofdawn/TreeTag) · [PyG](https://github.com/pyg-team/pytorch_geometric)
- [AWS Neptune agent samples](https://github.com/aws-samples/amazon-neptune-samples/tree/master/neptune-prototyping-with-agents)
