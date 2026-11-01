#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=clean_test
#SBATCH --time=00:30:00
#SBATCH --mem=16G
#SBATCH --output=logs/clean_checkout_%j.out
# Fresh-clone test: clone the public repo into an empty scratch directory (no data/, no exports/) and run what a new user would:
# the unit tests, then the quick start on the bundled sample graph, with PYTHONPATH pointing only at the clone.
# Also runnable inside an interactive job:  srun --jobid=<id> --overlap bash scripts/clean_checkout_test.sbatch
D=/scratch/hamza95/clean_checkout; rm -rf $D; mkdir -p $D; cd $D
git clone -q https://github.com/hamzahanif2210/bio_agent_kg_challenge.git repo || exit 1; cd repo
module load gcc arrow cuda python/3.13 2>/dev/null; source /project/rpp-nahee/hamza95/python313/bin/activate
export PYTHONPATH=$PWD/src; unset AGENT_ROOT
fail=0
for t in tests/test_*.py; do r=$(python -W ignore $t 2>&1 | tail -1); printf "%-30s %s\n" $t "$r"; case "$r" in *PASSED*) ;; *) fail=1;; esac; done
S="--graph sample/sample.whole"
python -W ignore -m bioagent $S ask --entities BRCA1 --html /tmp/brca1_$$.html | tail -4 || fail=1
python -W ignore -m bioagent $S explain EGFR "non-small cell lung carcinoma" | head -8 || fail=1
python -W ignore -m bioagent.export.formats sample/sample.pruned /tmp/sample_export_$$ | tail -2 || fail=1
ls /tmp/sample_export_$$* | head; rm -rf /tmp/brca1_$$.html /tmp/sample_export_$$*
echo "CLEAN CHECKOUT: $([ $fail = 0 ] && echo OK || echo FAILED)"
