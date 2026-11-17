# scripts: Slurm jobs and helpers

Heavy steps run as Slurm jobs, never on a login node. Every `.sbatch` file starts with a comment saying what it does and how to call it. Keys are always read from files inside the job, never from a command line.

## Rebuild everything

`sbatch scripts/run_pipeline.sbatch` runs the whole pipeline from the fetched Pharos graph (rules, PubMed tiers, judge verdicts, exports, no LLM calls). Keep it up to date with `sbatch scripts/update.sbatch 100`. The slow inputs are separate jobs whose results are cached:

| Step | Scripts |
|---|---|
| Fetch Pharos (hours, resumable) | `fetch_pharos_full.sbatch`, `fetch_pharos_evidence.sbatch`, `fetch_pharos.sbatch` |
| Other sources (GO, MONDO, UniProt, Open Targets, Monarch, OptimusKG) | `download_sources.sh`, `download_sources.sbatch`, `fetch_crapome.py` and `.sbatch` |
| Pruning | `run_prune.sbatch` (rules), `pubmed_counts.py` and `pubmed_tiers.sbatch` (PubMed, about 6 h), `judge_tier3.py` and `.sbatch` (LLM judge, about 7 h), `apply_judge.sbatch`, `rebuild_and_prune.sbatch`, `genes.sbatch` (gene-protein split) |
| Maintain | `update.sbatch`, `update_selftest.sbatch` |
| Export | `export.sbatch`, `export_enriched.sbatch`, `export_plain.py`, `upload_hf.py` and `.sbatch` |

## Evaluate

| Purpose | Scripts |
|---|---|
| Link prediction | `baseline_array.sbatch` (4 edge types x 3 seeds), `featured_array.sbatch` (156 ablation runs), `enrich_eval.sbatch`, `build_features.*`, `build_context.*`, `summarize_runs.py`, `summarize_featured.py` |
| Pruning quality | `score_gold.py` (any labelled edge list), `silver_eval.*`, `silver_go.*`, `review_sheet.*`, `llm_review*`, `go_sample.*`, `judge_sample.*`, `evidence_stats.py` |
| Standards | `validate_biolink.*`, `kgx_container.sbatch` (real `kgx validate`) |

## Agent and demos

`compile_agent.py` (install the skill for pi, OpenClaw, NemoClaw, Hermes), `run_agent_nrp.sbatch` (ingest agent run), `model_bakeoff.py`, `ask_demo.sbatch`, `explain_demo.py`, `make_sample.*` (the sample graph), `clean_checkout_test.sbatch` (fresh-clone test).
