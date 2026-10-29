#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=ask_demo
#SBATCH --time=00:20:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=24G
#SBATCH --output=logs/ask_demo_%j.out
# Question-to-graph demo on the v2 pruned graph; the LLM only extracts entity names.
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
export LLM_API_KEY=$(cat /project/rpp-nahee/hamza95/.nrp_token)
python -u -m bioagent.qa.ask data/processed/pharos_pruned_v2.whole "How is EGFR connected to non-small cell lung carcinoma?" --base-url https://ellm.nrp-nautilus.io/v1 --model gpt-oss
echo ===========
python -u -m bioagent.qa.ask data/processed/pharos_pruned_v2.whole "What is known about BRCA1?" --base-url https://ellm.nrp-nautilus.io/v1 --model gpt-oss
