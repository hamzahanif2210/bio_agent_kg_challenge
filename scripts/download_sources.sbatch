#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=dl_sources
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --output=logs/download_sources_%j.out
# Downloads enrichment sources to /scratch (resumable). Never run download_sources.sh on the login node.
cd /project/rpp-nahee/hamza95/agent_challenge
bash scripts/download_sources.sh
