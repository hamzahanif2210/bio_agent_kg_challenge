"""Leakage-safe held-out edge split.

Leak rules (see README):
  * An edge and its reverse (B->A for A->B), and any other edge between the
    same two nodes, share one *unordered pair key* and always land in the same
    split.
  * Every edge that shares a key with a held-out edge is returned in
    `blocked` and must be removed from the message-passing graph and from
    anything an agent is allowed to see.
  * `leaked(external_edges, split)` flags enrichment edges that duplicate a
    held-out pair so they can be dropped before use.
"""
from dataclasses import dataclass

import numpy as np


def pair_keys(edges):
    """Unordered pair key per edge row, as an array of 'lo|hi' strings."""
    s = edges["subject"].astype(str).to_numpy()
    o = edges["object"].astype(str).to_numpy()
    lo = np.where(s < o, s, o)
    hi = np.where(s < o, o, s)
    return np.char.add(np.char.add(lo.astype(str), "|"), hi.astype(str))


@dataclass
class Split:
    test: np.ndarray     # row positions, one per unordered pair
    val: np.ndarray
    train: np.ndarray    # target-type rows not blocked (may include both directions)
    blocked: np.ndarray  # every row sharing a pair with test/val (remove these)
    heldout_keys: np.ndarray


def split_edges(edges, target_mask, val=0.1, test=0.1, seed=0):
    """`edges` must have a default RangeIndex. `target_mask` selects the edges
    of the type to predict. Splitting is by unordered pair."""
    rng = np.random.default_rng(seed)
    keys = pair_keys(edges)
    target_pos = np.flatnonzero(np.asarray(target_mask))
    ukeys, first = np.unique(keys[target_pos], return_index=True)
    order = rng.permutation(len(ukeys))
    n_te, n_va = int(len(ukeys) * test), int(len(ukeys) * val)
    te_k, va_k = ukeys[order[:n_te]], ukeys[order[n_te:n_te + n_va]]
    heldout = np.concatenate([te_k, va_k])

    rep = target_pos[first]  # one representative row per unique pair
    in_te = np.isin(keys[rep], te_k)
    in_va = np.isin(keys[rep], va_k)
    blocked = np.flatnonzero(np.isin(keys, heldout))
    train = target_pos[~np.isin(keys[target_pos], heldout)]
    return Split(rep[in_te], rep[in_va], train, blocked, heldout)


def leaked(external_edges, split):
    """Boolean mask over `external_edges`: True where the edge duplicates a
    held-out pair (either direction, any predicate). Drop these."""
    return np.isin(pair_keys(external_edges), split.heldout_keys)
