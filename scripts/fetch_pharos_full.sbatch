#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=pharos_full
#SBATCH --time=08:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=24G
#SBATCH --output=logs/pharos_full_%j.out
# Full (untruncated) Pharos graph: nested lists fetched with top:5000.
# Resumable: raw pages are cached in data/raw/pharos_full, so just resubmit if it stops.
cd /project/rpp-nahee/hamza95/agent_challenge
source env.sh
python -m bioagent.ingest.pharos data/processed/pharos_full
