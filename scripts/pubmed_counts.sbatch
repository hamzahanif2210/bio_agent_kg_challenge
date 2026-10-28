#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=pubmed_counts
#SBATCH --time=09:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --output=logs/pubmed_counts_%j.out
# NCBI key is read from a file inside the job, never put on a command line.
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
export NCBI_API_KEY=$(cat /project/rpp-nahee/hamza95/NCBI_API_KEY)
python -u scripts/pubmed_counts.py "$@"
