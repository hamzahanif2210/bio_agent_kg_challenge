"""Link-prediction eval: GraphSAGE encoder + dot-product decoder.

Same function runs on the Pharos baseline and on the agent-built KG.
Held-out pairs (and their reverses / same-pair edges) are removed from the
message-passing graph. Test positives are scored against three negative
contracts: random, type-matched, and degree+type-matched (hard).

Usage:
  python -m bioagent.eval.baseline PREFIX PREDICATE [EVIDENCE_PREFIX] [--epochs N] [--seed S]
"""
import argparse
import json

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import average_precision_score, roc_auc_score
from torch_geometric.nn import SAGEConv

from bioagent.eval.split import split_edges
from bioagent.schema.kg import read_kg


class Net(torch.nn.Module):
    def __init__(self, n, d=64):
        super().__init__()
        self.emb = torch.nn.Embedding(n, d)
        self.c1, self.c2 = SAGEConv(d, d), SAGEConv(d, d)

    def forward(self, ei):
        return self.c2(F.relu(self.c1(self.emb.weight, ei)), ei)


class Negatives:
    """Corrupt the object end of a positive pair. Modes:
    random: any node; typed: same category; degree: same category and
    log2-degree bucket. Never returns a pair that is a known edge."""

    def __init__(self, cat, deg, known_codes, n, rng):
        self.n, self.rng = n, rng
        self.known = np.sort(known_codes)
        bucket = np.floor(np.log2(deg + 1)).astype(np.int64)
        self.group = {"typed": cat.astype(np.int64),
                      "degree": cat.astype(np.int64) * 64 + bucket}
        self.order, self.lut = {}, {}
        for m, g in self.group.items():
            order = np.argsort(g, kind="stable")
            uniq, st, ct = np.unique(g[order], return_index=True, return_counts=True)
            self.order[m] = order
            self.lut[m] = {int(k): (int(a), int(b)) for k, a, b in zip(uniq, st, ct)}

    def _is_known(self, u, v):
        lo, hi = np.minimum(u, v), np.maximum(u, v)
        code = lo * self.n + hi
        i = np.minimum(np.searchsorted(self.known, code), len(self.known) - 1)
        return self.known[i] == code

    def _draw(self, v, mode):
        if mode == "random":
            return self.rng.integers(0, self.n, size=len(v))
        lut = self.lut[mode]
        g = self.group[mode][v]
        st = np.array([lut[int(x)][0] for x in g])
        ct = np.array([lut[int(x)][1] for x in g])
        pick = st + (self.rng.random(len(v)) * ct).astype(np.int64)
        return self.order[mode][pick]

    def sample(self, u, v, mode, tries=10):
        u, v = np.asarray(u), np.asarray(v)
        neg = self._draw(v, mode)
        for _ in range(tries):
            bad = self._is_known(u, neg) | (neg == u)
            if not bad.any():
                break
            neg[bad] = self._draw(v[bad], mode)
        ok = ~(self._is_known(u, neg) | (neg == u))
        return u[ok], neg[ok]


def run(prefix, predicate, evidence_prefix="", epochs=100, seed=0, dim=64):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    nodes, edges = read_kg(prefix)
    ix = {n: i for i, n in enumerate(nodes.id)}
    N = len(nodes)
    edges = edges[edges.subject.isin(ix) & edges.object.isin(ix)].reset_index(drop=True)
    target = (edges.predicate == predicate) & edges.evidence.str.startswith(evidence_prefix)
    if target.sum() == 0:
        raise ValueError("no edges match the target selector")
    sp = split_edges(edges, target.to_numpy(), seed=seed)

    s = edges.subject.map(ix).to_numpy()
    o = edges.object.map(ix).to_numpy()
    keep = np.ones(len(edges), bool)
    keep[sp.blocked] = False  # held-out pairs never reach message passing
    ms, mo = s[keep], o[keep]
    ei = torch.from_numpy(np.stack([np.r_[ms, mo], np.r_[mo, ms]]))
    deg = np.bincount(np.r_[ms, mo], minlength=N)
    cat = nodes.category.astype("category").cat.codes.to_numpy()
    known = np.minimum(s, o) * N + np.maximum(s, o)  # all edges incl. held-out
    neg = Negatives(cat, deg, known, N, rng)

    tr_u, tr_v = s[sp.train], o[sp.train]
    model = Net(N, dim)
    opt = torch.optim.Adam(model.parameters(), 1e-2)
    for _ in range(epochs):
        model.train()
        opt.zero_grad()
        z = model(ei)
        nu, nv = neg.sample(tr_u, tr_v, "typed")
        pos = (z[tr_u] * z[tr_v]).sum(1)
        ng = (z[nu] * z[nv]).sum(1)
        logits = torch.cat([pos, ng])
        y = torch.cat([torch.ones_like(pos), torch.zeros_like(ng)])
        F.binary_cross_entropy_with_logits(logits, y).backward()
        opt.step()

    model.eval()
    out = {"seed": seed, "n_test": int(len(sp.test)), "n_train": int(len(sp.train)),
           "n_blocked": int(len(sp.blocked))}
    with torch.no_grad():
        z = model(ei)
        for name, idx in (("test", sp.test), ("val", sp.val)):
            pu, pv = s[idx], o[idx]
            ps = (z[pu] * z[pv]).sum(1).numpy()
            for mode in ("random", "typed", "degree"):
                nu, nv = neg.sample(pu, pv, mode)
                ns = (z[nu] * z[nv]).sum(1).numpy()
                y = np.r_[np.ones(len(ps)), np.zeros(len(ns))]
                sc = np.r_[ps, ns]
                out[f"{name}_{mode}_auroc"] = round(float(roc_auc_score(y, sc)), 4)
                out[f"{name}_{mode}_ap"] = round(float(average_precision_score(y, sc)), 4)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("prefix")
    ap.add_argument("predicate")
    ap.add_argument("evidence_prefix", nargs="?", default="")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    print(json.dumps(run(a.prefix, a.predicate, a.evidence_prefix, a.epochs, a.seed), indent=1))
