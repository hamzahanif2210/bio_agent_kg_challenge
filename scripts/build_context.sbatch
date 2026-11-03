#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=ctx
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=96G
#SBATCH --output=logs/context_%j.out
# Context edges (pathways, phenotypes, locations, tissues) from Open Targets and OptimusKG for the link-prediction experiments.
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u -W ignore scripts/build_context.py
