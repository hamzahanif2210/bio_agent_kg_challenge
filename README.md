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

Judging criteria and where to look: **Usability** (40%) [src/bioagent](src/bioagent/README.md) and [qa](src/bioagent/qa/README.md); **Accuracy and pruning** (30%) [docs](docs/README.md) and [the paper](paper/main.pdf); **Explainability** (20%) `explain` and the edge pop-ups; **Standards** (10%) [standards](src/bioagent/standards/README.md).

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
