#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=feat
#SBATCH --time=01:30:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --output=logs/features_%j.out
# Node features (text and sequence composition) for the link-prediction experiments.
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u -W ignore scripts/build_features.py
