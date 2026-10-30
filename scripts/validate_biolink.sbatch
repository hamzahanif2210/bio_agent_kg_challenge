#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=biolink_check
#SBATCH --time=00:20:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --output=logs/biolink_check_%j.out
# Validate exported graphs against the Biolink model YAML (data/external/biolink-model.yaml). No extra packages needed.
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u scripts/validate_biolink.py exports/whole.kgx
python -u scripts/validate_biolink.py exports/pruned.kgx
