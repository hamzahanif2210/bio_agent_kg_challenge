#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=pharos_base
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --array=0-11
#SBATCH --output=logs/baseline_%A_%a.out
# 4 target edge types x 3 seeds = 12 tasks. Usage: sbatch scripts/baseline_array.sbatch [GRAPH_PREFIX] [TAG]
GRAPH=${1:-data/processed/pharos}
TAG=${2:-pharos}
TARGETS=("ppi|biolink:interacts_with|pharos:ppi" "disease|biolink:related_to|pharos:disease_association" "go|biolink:related_to|pharos:go" "ligand|biolink:interacts_with|pharos:ligand_activity")
SEEDS=(0 1 2)
T=${TARGETS[$((SLURM_ARRAY_TASK_ID / 3))]}
SEED=${SEEDS[$((SLURM_ARRAY_TASK_ID % 3))]}
IFS='|' read NAME PRED EVID <<< "$T"
cd /project/rpp-nahee/hamza95/agent_challenge
source env.sh
python -W ignore -m bioagent.eval.baseline "$GRAPH" "$PRED" "$EVID" --seed $SEED > runs/${TAG}_${NAME}_s${SEED}.json
