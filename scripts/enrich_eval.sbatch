#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=enrich_build
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=48G
#SBATCH --output=logs/enrich_%j.out
# Build the ontology-enriched graph (kept edges + GO/MONDO hierarchy). Then run the baseline on it with the shared test edges:
#   J=$(sbatch --parsable scripts/enrich_eval.sbatch); sbatch --dependency=afterok:$J scripts/baseline_array.sbatch data/processed/enriched_ont enrichont data/processed/pharos_evidence
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u -m bioagent.enrich.ontology data/processed/pharos_pruned_v3.pruned /scratch/hamza95/bio_kg_data data/processed/enriched_ont
