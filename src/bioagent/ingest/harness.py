"""Thin ingest-agent harness: a tool-calling loop around the Claude API.

Design (see README "Design principles"):
  * The LLM only chooses tools and parameters. Edges come from tools that
    query real sources; they go straight into a KGStore, never through the
    LLM's text, so nothing is invented from model memory.
  * KGStore validates every edge (Biolink predicate, provenance fields,
    confidence in [0,1]) and drops edges that duplicate a held-out pair.
  * Every LLM call is cached on disk (re-runs are free and reproducible) and
    every step is logged to JSONL (tool, inputs, result summary, tokens).
  * Hard caps on steps and total tokens.

The LLM is injected as a callable so tests run without an API key.
"""
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from bioagent.eval.split import pair_keys
from bioagent.schema.kg import EDGE_COLS, NODE_COLS

REQUIRED_EDGE_FIELDS = ["subject", "predicate", "object", "source", "evidence", "method"]


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    fn: Callable  # fn(store, **kwargs) -> str  (text shown to the LLM)

    def spec(self):
        return {"name": self.name, "description": self.description,
                "input_schema": self.input_schema}


class KGStore:
    """Accumulates validated nodes/edges. `blocked_keys` are held-out unordered
    pair keys (from eval.split); edges on those pairs are dropped on entry."""

    def __init__(self, blocked_keys=None):
        self.nodes = {}
        self.edges = {}
        self.blocked = np.asarray(blocked_keys if blocked_keys is not None else [], dtype=str)
        self.stats = {"added": 0, "dup": 0, "leak": 0, "invalid": 0}

    def add(self, nodes_df, edges_df):
        before = self.stats.copy()
        for r in nodes_df.to_dict("records"):
            self.nodes.setdefault(r["id"], {c: r.get(c) for c in NODE_COLS})
        if len(edges_df):
            leak = np.isin(pair_keys(edges_df), self.blocked) if len(self.blocked) else np.zeros(len(edges_df), bool)
            for r, is_leak in zip(edges_df.to_dict("records"), leak):
                if is_leak:
                    self.stats["leak"] += 1
                elif not self._valid(r):
                    self.stats["invalid"] += 1
                else:
                    k = (r["subject"], r["predicate"], r["object"], r["source"])
                    if k in self.edges:
                        self.stats["dup"] += 1
                    else:
                        self.edges[k] = {c: r.get(c) for c in EDGE_COLS}
                        self.stats["added"] += 1
        return {k: self.stats[k] - before[k] for k in self.stats}

    @staticmethod
    def _valid(r):
        if any(r.get(f) in (None, "") for f in REQUIRED_EDGE_FIELDS):
            return False
        if not str(r["predicate"]).startswith("biolink:"):
            return False
        c = r.get("confidence")
        if c is None:
            return False
        c = float(c)
        return c != c or 0.0 <= c <= 1.0  # NaN = source reports no score

    def frames(self):
        edges = pd.DataFrame(self.edges.values(), columns=EDGE_COLS)
        nodes = pd.DataFrame(self.nodes.values(), columns=NODE_COLS)
        have = set(nodes.id)
        ok = edges.subject.isin(have) & edges.object.isin(have)  # no dangling edges
        return nodes, edges[ok].reset_index(drop=True)

    def summary(self):
        n, e = self.frames()
        return {"nodes": len(n), "edges": len(e), **self.stats}


def anthropic_llm(client=None):
    """Default LLM callable. Needs ANTHROPIC_API_KEY."""
    import anthropic
    client = client or anthropic.Anthropic()

    def call(model, system, messages, tools, max_tokens):
        r = client.messages.create(model=model, system=system, messages=messages,
                                   tools=tools, max_tokens=max_tokens)
        return r.model_dump(mode="json")
    return call


def _clean(blocks):
    """Keep only the fields the API accepts back in assistant messages."""
    out = []
    for b in blocks:
        if b["type"] == "text":
            out.append({"type": "text", "text": b["text"]})
        elif b["type"] == "tool_use":
            out.append({"type": "tool_use", "id": b["id"], "name": b["name"], "input": b["input"]})
    return out


def run_agent(task, tools, store, llm, model="claude-sonnet-5-5", system="",
              max_steps=12, max_total_tokens=200_000, max_tokens=2048,
              cache_dir="data/cache/llm", log_path=None):
    registry = {t.name: t for t in tools}
    specs = [t.spec() for t in tools]
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "a") if log_path else None
    messages = [{"role": "user", "content": task}]
    used, final_text, stop = 0, "", "max_steps"
    for step in range(max_steps):
        key = hashlib.sha256(json.dumps([model, system, messages, specs, max_tokens],
                                        sort_keys=True).encode()).hexdigest()
        f = cache / f"{key}.json"
        cached = f.exists()
        if cached:
            resp = json.loads(f.read_text())
        else:
            resp = llm(model, system, messages, specs, max_tokens)
            f.write_text(json.dumps(resp))
        usage = resp.get("usage") or {}
        used += (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0)
        content = _clean(resp["content"])
        messages.append({"role": "assistant", "content": content})
        text = " ".join(b["text"] for b in content if b["type"] == "text")
        entry = {"ts": time.time(), "step": step, "cached": cached,
                 "tokens": usage, "text": text, "tool_calls": []}
        calls = [b for b in content if b["type"] == "tool_use"]
        if resp.get("stop_reason") != "tool_use" or not calls:
            final_text, stop = text, "done"
            if log:
                log.write(json.dumps(entry) + "\n")
            break
        results = []
        for b in calls:
            tool = registry.get(b["name"])
            try:
                if tool is None:
                    raise KeyError(f"unknown tool {b['name']}")
                out, err = tool.fn(store, **b["input"]), False
            except Exception as e:  # report to the model instead of crashing
                out, err = f"ERROR: {type(e).__name__}: {e}", True
            out = str(out)[:4000]
            entry["tool_calls"].append({"name": b["name"], "input": b["input"],
                                        "error": err, "result": out[:500]})
            results.append({"type": "tool_result", "tool_use_id": b["id"],
                            "content": out, "is_error": err})
        messages.append({"role": "user", "content": results})
        if log:
            log.write(json.dumps(entry) + "\n")
        if used >= max_total_tokens:
            stop = "token_cap"
            break
    if log:
        log.close()
    return {"final_text": final_text, "stop": stop, "tokens": used, "kg": store.summary()}
