#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=pubmed_tiers
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=24G
#SBATCH --output=logs/pubmed_tiers_%j.out
# Apply PubMed tiers 1-2 to the v1 pruned graph -> data/processed/pharos_pruned_v2.{whole,pruned}.*
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u -m bioagent.clean.pubmed_tiers data/processed/pharos_pruned data/processed/pubmed_counts.jsonl data/processed/pharos_pruned_v2
