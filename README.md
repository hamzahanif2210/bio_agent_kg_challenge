# Bio-Agent Knowledge Graph

An AI agent that builds, prunes, explains and answers questions over a Biolink-aligned biomedical knowledge graph made from [Pharos](https://pharos.nih.gov/about). Entry for the **Bio-Agent Knowledge Graph Construction Challenge** (open-source track). Licence: MIT. Paper: [paper/main.pdf](paper/main.pdf). Write-up: [docs/WRITEUP.md](docs/WRITEUP.md).

**Contents:** 1 Executive summary · 2 Interactive workbench · 3 Ontological standards · 4 Render and GitHub deployment · 5 NVIDIA Brev (NemoClaw, OpenClaw, Hermes, pi) · 6 Server API · 7 Local development · 8 The challenge · 9 Methods, results and reference

## 1. Executive summary

Knowledge graphs are powerful in biology and hard to build and use. This project gives a non-expert one place to **ingest, prune, ask, explain and maintain** a graph, and shows how much of it to trust.

| Challenge goal | What we built | Result |
|---|---|---|
| **Ingest** | Tool-calling agent harness over the live Pharos API (LLM cache, step and token caps, leak guard) | 397,636 nodes, 3,091,048 edges, per-edge evidence |
| **Clean / prune** | Rules, CRAPome contaminants, obsolete-term remap, PubMed co-mention tiers, an LLM judge, and a second-opinion check on rescued links | 3,089,014 edges: **2,897,292 kept, 191,722 pruned**; every verdict has a rule, reason and confidence |
| **Filter and ask** | Plain-language question to the relevant subgraph, with an interactive picture (green kept, dashed red pruned) | Web page, CLI and JSON API |
| **Explain** | "Why does A connect to B?": sources, evidence, verdict, and paths through shared neighbours | `explain` command and `/api/explain` |
| **Maintain** | Re-fetch targets, report added, removed and re-scored edges | Self-test passes (20 added, 5 re-scored, 10 removed found); one live re-check of 400 random targets found no changes |
| **Standards** | Biolink 4.4.6 predicates, gene-protein split, OBO classes and IRIs on every node and edge | Real `kgx validate` 2.6.0 passes on the pruned graph |
| **Link prediction** | Leakage-safe split, hard negatives, 3 seeds, 156 ablation runs | With text and sequence features the pruned graph beats plain Pharos on all four edge types; the gain comes from the features (see section 9) |

Judging criteria and where to look: **Usability** (40%) sections 2, 6, 7; **Accuracy and pruning** (30%) section 9 and [the paper](paper/main.pdf); **Explainability** (20%) `explain` and the edge pop-ups; **Standards** (10%) section 3.

## 2. Core interactive workbench modules

| Module | What it does | Where |
|---|---|---|
| Web workbench | Type a name or a comma-separated pair; get the answer text plus an interactive picture. Click an edge to see its source, evidence, verdict and reason. Works offline (the graph library is bundled). | `python -m bioagent serve` (`qa/serve.py`, `qa/visual.py`) |
| Ask | Neighbours of a node, or the connection between two. With an LLM key, full sentences are accepted; the LLM only picks out the names, all facts come from the graph. | `python -m bioagent ask` (`qa/ask.py`) |
| Explain | Lineage of any link: source, evidence, method, timestamp, verdict, rule, reason, and up to five paths through shared neighbours (two hops) | `python -m bioagent explain A B` (`provenance/explain.py`) |
| Prune | Tiered pipeline described in section 9, re-runnable with one Slurm command | `clean/`, `scripts/run_pipeline.sbatch` |
| Maintain | Re-fetch and diff: added, removed, re-scored | `ingest/update.py`, `scripts/update.sbatch` |
| Export | KGX TSV and PyTorch Geometric, for the whole, pruned and enriched graphs | `export/`, `python -m bioagent export` |
| Review tools | Score pruning against any gold list (`scripts/score_gold.py`), plain CSV edge lists (`scripts/export_plain.py`), silver-standard checks (`scripts/silver_eval.py`, `scripts/silver_go.py`) | `scripts/` |
| Agent skill | One `SKILL.md` that lets an agent harness call all of the above | `agents/bioagent-kg/` (section 5) |

## 3. Adherence to ontological standards (OBO Foundry and Monarch Biolink)

- **Biolink 4.4.6.** Nodes use Biolink classes (`biolink:Protein`, `Gene`, `Disease`, `SmallMolecule`, `BiologicalProcess`, ...). Edges use specific Biolink predicates (`physically_interacts_with`, `actively_involved_in`, `capable_of`, `located_in`, `gene_associated_with_condition`, with `associated_with` and `related_to` as the general fall-backs) rather than one generic link; `standards/biolink.py` checks every predicate and its subject and object classes against the model.
- **Gene and protein are separate.** A gene-disease link is attached to the gene node, not the protein (`standards/genes.py`). Without the split the graph mixes the two, which Biolink does not allow.
- **OBO terms and IRIs.** `ontology_class`, `ontology_class_iri` and `iri` columns map each node class to an OBO term (protein `PR:000000001`, protein-coding gene `SO:0001217`, disease `MONDO:0000001`, GO branches, ...) and each CURIE to a resolvable IRI. A predicate with no declared OBO property stays empty: we do not invent mappings (`standards/ontology.py`).
- **Identifiers.** UniProtKB, MONDO, GO, ChEMBL and PHAROS CURIEs. Obsolete GO and MONDO terms are remapped to their replacement, the old id kept in `original_object`.
- **Real validator.** `kgx validate` 2.6.0 (run in a container, `scripts/kgx_container.sbatch`) first flagged one problem: Biolink's context has `PHAROS` but not `PHAROS.LIGAND`. The export now writes `PHAROS:`; the pruned graph then validates with no errors (`runs/kgx_validate_pruned.txt`).
- **Provenance on every edge:** `source`, `evidence`, `confidence`, `method`, `timestamp`, plus `verdict`, `rule`, `reason`.

## 4. Render blueprint (`render.yaml`) and GitHub deployment

The repository includes a [Dockerfile](Dockerfile) and a [Render Blueprint](render.yaml) that host the web workbench and JSON API on the bundled **sample graph** (about 12,000 edges; 10 well-known cancer proteins and their neighbours).

1. Push this repository to GitHub (a public fork or your own copy).
2. In Render choose **New + > Blueprint**, select the repository; Render reads `render.yaml` and builds the Dockerfile.
3. Optional, for full-sentence questions: in the Render dashboard set `LLM_BASE_URL` and `LLM_API_KEY`. Keys are never stored in the repository.
4. Open the service URL; `/healthz` is the health check.

The service binds `0.0.0.0` only because `HOST=0.0.0.0` is set in the blueprint; the default everywhere else is `127.0.0.1`. The free plan is enough for the sample graph. The full graph (about 3 million edges) needs several GB of memory, so host it on a larger plan or on Brev (section 5), with the exports downloaded from the project's Hugging Face dataset. Render has no authentication in front of this service: do not put private data in it.

## 5. Compiling to NVIDIA Brev (NemoClaw / OpenClaw / Nous Hermes) and the pi harness

The agent is packaged as one [Agent Skill](agents/bioagent-kg/SKILL.md): a folder with `SKILL.md` (YAML `name` and `description`, then instructions). pi, OpenClaw (and therefore NemoClaw, which runs OpenClaw or Hermes in an OpenShell sandbox) and Hermes Agent read this same format, so "compiling" means putting the folder where each one looks:

```bash
python scripts/compile_agent.py pi --user  # ~/.agents/skills/ (project .agents/skills/ needs /trust)        ([pi](https://github.com/earendil-works/pi))
python scripts/compile_agent.py openclaw   # skills/                (plain OpenClaw)
python scripts/compile_agent.py hermes     # ~/.hermes/skills/research/
# add --user to install for your whole account instead of this repository
# inside a NemoClaw sandbox use NemoClaw's own command instead:  nemoclaw <sandbox> skill install agents/bioagent-kg
```

### On NVIDIA Brev with NemoClaw (verified 2026-11-17)

Two commands on a fresh Brev instance (Ubuntu 24.04; a 4 vCPU / 16 GB CPU box is enough, because the model runs on NVIDIA's hosted endpoints):

```bash
bash deploy/brev/setup.sh nemoclaw            # host fixes, slim requirements, web service on port 8000
export NVIDIA_API_KEY=nvapi-...               # your key from build.nvidia.com; never commit it
export NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1 # only after reading NVIDIA's third-party software notice
bash deploy/brev/nemoclaw.sh openclaw         # or: hermes
```

`nemoclaw.sh` installs NemoClaw, onboards a sandbox for the chosen agent, allows PyPI only (`nemoclaw <sandbox> policy add pypi`; the sandbox blocks the internet by default), uploads the repo, installs the skill with `nemoclaw <sandbox> skill install`, builds a virtual environment inside the sandbox and asks one test question.

| Harness | Run on Brev | Test question: "How is EGFR connected to non-small cell lung carcinoma, and should I trust that link?" |
|---|---|---|
| **NemoClaw + OpenClaw** | Yes: NemoClaw v0.0.144, OpenShell 0.0.116, sandbox `bioagent`, model `nvidia/nemotron-3.5-super-vl-120b-a12b` | Correct: ran `explain`, reported the one direct edge (keep, 0.90, Open Targets 0.85), 43 shared neighbours, and noted it used the sample graph |
| **NemoClaw + Hermes** | Yes: same instance, sandbox `bioagent-hermes`, same model, asked through Hermes's OpenAI-compatible API (`127.0.0.1:8642`, model `hermes-agent`) | Correct: same facts and verdict |
| **pi** | Tested on a workstation, not on Brev (below) | Correct |

Instance: Brev `cpu-e2.4vcpu-16gb` (Nebius, USD 0.14 per hour). Transcripts are in `runs/brev/` (git-ignored).

**Problems found on the stock Brev image, now handled by `setup.sh`:** (1) `strings` is missing (install `binutils`); (2) the default `umask 0002` leaves the home folder group-writable, which the NemoClaw installer rejects as an "unsafe executable directory" (`umask 022` and `chmod go-w` on every folder under `~`, including `~/.local/bin`); (3) `ufw` blocks the OpenShell Docker bridge, so the sandbox cannot reach the gateway (`sudo ufw allow from 172.18.0.0/16 to 172.18.0.1 port 8080 proto tcp`, the rule NemoClaw itself suggests; nothing is opened to the internet). Also: Nemotron 3.5 rejects OpenClaw's `--thinking low` (use the default), and pip refuses the sandbox's system Python (use a virtual environment).

**pi (2026-11-16, workstation):** `npm install -g --ignore-scripts @earendil-works/pi-coding-agent` (Node 22.19+), with the NRP gpt-oss model through a `models.json` custom provider and `pi --skill agents/bioagent-kg --mode json "/skill:bioagent-kg ..."`. It ran our `explain` command and answered the same question correctly. pi skips a project's `.agents/skills/` until you trust the folder (`/trust`), which a non-interactive run cannot do, so use `--user` or `--skill <path>`; in that run the model first tried `pip install` and read a demo file before finding the command, so a small model is not always efficient. Run non-interactive pi with stdin closed (`< /dev/null`).

Notes: model keys go only into environment variables or each harness's own login step, never into this repository. NemoClaw sandboxes have network policies and an OpenShell gateway; pi has no permission system, so run it in a container. The skill tells the agent to answer only from the graph tools. Not tested: plain OpenClaw outside NemoClaw, and the full 3-million-edge graph on Brev (only the bundled sample graph was used).

## 6. Server API endpoints (`src/bioagent/qa/serve.py`)

Read-only, JSON, no authentication; the server listens on `127.0.0.1:8000` unless `--host` or `HOST` says otherwise (`--port` or `PORT` for the port).

| Method and path | Parameters | Returns |
|---|---|---|
| `GET /` | `q` (names, comma-separated, or a sentence if an LLM is set) | HTML page with the answer and picture |
| `GET /pic/<n>` | | the interactive picture made for a page request |
| `GET /healthz` | | `{"ok": true}` |
| `GET /api/stats` | | node, edge, kept and pruned counts |
| `GET /api/node` | `q` (id or exact name) | the node record |
| `GET /api/ask` | `q` | `{entities, answer, edges[]}`: best-supported kept neighbours (or the connection) with verdicts |
| `GET /api/explain` | `a`, `b` | direct edges and shared-neighbour paths between A and B with source, evidence, verdict, rule and reason |

Errors come back as `{"error": "..."}` with status 400 or 404. Example: `curl 'http://127.0.0.1:8000/api/explain?a=EGFR&b=non-small%20cell%20lung%20carcinoma'`.

## 7. Local development

### Quick start (no graph expertise needed)

Everything below runs from the repository root. The repository includes a small sample graph (`sample/`: 10 well-known cancer proteins and their neighbours, about 12,000 edges), so this works straight after cloning. The full graphs are downloaded separately (see "Full graphs").

```bash
. ./env.sh                                   # loads Python and the project (Alliance cluster); elsewhere: pip install -r requirements.txt and set PYTHONPATH=src
python -m bioagent --graph sample/sample.whole serve                  # web page: open http://127.0.0.1:8000, type BRCA1
python -m bioagent --graph sample/sample.whole ask --entities BRCA1 --html demo/brca1.html     # what is known about a protein or disease
python -m bioagent --graph sample/sample.whole ask --entities EGFR "non-small cell lung carcinoma" --html demo/egfr.html   # how two things connect
python -m bioagent --graph sample/sample.whole explain EGFR "non-small cell lung carcinoma"    # sources, evidence and verdict for each connection
```

With the full graph in place, drop `--graph sample/sample.whole` (the default is `data/processed/pharos_pruned_v3.whole`).

Open the `.html` file in a browser: nodes are coloured by type, green edges were kept and dashed red edges were pruned. **Click an edge** to see where it comes from and why it was kept or pruned.

To ask in a plain sentence, give the tool an LLM (it is only used to pick out the names; all facts come from the graph):

```bash
export LLM_BASE_URL=https://ellm.nrp-nautilus.io/v1 LLM_API_KEY=...      # your own key, never put it in the repo
python -m bioagent ask "How is EGFR connected to non-small cell lung carcinoma?"
```

Name a node closely: `lung cancer` and `non-small cell lung carcinoma` are different nodes. A partial name is accepted and the match is shown.

**Rebuild everything** from the fetched Pharos graph (rules, PubMed tiers, judge verdicts, exports) with one command: `sbatch scripts/run_pipeline.sbatch`. The slow inputs are separate jobs whose results are cached: `scripts/fetch_pharos_full.sbatch` (Pharos, hours), `scripts/pubmed_counts.sbatch` (PubMed counts, about 6 h, needs a free NCBI key in `NCBI_API_KEY`), `scripts/judge_tier3.sbatch` (LLM judge, about 7 h), `scripts/fetch_crapome.sbatch` (contaminant list, 20 min). **Keep up to date** with `sbatch scripts/update.sbatch 100`.

**What you get** (in `exports/`, git-ignored; rebuild with `python -m bioagent export`): `whole.*` has every Pharos edge with a keep / prune verdict, confidence and reason; `pruned.*` has only the kept edges. Each comes as KGX TSV (`*.kgx/nodes.tsv`, `edges.tsv`) and PyTorch Geometric (`*.pyg.pt`):

```python
import torch
d = torch.load("exports/pruned.pyg.pt", weights_only=False)
data = d["data"]                  # HeteroData; edge_attr columns are in d["edge_attr_columns"]
print(data.edge_types)            # e.g. ('Protein', 'physically_interacts_with', 'Protein')
d["node_ids"]["Protein"][0]       # CURIE of node 0 of that type
```


### Tests, setup and layout

Tests are plain Python scripts (no pytest needed): `for t in tests/test_*.py; do python $t || echo FAIL $t; done`. Setup, repository layout, the graph format and the evaluation protocol are described in the sections below ("Repository layout", "Graph format", "Setup", "Evaluation protocol"). On the Alliance cluster, heavy steps run as Slurm jobs (`scripts/*.sbatch`), not on the login node.

## 8. The challenge

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


## 9. Methods, results and reference

### How the graph was pruned

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

### LLM choice (measured 2026-10-27, NRP)

Three small tool-use tasks per model (`scripts/model_bakeoff.py`, results in `runs/bakeoff_nrp.json`): fetch two genes, fetch three genes, and recover from an unknown gene.

| Model | Passed | Avg seconds/task | Avg tokens/task |
|---|---|---|---|
| kimi | 3/3 | 16 | 1,615 |
| glm-5 | 3/3 | 17 | 2,271 |
| deepseek-v4-flash | 3/3 | 14 | 2,825 |
| minimax | 3/3 | 13 | 3,108 |
| gpt-oss | 3/3 | 8 | 2,652 |
| service (alias) | 3/3 | 13 | 2,805 |
| qwen3 | 3/3 | 281 | 3,102 |
| qwen3-small | 2/3 (one HTTP 500) | 5 | 2,698 |
| gemma | 0/3 (read timeouts) | 300 | n/a |

Default: **kimi** (fewest tokens), with **gpt-oss** when speed matters and **glm-5** as a backup. These tasks do not separate the top models, so a harder test is still needed. Run the agent on NRP with `sbatch scripts/run_agent_nrp.sbatch "TASK" OUT_PREFIX [MODEL]` (reads the token from a file inside the job).

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

### Does pruning or restructuring change link prediction? (hard-negative AUROC, 3 seeds)

| Target edges | Plain Pharos | Pruned v3 (shared test edges) | With gene nodes (own split) |
|---|---|---|---|
| protein-disease | 0.525 ± 0.000 | 0.538 ± 0.004 | 0.529 ± 0.001 |
| protein-GO term | 0.590 ± 0.003 | 0.583 ± 0.003 | 0.589 ± 0.015 |
| ligand-protein | 0.626 ± 0.011 | 0.609 ± 0.012 | 0.624 ± 0.013 |
| protein-protein | 0.686 ± 0.037 | 0.682 ± 0.034 | 0.656 ± 0.013 |

Pruned v3 is trained on the kept edges only but scored on the same hidden edges as plain Pharos (`--ref`), so the two columns answer the same questions (`scripts/baseline_array.sbatch data/processed/pharos_pruned_v3.pruned prunedv3 data/processed/pharos_evidence`). The gene-node graph changes the endpoints of the disease edges, so it cannot share the test set and uses its own split; treat differences below about 0.02 as noise. **Result: none of the differences is clearly larger than the seed spread, so pruning and the gene split neither help nor hurt link prediction with this model.** The graph is cleaner and better explained, but we cannot claim a prediction gain. Link prediction is also a weak yardstick for pruning: the organizers' gold set is the real judge.

**Enrichment tried: GO and MONDO hierarchies** (`enrich/ontology.py`: 30,500 GO and 16,565 MONDO `subclass_of` edges, 5,834 ancestor nodes added to pruned v3; same hidden edges). Hard-negative AUROC against pruned v3: protein-disease 0.535 ± 0.002 (0.538), protein-GO 0.579 ± 0.003 (0.583), ligand-protein 0.608 (0.609), protein-protein 0.681 (0.682). **No gain**: with learned embeddings and no node features the model does not exploit the hierarchy. Enrichment stays in the repo as a tested tool but is not part of the submitted graphs.

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

