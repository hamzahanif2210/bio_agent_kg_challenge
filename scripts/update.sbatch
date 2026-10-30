#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=kg_update
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=24G
#SBATCH --output=logs/update_%j.out
# Maintenance mode demo: re-fetch N random targets live from Pharos and report what changed since our snapshot.
#   sbatch scripts/update.sbatch [N]      -> data/processed/pharos_updated.{nodes,edges}.parquet and .delta.json
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u -m bioagent.ingest.update data/processed/pharos_evidence data/processed/pharos_updated --sample ${1:-100}
