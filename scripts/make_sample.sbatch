#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=make_sample
#SBATCH --time=00:15:00
#SBATCH --mem=32G
#SBATCH --output=logs/make_sample_%j.out
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u scripts/make_sample.py
