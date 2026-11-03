#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=kgx_env
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --output=logs/kgx_env_%j.out
# Try to build a separate environment with the real `kgx` and run `kgx validate` on the pruned export. Own venv in scratch; PyPI wheels only.
module load gcc python/3.11
cd /scratch/hamza95 && rm -rf kgx_venv && python -m venv kgx_venv && . kgx_venv/bin/activate
export PIP_CONFIG_FILE=/dev/null
pip install --upgrade pip 2>&1 | tail -1
pip install kgx 2>&1 | tail -15
kgx --help 2>&1 | head -5
