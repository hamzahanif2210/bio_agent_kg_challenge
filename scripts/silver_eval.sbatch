#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=silver
#SBATCH --time=00:40:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --output=logs/silver_%j.out
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u -W ignore scripts/silver_eval.py
