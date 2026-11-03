"""Link prediction with node features and context edges, scored exactly like eval.baseline (same hidden edges, same negatives).

  python -m bioagent.eval.featured PREFIX PREDICATE EVIDENCE --ref REF [--features text,seq] [--context pathway,gene_phenotype,...]
         [--model sage|gcn] [--decoder dot|mlp] [--seed S] [--epochs N]

Differences from the baseline: node input = learned embedding + a linear projection of each feature set; extra context edges
(data/context/context.*) join message passing after every pair equal to a held-out pair is dropped (leak check, count reported).
"""
import argparse
import json

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.metrics import average_precision_score, roc_auc_score
from torch_geometric.nn import GCNConv, SAGEConv

from bioagent.eval.baseline import Negatives
from bioagent.eval.split import pair_keys, split_edges
from bioagent.schema.kg import read_kg


class Net(torch.nn.Module):
    def __init__(self, n, feats, d=64, model="sage", decoder="dot"):
        super().__init__()
        self.emb = torch.nn.Embedding(n, d)
        self.rows = {k: torch.as_tensor(r) for k, (r, _) in feats.items()}
        self.X = {k: torch.as_tensor(x, dtype=torch.float32) for k, (_, x) in feats.items()}
        self.proj = torch.nn.ModuleDict({k: torch.nn.Linear(x.shape[1], d) for k, (_, x) in feats.items()})
        conv = SAGEConv if model == "sage" else GCNConv
        self.c1, self.c2 = conv(d, d), conv(d, d)
        self.mlp = torch.nn.Sequential(torch.nn.Linear(2 * d, d), torch.nn.ReLU(), torch.nn.Linear(d, 1)) if decoder == "mlp" else None

    def forward(self, ei):
        h = self.emb.weight
        for k in self.proj:
            h = h.index_add(0, self.rows[k], self.proj[k](self.X[k]))
        return self.c2(F.relu(self.c1(h, ei)), ei)

    def score(self, z, u, v):
        return (z[u] * z[v]).sum(1) if self.mlp is None else self.mlp(torch.cat([z[u] * z[v], (z[u] - z[v]).abs()], 1)).squeeze(1)


def run(prefix, predicate, evidence_prefix, ref, features=(), context=(), model="sage", decoder="dot", epochs=100, seed=0, dim=64,
        feat_dir="data/features", ctx_prefix="data/context/context"):
    torch.manual_seed(seed)
    nodes, edges_r = read_kg(ref)
    ix = {n: i for i, n in enumerate(nodes.id)}
    N = len(nodes)

    def load(edges):
        edges = edges[edges.subject.isin(ix) & edges.object.isin(ix)].reset_index(drop=True)
        return edges, ((edges.predicate == predicate) & edges.evidence.str.startswith(evidence_prefix)).to_numpy()

    edges_r, target_r = load(edges_r)
    sp = split_edges(edges_r, target_r, seed=seed)
    sr, orr = edges_r.subject.map(ix).to_numpy(), edges_r.object.map(ix).to_numpy()
    keep_r = np.ones(len(edges_r), bool); keep_r[sp.blocked] = False
    deg = np.bincount(np.r_[sr[keep_r], orr[keep_r]], minlength=N)
    cat = nodes.category.astype("category").cat.codes.to_numpy()
    known = np.minimum(sr, orr) * N + np.maximum(sr, orr)
    neg_eval = Negatives(cat, deg, known, N, np.random.default_rng(seed + 1000))
    neg_train = Negatives(cat, deg, known, N, np.random.default_rng(seed))
    evals = {(nm, md): neg_eval.sample(sr[idx], orr[idx], md) for nm, idx in (("test", sp.test), ("val", sp.val)) for md in ("random", "typed", "degree")}

    edges, target = (edges_r, target_r) if prefix == ref else load(read_kg(prefix)[1])
    keys = pair_keys(edges)
    keep = ~np.isin(keys, sp.heldout_keys)
    s, o = edges.subject.map(ix).to_numpy(), edges.object.map(ix).to_numpy()
    src, dst = s[keep], o[keep]
    out = {"seed": seed, "model": model, "decoder": decoder, "features": list(features), "context": list(context)}

    total = N
    if context:
        ce, cn = pd.read_parquet(f"{ctx_prefix}.edges.parquet"), pd.read_parquet(f"{ctx_prefix}.nodes.parquet")
        ce = ce[ce.evidence.isin([f"context:{c}" for c in context]) & ce.subject.isin(ix)]
        for nid in cn.id[cn.id.isin(set(ce.object)) & ~cn.id.isin(ix)]:
            ix[nid] = total; total += 1
        ce = ce[ce.object.isin(ix)]
        leak = np.isin(pair_keys(ce), sp.heldout_keys)          # context pair identical to a hidden edge: drop it
        out["context_edges"], out["context_leaked_dropped"] = int((~leak).sum()), int(leak.sum())
        ce = ce[~leak]
        cs, co = ce.subject.map(ix).to_numpy(), ce.object.map(ix).to_numpy()
        src, dst = np.r_[src, cs], np.r_[dst, co]
    ei = torch.from_numpy(np.stack([np.r_[src, dst], np.r_[dst, src]]))
    tr = np.flatnonzero(target & keep)
    tr_u, tr_v = s[tr], o[tr]

    feats = {}
    for f in features:
        z = np.load(f"{feat_dir}/{f}.npz", allow_pickle=True)
        rows = np.array([ix.get(i, -1) for i in z["ids"]]); ok = rows >= 0
        feats[f] = (rows[ok], z["X"][ok].astype(np.float32))
    net = Net(total, feats, dim, model, decoder)
    opt = torch.optim.Adam(net.parameters(), 1e-2)
    for _ in range(epochs):
        net.train(); opt.zero_grad()
        z = net(ei)
        nu, nv = neg_train.sample(tr_u, tr_v, "typed")
        pos, ng = net.score(z, tr_u, tr_v), net.score(z, nu, nv)
        F.binary_cross_entropy_with_logits(torch.cat([pos, ng]), torch.cat([torch.ones_like(pos), torch.zeros_like(ng)])).backward()
        opt.step()

    net.eval()
    out.update({"n_test": int(len(sp.test)), "n_train": int(len(tr))})
    with torch.no_grad():
        z = net(ei)
        for nm, idx in (("test", sp.test), ("val", sp.val)):
            ps = net.score(z, sr[idx], orr[idx]).numpy()
            for md in ("random", "typed", "degree"):
                nu, nv = evals[(nm, md)]
                ns = net.score(z, nu, nv).numpy()
                y, sc = np.r_[np.ones(len(ps)), np.zeros(len(ns))], np.r_[ps, ns]
                out[f"{nm}_{md}_auroc"] = round(float(roc_auc_score(y, sc)), 4)
                out[f"{nm}_{md}_ap"] = round(float(average_precision_score(y, sc)), 4)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("prefix"); ap.add_argument("predicate"); ap.add_argument("evidence_prefix", nargs="?", default="")
    ap.add_argument("--ref", required=True); ap.add_argument("--seed", type=int, default=0); ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--features", default=""); ap.add_argument("--context", default="")
    ap.add_argument("--model", default="sage"); ap.add_argument("--decoder", default="dot"); ap.add_argument("--dim", type=int, default=64)
    a = ap.parse_args()
    split = lambda t: tuple(x for x in t.split(",") if x)
    print(json.dumps(run(a.prefix, a.predicate, a.evidence_prefix, a.ref, split(a.features), split(a.context), a.model, a.decoder, a.epochs, a.seed, a.dim), indent=1))
