"""Run the ingest agent.

  python -m bioagent.ingest.run "Build a graph around EGFR and its partners" --out data/processed/agent_kg \\
      [--eval-graph data/processed/pharos --target-predicate biolink:interacts_with \\
       --target-evidence pharos:ppi --seed 0]

--eval-graph + --target-* make the agent leak-safe: edges on the held-out pairs of
that evaluation split (same split as eval.baseline) are dropped as they arrive.
Needs ANTHROPIC_API_KEY.
"""
import argparse
import json
import os
import sys

from bioagent.eval.split import split_edges, pair_keys
from bioagent.ingest.harness import KGStore, anthropic_llm, run_agent
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
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--max-steps", type=int, default=12)
    ap.add_argument("--max-tokens-total", type=int, default=200_000)
    ap.add_argument("--eval-graph")
    ap.add_argument("--target-predicate")
    ap.add_argument("--target-evidence", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--log", default="runs/ingest_log.jsonl")
    a = ap.parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY first (export ANTHROPIC_API_KEY=...). Never commit it.")
    keys = None
    if a.eval_graph:
        keys = heldout_keys(a.eval_graph, a.target_predicate, a.target_evidence, a.seed)
    store = KGStore(blocked_keys=keys)
    res = run_agent(a.task, TOOLS, store, anthropic_llm(), model=a.model, system=SYSTEM,
                    max_steps=a.max_steps, max_total_tokens=a.max_tokens_total, log_path=a.log)
    nodes, edges = store.frames()
    write_kg(nodes, edges, a.out)
    print(json.dumps(res, indent=1))
