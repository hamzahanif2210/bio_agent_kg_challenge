#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=rebuild_prune
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=48G
#SBATCH --output=logs/rebuild_prune_%j.out
# Rebuild the Pharos evidence graph from the cached API pages (no network), then re-run pruning.
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u -m bioagent.ingest.pharos data/processed/pharos_evidence | head -3
python -u -m bioagent.clean.run_prune data/processed/pharos_evidence /scratch/hamza95/bio_kg_data data/processed/pharos_pruned | tail -3
python -u scripts/explain_demo.py
