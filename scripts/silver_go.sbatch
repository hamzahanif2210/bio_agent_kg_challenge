#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=silver_go
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --output=logs/silver_go_%j.out
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u -W ignore scripts/silver_go.py
