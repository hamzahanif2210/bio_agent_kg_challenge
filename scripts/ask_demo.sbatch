#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=ask_demo
#SBATCH --time=00:20:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --output=logs/ask_demo_%j.out
# Question-to-graph demo on the final graph, with interactive pictures in demo/*.html. The LLM only extracts entity names.
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
export LLM_API_KEY=$(cat /project/rpp-nahee/hamza95/.nrp_token) LLM_BASE_URL=https://ellm.nrp-nautilus.io/v1
python -u -m bioagent ask "How is EGFR connected to non-small cell lung carcinoma?" --html demo/egfr_nsclc.html
echo ===========
python -u -m bioagent ask "What is known about BRCA1?" --html demo/brca1.html
