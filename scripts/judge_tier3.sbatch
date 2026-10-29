#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=judge_tier3
#SBATCH --time=08:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --output=logs/judge_tier3_%j.out
# Tier-3 LLM judge on NRP. Keys are read from files inside the job, never put on a command line.
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
export LLM_API_KEY=$(cat /project/rpp-nahee/hamza95/.nrp_token)
export NCBI_API_KEY=$(cat /project/rpp-nahee/hamza95/NCBI_API_KEY)
python -u scripts/judge_tier3.py "$@"
