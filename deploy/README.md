# Deployment: Render and NVIDIA Brev

Hosting the web workbench (Render) and running the agent in NemoClaw, OpenClaw and Hermes sandboxes (NVIDIA Brev).

### Render blueprint (`render.yaml`) and GitHub deployment

The repository includes a [Dockerfile](../Dockerfile) and a [Render Blueprint](../render.yaml) that host the web workbench and JSON API on the bundled **sample graph** (about 12,000 edges; 10 well-known cancer proteins and their neighbours).

1. Push this repository to GitHub (a public fork or your own copy).
2. In Render choose **New + > Blueprint**, select the repository; Render reads `render.yaml` and builds the Dockerfile.
3. Optional, for full-sentence questions: in the Render dashboard set `LLM_BASE_URL` and `LLM_API_KEY`. Keys are never stored in the repository.
4. Open the service URL; `/healthz` is the health check.

The service binds `0.0.0.0` only because `HOST=0.0.0.0` is set in the blueprint; the default everywhere else is `127.0.0.1`. The free plan is enough for the sample graph. The full graph (about 3 million edges) needs several GB of memory, so host it on a larger plan or on Brev (below), with the exports downloaded from the project's Hugging Face dataset. Render has no authentication in front of this service: do not put private data in it.

### Compiling to NVIDIA Brev (NemoClaw / OpenClaw / Nous Hermes) and the pi harness

The agent is packaged as one [Agent Skill](../agents/bioagent-kg/SKILL.md): a folder with `SKILL.md` (YAML `name` and `description`, then instructions). pi, OpenClaw (and therefore NemoClaw, which runs OpenClaw or Hermes in an OpenShell sandbox) and Hermes Agent read this same format, so "compiling" means putting the folder where each one looks:

```bash
python scripts/compile_agent.py pi --user  # ~/.agents/skills/ (project .agents/skills/ needs /trust)        ([pi](https://github.com/earendil-works/pi))
python scripts/compile_agent.py openclaw   # skills/                (plain OpenClaw)
python scripts/compile_agent.py hermes     # ~/.hermes/skills/research/
## add --user to install for your whole account instead of this repository
## inside a NemoClaw sandbox use NemoClaw's own command instead:  nemoclaw <sandbox> skill install agents/bioagent-kg
```

#### On NVIDIA Brev with NemoClaw (verified 2026-11-17)

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
