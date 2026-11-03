#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=kgx_ctr
#SBATCH --time=01:30:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --output=logs/kgx_container_%j.out
# Real `kgx validate` in a Python 3.11 container (the cluster Python cannot install kgx's dependencies). Validates the sample export.
cd /project/rpp-nahee/hamza95/agent_challenge
module load apptainer
export APPTAINER_CACHEDIR=/scratch/hamza95/apptainer_cache APPTAINER_TMPDIR=/scratch/hamza95/apptainer_tmp; mkdir -p $APPTAINER_CACHEDIR $APPTAINER_TMPDIR
[ -f /scratch/hamza95/py311.sif ] || apptainer pull /scratch/hamza95/py311.sif docker://python:3.11-slim
apptainer exec --cleanenv --bind $PWD:/work /scratch/hamza95/py311.sif bash -c '
  python -m venv /tmp/v && . /tmp/v/bin/activate && pip install -q kgx 2>&1 | tail -3
  kgx --version; cd /work && kgx validate --input-format tsv --output runs/kgx_validate_pruned.txt exports/pruned.kgx/nodes.tsv exports/pruned.kgx/edges.tsv; echo "kgx exit: $?"'
