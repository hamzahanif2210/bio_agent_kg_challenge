#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=review_llm
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --output=logs/review_llm_%j.out
# Blind LLM review of the 64-row sheet on NRP.  sbatch --job-name=review_MODEL scripts/llm_review.sbatch MODEL
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
export LLM_API_KEY=$(cat /project/rpp-nahee/hamza95/.nrp_token)
python -u scripts/llm_review.py --model "$1" --sheet "${SHEET:-data/processed/review_sheet.csv}" --out runs/review${TAG}_$1.json
