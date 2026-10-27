#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=dl_src
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --array=0-5
#SBATCH --output=logs/dl_src_%A_%a.out
# One array task per source, in parallel. Resumable: just resubmit. Never download on the login node.
SOURCES=(go mondo uniprot monarch opentargets optimuskg)
cd /project/rpp-nahee/hamza95/agent_challenge
bash scripts/download_sources.sh ${SOURCES[$SLURM_ARRAY_TASK_ID]}
