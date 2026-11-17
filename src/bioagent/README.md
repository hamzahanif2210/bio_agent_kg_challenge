# bioagent: the package

## What you can do

| Module | What it does | Where |
|---|---|---|
| Web workbench | Type a name or a comma-separated pair; get the answer text plus an interactive picture. Click an edge to see its source, evidence, verdict and reason. Works offline (the graph library is bundled). | `python -m bioagent serve` (`qa/serve.py`, `qa/visual.py`) |
| Ask | Neighbours of a node, or the connection between two. With an LLM key, full sentences are accepted; the LLM only picks out the names, all facts come from the graph. | `python -m bioagent ask` (`qa/ask.py`) |
| Multi-hop with filters | Everything within N hops of a node, or the shortest paths of up to N hops between two, strongest first. Filters: kept edges only, minimum confidence, node classes to pass through. The picture and the web page take the same options. | `ask --hops 3 --min-conf 0.8 --types Protein Disease` (`qa/hops.py`) |
| Bring your own data | Add a CSV of your own measured relationships (`subject`, `object`, optional predicate, score, PMID, source). Names are matched to graph nodes, each row becomes an edge with provenance and gets a keep/prune verdict with a stated reason (score, PMID, whether Pharos already supports it, shared neighbours, unknown entity). | `python -m bioagent ingest-csv my.csv`, or the upload box on the web page (`ingest/csv_ingest.py`) |
| Cut-off slider | In every picture, drag a confidence cut-off: edges below it turn red and dashed, with a live count of kept and pruned; one click returns to the pipeline's own verdicts. | `qa/visual.py` |
| Explain | Lineage of any link: source, evidence, method, timestamp, verdict, rule, reason, and up to five paths through shared neighbours (two hops) | `python -m bioagent explain A B` (`provenance/explain.py`) |
| Prune | Tiered pipeline described in section 9, re-runnable with one Slurm command | `clean/`, `scripts/run_pipeline.sbatch` |
| Maintain | Re-fetch and diff: added, removed, re-scored | `ingest/update.py`, `scripts/update.sbatch` |
| Export | KGX TSV and PyTorch Geometric, for the whole, pruned and enriched graphs | `export/`, `python -m bioagent export` |
| Review tools | Score pruning against any gold list (`scripts/score_gold.py`), plain CSV edge lists (`scripts/export_plain.py`), silver-standard checks (`scripts/silver_eval.py`, `scripts/silver_go.py`) | `scripts/` |
| Agent skill | One `SKILL.md` that lets an agent harness call all of the above | `agents/bioagent-kg/` (section 5) |

## Layout

| Folder | Contents |
|---|---|
| `schema/kg.py` | The shared graph contract: nodes and edges as Parquet, mandatory provenance columns |
| `ingest/` | `harness.py` tool-calling loop (LLM cache, step and token caps, leak guard), `tools.py` and `pharos.py` (Pharos GraphQL), `run.py` agent CLI, `update.py` maintenance, `csv_ingest.py` your own tables |
| `clean/` | `prune.py` rules, `pubmed_tiers.py` PubMed co-mention tiers, `judge.py` and `apply_judge.py` LLM judge, `run_prune.py` |
| `enrich/ontology.py` | GO and MONDO hierarchy edges |
| `standards/` | Biolink predicates and classes, gene-protein split, OBO IRIs ([details](standards/README.md)) |
| `provenance/explain.py` | "Why does A connect to B?" lineage |
| `qa/` | `ask.py`, `hops.py`, `serve.py`, `visual.py` ([web API](qa/README.md)) |
| `eval/` | `split.py` leakage-safe split, `baseline.py` and `featured.py` GNN link prediction |
| `export/` | KGX TSV and PyTorch Geometric exports |

Graph format: `<prefix>.nodes.parquet` (`id`, `category`, `name`, `source`) and `<prefix>.edges.parquet` (`subject`, `predicate`, `object`, `source`, `evidence`, `confidence`, `timestamp`, `method`, `attributes`, plus `verdict`, `verdict_confidence`, `reason`, `rule` on pruned graphs). Read and write with `bioagent.schema.kg`.
