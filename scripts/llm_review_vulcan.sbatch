#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=review_vulcan
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --output=logs/review_vulcan_%j.out
# Blind LLM review of the 64-row sheet on Alliance Vulcan.  sbatch --job-name=review_MODEL scripts/llm_review_vulcan.sbatch MODEL OUTNAME
# The key is read from a file inside the job, never put on a command line.
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
export LLM_API_KEY=$(grep '^TYK_KEY=' /project/rpp-nahee/hamza95/.aleph_tyk.env | cut -d= -f2-)
python -u scripts/llm_review.py --base-url https://inference.vulcan.alliancecan.ca/v1 --model "$1" --out runs/review_${2:-$1}.json
