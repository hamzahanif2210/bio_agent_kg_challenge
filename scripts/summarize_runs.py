"""Summarize runs/<tag>_<type>_s<seed>.json: mean +/- std over seeds. Usage: python scripts/summarize_runs.py [tag]"""
import glob, json, sys, re
import numpy as np
tag = sys.argv[1] if len(sys.argv) > 1 else "pharos"
rows = {}
for f in sorted(glob.glob(f"runs/{tag}_*_s*.json")):
    m = re.match(rf"runs/{tag}_(.+)_s(\d+)\.json", f)
    rows.setdefault(m.group(1), []).append(json.load(open(f)))
keys = ["test_random_auroc", "test_typed_auroc", "test_degree_auroc", "test_degree_ap"]
print(f"{'target':8} {'n_seeds':>7} {'n_test':>7} " + " ".join(f"{k.replace('test_',''):>18}" for k in keys))
for t, rs in rows.items():
    cells = [f"{np.mean([r[k] for r in rs]):.3f}+/-{np.std([r[k] for r in rs]):.3f}" for k in keys]
    print(f"{t:8} {len(rs):7d} {rs[0]['n_test']:7d} " + " ".join(f"{c:>18}" for c in cells))
