#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=apply_judge
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=24G
#SBATCH --output=logs/apply_judge_%j.out
# Fold tier-3 judge verdicts into the graph -> data/processed/pharos_pruned_v3.{whole,pruned}.*
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u -m bioagent.clean.apply_judge data/processed/pharos_pruned_v2 data/processed/judge_tier3.jsonl data/processed/pharos_pruned_v3 gpt-oss
