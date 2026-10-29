#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=judge_v2
#SBATCH --time=01:30:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=24G
#SBATCH --output=logs/judge_v2_%j.out
# Pruning v2 pilot on NRP. Token is read from a file inside the job, never put on a command line.
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
export LLM_API_KEY=$(cat /project/rpp-nahee/hamza95/.nrp_token)
python -u scripts/judge_sample.py --base-url https://ellm.nrp-nautilus.io/v1 --model "${1:-kimi}" --n-silver "${2:-40}" --n-weak "${3:-100}" --out "${4:-runs/judge_v2.json}"
