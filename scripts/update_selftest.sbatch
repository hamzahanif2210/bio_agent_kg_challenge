#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=upd_self
#SBATCH --time=01:00:00
#SBATCH --mem=24G
#SBATCH --output=logs/update_selftest_%j.out
# Maintenance self-test: damage the stored snapshot in known ways (10 missing edges, 10 shifted scores, 10 invented edges) for 40 live-fetched
# targets and check that the update finds those changes. The "planted" and "detected" numbers must agree: planted-missing = detected "added"
# (the 10 invented edges replaced real ones, so those real edges come back as added too: expect added = 20), planted-rescored = detected "rescored", planted-not-in-pharos = detected "removed".
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
python -u -m bioagent.ingest.update data/processed/pharos_evidence data/processed/pharos_selftest --sample 40 --perturb 10
