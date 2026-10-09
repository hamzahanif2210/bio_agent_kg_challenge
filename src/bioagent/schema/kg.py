"""Shared KG contract. Every module reads/writes these two tables (Parquet).

nodes: id (CURIE), category (Biolink class), name, source
edges: subject, predicate (Biolink), object, source, evidence, confidence,
       timestamp, method  -- provenance columns are mandatory (explainability).
"""
import pandas as pd

NODE_COLS = ["id", "category", "name", "source"]
EDGE_COLS = ["subject", "predicate", "object", "source", "evidence",
             "confidence", "timestamp", "method"]


def _check(df, cols, what):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{what} missing columns: {missing}")
    return df[cols]


def read_kg(path_prefix):
    return (pd.read_parquet(f"{path_prefix}.nodes.parquet"),
            pd.read_parquet(f"{path_prefix}.edges.parquet"))


def write_kg(nodes, edges, path_prefix):
    _check(nodes, NODE_COLS, "nodes").to_parquet(f"{path_prefix}.nodes.parquet")
    _check(edges, EDGE_COLS, "edges").to_parquet(f"{path_prefix}.edges.parquet")
