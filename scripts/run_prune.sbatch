#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=prune_v1
#SBATCH --time=01:30:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=48G
#SBATCH --output=logs/prune_%j.out
# Pruning rules v1 on the Pharos evidence graph -> data/processed/pharos_pruned.{whole,pruned}.*
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u -m bioagent.clean.run_prune data/processed/pharos_evidence /scratch/hamza95/bio_kg_data data/processed/pharos_pruned
