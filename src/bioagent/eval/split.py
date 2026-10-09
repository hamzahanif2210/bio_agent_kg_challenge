"""Fixed held-out edge split. Test edges must NEVER be used by ingest/clean
(leak guard: agents get train edges only; see `train_only`)."""
import numpy as np


def split_edges(edges, target_predicate, val=0.1, test=0.1, seed=0):
    rng = np.random.default_rng(seed)
    idx = edges.index[edges.predicate == target_predicate].to_numpy()
    rng.shuffle(idx)
    n_te, n_va = int(len(idx) * test), int(len(idx) * val)
    return idx[:n_te], idx[n_te:n_te + n_va], idx[n_te + n_va:]


def train_only(edges, test_idx, val_idx):
    return edges.drop(index=list(test_idx) + list(val_idx))
