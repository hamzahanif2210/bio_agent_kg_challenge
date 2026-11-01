#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=go_sample
#SBATCH --time=00:10:00
#SBATCH --mem=16G
#SBATCH --output=logs/go_sample_%j.out
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u scripts/go_sample.py
