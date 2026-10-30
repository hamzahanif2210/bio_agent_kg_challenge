#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=biolink_check
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --output=logs/biolink_check_%j.out
# Validate the exported graph against the Biolink model. bmt (Biolink Model Toolkit) is installed into scratch, not the repo.
# (kgx itself failed to install: it forces a pyarrow source build; bmt is the part that knows the model.)
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
pip install --target /scratch/hamza95/bmt_env bmt 2>&1 | tail -2
export PYTHONPATH=/scratch/hamza95/bmt_env:$PYTHONPATH
python -u scripts/validate_biolink.py exports/pruned.kgx
