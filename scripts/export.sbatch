#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=export_kg
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --output=logs/export_%j.out
# Export the final graphs (whole + pruned) as KGX TSV and PyTorch Geometric -> exports/{whole,pruned}.{kgx/,pyg.pt}
# Usage: sbatch scripts/export.sbatch [GRAPH_PREFIX]   (default: the v3 graph)
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
G=${1:-data/processed/pharos_pruned_v3}
python -u -W ignore -m bioagent.export.formats $G.whole exports/whole
python -u -W ignore -m bioagent.export.formats $G.pruned exports/pruned
