#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=plain_gold
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --output=logs/plain_gold_%j.out
# Writes the plain edge lists, then checks score_gold.py on a labelled sample made from the graph itself (format test, not a result).
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u -W ignore scripts/export_plain.py
python -W ignore - <<'P'
import pandas as pd
e = pd.read_parquet("data/processed/pharos_pruned_v3.whole.edges.parquet", columns=["subject", "object", "verdict"]).sample(2000, random_state=0)
e["label"] = e.verdict; e[["subject", "object", "label"]].to_csv("runs/_gold_format_test.tsv", sep="\t", index=False)
P
python -u -W ignore scripts/score_gold.py runs/_gold_format_test.tsv --out runs/_gold_format_test.json | tail -n 12
