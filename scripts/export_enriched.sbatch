#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=exp_enr
#SBATCH --time=01:30:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=96G
#SBATCH --output=logs/export_enriched_%j.out
# Enriched graph (kept edges + context edges + node features) -> exports/enriched.{kgx,pyg.pt}
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u -W ignore -m bioagent.export.enriched data/processed/pharos_pruned_v3.pruned data/context/context data/features exports/enriched
