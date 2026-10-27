"""Run the ingest agent.

  python -m bioagent.ingest.run "Build a graph around EGFR and its partners" --out data/processed/agent_kg \\
      [--eval-graph data/processed/pharos --target-predicate biolink:interacts_with \\
       --target-evidence pharos:ppi --seed 0]

--eval-graph + --target-* make the agent leak-safe: edges on the held-out pairs of
that evaluation split (same split as eval.baseline) are dropped as they arrive.
Needs an API key in an environment variable (see --provider / --api-key-env).
"""
import argparse
import json
import os
import sys

from bioagent.eval.split import split_edges, pair_keys
from bioagent.ingest.harness import KGStore, anthropic_llm, openai_llm, run_agent
from bioagent.ingest.tools import TOOLS
from bioagent.schema.kg import read_kg, write_kg

SYSTEM = (
    "You build a biomedical knowledge graph by calling tools. Only add data through tools; "
    "never state or invent relationships from memory. Fetch the targets needed for the task, "
    "check kg_status, then reply with a short summary of what was added and anything that failed."
)


def heldout_keys(graph, predicate, evidence_prefix, seed):
    _, edges = read_kg(graph)
    mask = ((edges.predicate == predicate) & edges.evidence.str.startswith(evidence_prefix)).to_numpy()
    return split_edges(edges, mask, seed=seed).heldout_keys


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("--out", required=True)
    ap.add_argument("--provider", choices=["anthropic", "openai"], default="anthropic",
                    help="anthropic = Claude API; openai = any OpenAI-compatible endpoint (Vulcan, NRP, vLLM)")
    ap.add_argument("--base-url", help="for --provider openai, e.g. https://inference.vulcan.alliancecan.ca/v1 "
                                       "or https://ellm.nrp-nautilus.io/v1")
    ap.add_argument("--api-key-env", help="name of the environment variable holding the key "
                                          "(default ANTHROPIC_API_KEY, or LLM_API_KEY for --provider openai)")
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--max-steps", type=int, default=12)
    ap.add_argument("--max-tokens-total", type=int, default=200_000)
    ap.add_argument("--eval-graph")
    ap.add_argument("--target-predicate")
    ap.add_argument("--target-evidence", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--log", default="runs/ingest_log.jsonl")
    a = ap.parse_args()
    key_env = a.api_key_env or ("ANTHROPIC_API_KEY" if a.provider == "anthropic" else "LLM_API_KEY")
    if not os.environ.get(key_env):
        sys.exit(f"Set {key_env} first (export {key_env}=...). Never commit it.")
    if a.provider == "openai" and not a.base_url:
        sys.exit("--provider openai needs --base-url")
    keys = None
    if a.eval_graph:
        keys = heldout_keys(a.eval_graph, a.target_predicate, a.target_evidence, a.seed)
    store = KGStore(blocked_keys=keys)
    llm = anthropic_llm() if a.provider == "anthropic" else openai_llm(a.base_url, os.environ[key_env])
    res = run_agent(a.task, TOOLS, store, llm, model=a.model, system=SYSTEM,
                    max_steps=a.max_steps, max_total_tokens=a.max_tokens_total, log_path=a.log)
    nodes, edges = store.frames()
    write_kg(nodes, edges, a.out)
    print(json.dumps(res, indent=1))
