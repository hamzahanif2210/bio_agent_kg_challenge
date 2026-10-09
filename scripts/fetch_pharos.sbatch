#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=pharos_fetch
#SBATCH --time=06:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --output=logs/pharos_fetch_%j.out
# Resumable: raw pages are cached in data/raw/pharos, so just resubmit if it stops.
cd /project/rpp-nahee/hamza95/agent_challenge
source env.sh
python -m bioagent.ingest.pharos data/processed/pharos
