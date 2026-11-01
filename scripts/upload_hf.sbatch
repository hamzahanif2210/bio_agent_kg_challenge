#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=upload_hf
#SBATCH --time=04:00:00
#SBATCH --mem=8G
#SBATCH --output=logs/upload_hf_%j.out
# Upload exports/ (full graphs) to the private Hugging Face dataset repo. Run after the final rebuild.
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u scripts/upload_hf.py "$@"
