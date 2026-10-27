#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=pharos_evid
#SBATCH --time=10:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=40G
#SBATCH --output=logs/pharos_evidence_%j.out
# Full Pharos graph WITH per-edge evidence (PPI Score/p_int, disease association types/scores).
# Resumable: raw pages cache in data/raw/pharos_evidence; just resubmit if it stops.
cd /project/rpp-nahee/hamza95/agent_challenge
source env.sh
python -m bioagent.ingest.pharos data/processed/pharos_evidence
