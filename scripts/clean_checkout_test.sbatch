#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=clean_test
#SBATCH --time=00:30:00
#SBATCH --mem=16G
#SBATCH --output=logs/clean_checkout_%j.out
# Clone the public repo into an empty scratch directory and run everything a new user can run without our data: the unit tests.
set -e
D=/scratch/hamza95/clean_checkout; rm -rf $D; mkdir -p $D; cd $D
git clone -q https://github.com/hamzahanif2210/bio_agent_kg_challenge.git repo; cd repo
sed -i 's|/project/rpp-nahee/hamza95/agent_challenge|'$PWD'|' env.sh 2>/dev/null || true
. ./env.sh
for t in tests/test_*.py; do printf "%-28s" $t; python -W ignore $t 2>&1 | tail -1; done
python -m bioagent --help | head -3
