#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=genes
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --output=logs/genes_%j.out
# Gene-protein split on the v3 graph -> data/processed/pharos_genes.{whole,pruned}.*, exported to exports/genes_{whole,pruned}.*
# and checked against Biolink.
set -e
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
P=data/processed
python -u -m bioagent.standards.genes $P/pharos_pruned_v3.whole /scratch/hamza95/bio_kg_data $P/pharos_genes.whole
for part in whole pruned; do python -u -W ignore -m bioagent.export.formats $P/pharos_genes.$part exports/genes_$part; done
python -u scripts/validate_biolink.py exports/genes_pruned.kgx
