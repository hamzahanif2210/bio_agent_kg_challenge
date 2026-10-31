#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=review_sheet
#SBATCH --time=00:10:00
#SBATCH --mem=16G
#SBATCH --output=logs/review_sheet_%j.out
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u scripts/review_sheet.py 8
