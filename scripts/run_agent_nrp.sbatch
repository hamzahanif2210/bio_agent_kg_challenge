#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=agent_run
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --output=logs/agent_run_%j.out
# Leak-safe ingest-agent run on NRP. The token is read from a file inside the job (never put it on a command line).
# Usage: sbatch scripts/run_agent_nrp.sbatch "TASK" OUT_PREFIX [MODEL]
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
export LLM_API_KEY=$(cat /project/rpp-nahee/hamza95/.nrp_token)
python -u -m bioagent.ingest.run "$1" --out "$2" --provider openai --base-url https://ellm.nrp-nautilus.io/v1 \
    --model "${3:-kimi}" --max-steps 14 --max-tokens-total 120000 --log runs/agent_run_log.jsonl \
    --eval-graph data/processed/pharos_evidence --target-predicate biolink:interacts_with --target-evidence pharos:ppi --seed 0
