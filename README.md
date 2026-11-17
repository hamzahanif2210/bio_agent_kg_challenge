# Bio-Agent Knowledge Graph

**Team Random Agents:** Dr. Rizwan Qureshi, Dr. Hamza Hanif, Hara Moraitaki

An AI agent that builds, prunes, explains and answers questions over a Biolink-aligned biomedical knowledge graph made from [Pharos](https://pharos.nih.gov/about). Entry for the **Bio-Agent Knowledge Graph Construction Challenge** (open-source track), MIT licence.

[Paper](paper/main.pdf) · [Write-up](docs/WRITEUP.md) · [Methods and results](docs/README.md) · [Full graphs on Hugging Face](https://huggingface.co/datasets/hamzahanif/bioagent-kg-pharos) · [Demo pictures](demo/README.md)

## What it does

| Challenge goal | What we built | Result |
|---|---|---|
| **Ingest** | Tool-calling agent harness over the live Pharos API (LLM cache, step and token caps, leak guard) | 397,636 nodes, 3,091,048 edges, per-edge evidence |
| **Clean / prune** | Rules, CRAPome contaminants, obsolete-term remap, PubMed co-mention tiers, an LLM judge, and a second-opinion check on rescued links | 3,089,014 edges: **2,897,292 kept, 191,722 pruned**; every verdict has a rule, reason and confidence |
| **Filter and ask** | Plain-language question to the relevant subgraph, with an interactive picture (green kept, dashed red pruned) | Web page, CLI and JSON API |
| **Explain** | "Why does A connect to B?": sources, evidence, verdict, and paths through shared neighbours | `explain` command and `/api/explain` |
| **Maintain** | Re-fetch targets, report added, removed and re-scored edges | Self-test passes (20 added, 5 re-scored, 10 removed found); one live re-check of 400 random targets found no changes |
| **Standards** | Biolink 4.4.6 predicates, gene-protein split, OBO classes and IRIs on every node and edge | Real `kgx validate` 2.6.0 passes on the pruned graph |
| **Link prediction** | Leakage-safe split, hard negatives, 3 seeds, 156 ablation runs | With text and sequence features the pruned graph beats plain Pharos on all four edge types; the gain comes from the features (see [docs](docs/README.md)) |

## Agents and deployment

The query tools (ask, explain, multi-hop, ingest-csv) are packaged as one [Agent Skill](agents/bioagent-kg/SKILL.md) that pi, OpenClaw, NemoClaw and Hermes Agent read. Nothing is rewritten per harness: installing it means copying one folder.

| Where | How | Status |
|---|---|---|
| **NVIDIA Brev, NemoClaw + OpenClaw** | `bash deploy/brev/setup.sh nemoclaw`, then `bash deploy/brev/nemoclaw.sh openclaw` | Run on a fresh instance (4 vCPU, Nemotron 3.5 Super on NVIDIA endpoints); the agent answered the EGFR question correctly through the skill |
| **NVIDIA Brev, NemoClaw + Hermes** | same, `bash deploy/brev/nemoclaw.sh hermes` | Same instance type; same correct answer through Hermes's API |
| **pi** | `python scripts/compile_agent.py pi --user` | Run with a hosted model; answered correctly |
| **Render** | [render.yaml](render.yaml) + [Dockerfile](Dockerfile) | Web workbench and JSON API on the sample graph |

`deploy/brev/nemoclaw.sh` goes from a fresh Brev instance to a sandboxed agent in one command: it installs NemoClaw, creates the sandbox, allows only PyPI through its network policy, installs the skill and asks a test question. Your model key stays in an environment variable and never enters the repository. Details, logs and the fixes the stock Brev image needs: [deploy](deploy/README.md) and [agents](agents/README.md).

## Try it

The repository includes a sample graph (10 cancer proteins and their neighbours, 12,222 edges), so this works straight after cloning.

```bash
pip install -r requirements-serve.txt && export PYTHONPATH=src      # on the Alliance cluster: . ./env.sh
python -m bioagent --graph sample/sample.whole serve                 # web page at http://127.0.0.1:8000
python -m bioagent --graph sample/sample.whole ask --entities EGFR "non-small cell lung carcinoma" --hops 3 --min-conf 0.8
python -m bioagent --graph sample/sample.whole explain EGFR "non-small cell lung carcinoma"
python -m bioagent --graph sample/sample.whole ingest-csv sample/example_measurements.csv --out mine   # your own data
```

- **Ask** a name, a pair, or (with an LLM key) a full sentence. The LLM only picks out the names; every fact comes from the graph.
- **Explain** any link: source, evidence, verdict, rule, reason, and paths through shared neighbours.
- **Go deeper:** `--hops N` with `--min-conf`, `--types`, `--include-pruned`. Every picture has a cut-off slider that shows what a stricter or looser pruning rule would do.
- **Bring your own data:** `ingest-csv` (or the upload box on the web page) gives each row of your table a keep or prune verdict with a reason.
- **Full graphs** (3,089,014 edges; `whole.*` with every verdict, `pruned.*` with the 2,897,292 kept): `huggingface-cli download hamzahanif/bioagent-kg-pharos --repo-type dataset --local-dir exports` (about 9 GB; add `--include "pruned.*"` for the pruned graph only).

## Where things are

| Folder | What is in it |
|---|---|
| [src/bioagent](src/bioagent/README.md) | The package: ingest, clean, explain, ask, evaluate, export |
| [src/bioagent/qa](src/bioagent/qa/README.md) | Web workbench and JSON API |
| [src/bioagent/standards](src/bioagent/standards/README.md) | Biolink 4.4.6 and OBO standards |
| [agents](agents/README.md) | The Agent Skill for pi, OpenClaw, NemoClaw, Hermes |
| [deploy](deploy/README.md) | Render blueprint and NVIDIA Brev (NemoClaw, OpenClaw, Hermes) |
| [docs](docs/README.md) | Methods, pruning, evaluation protocol, results |
| [scripts](scripts/README.md) | Slurm jobs to rebuild and evaluate everything |
| [sample](sample/README.md), [demo](demo/README.md), [tests](tests/README.md) | Sample graph, interactive pictures, tests |

## License

MIT, see [LICENSE](LICENSE). Downloaded third-party data (Pharos, Open Targets, UniProt, GO, MONDO, Monarch, OptimusKG) keeps its own license and is not part of this repository.
