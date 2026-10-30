#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=crapome
#SBATCH --time=06:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --output=logs/crapome_%j.out
# CRAPome contaminant frequencies for our BioPlex-only proteins -> data/external/crapome_human.tsv (resumable)
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u scripts/fetch_crapome.py
