#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=pipeline
#SBATCH --time=01:30:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --output=logs/pipeline_%j.out
# The whole pipeline from the fetched Pharos graph, no LLM calls, one command:  sbatch scripts/run_pipeline.sbatch
#   1. rule-based pruning (v1)        -> data/processed/pharos_pruned.*
#   2. PubMed tiers (needs pubmed_counts.jsonl from scripts/pubmed_counts.sbatch)  -> pharos_pruned_v2.*
#   3. LLM-judge verdicts (needs judge_tier3.jsonl from scripts/judge_tier3.sbatch) -> pharos_pruned_v3.*
#   4. exports (KGX + PyTorch Geometric, whole and pruned) -> exports/
# Steps 2 and 3 are skipped when their input file is missing. The slow inputs (Pharos fetch, PubMed scan, judge) are
# separate jobs because they take hours; their results are cached under data/.
set -e
cd /project/rpp-nahee/hamza95/agent_challenge
. ./env.sh
P=data/processed
CRAP=data/external/crapome_human.tsv   # optional: from scripts/fetch_crapome.sbatch
python -u -m bioagent.clean.run_prune $P/pharos_evidence /scratch/hamza95/bio_kg_data $P/pharos_pruned $( [ -f $CRAP ] && echo $CRAP )
FINAL=$P/pharos_pruned
if [ -f $P/pubmed_counts.jsonl ]; then
  python -u -m bioagent.clean.pubmed_tiers $FINAL $P/pubmed_counts.jsonl $P/pharos_pruned_v2; FINAL=$P/pharos_pruned_v2
  if [ -f $P/judge_tier3.jsonl ]; then
    python -u -m bioagent.clean.apply_judge $FINAL $P/judge_tier3.jsonl $P/pharos_pruned_v3 gpt-oss; FINAL=$P/pharos_pruned_v3
  fi
fi
for part in whole pruned; do python -u -W ignore -m bioagent.export.formats $FINAL.$part exports/$part; done
echo "final graph: $FINAL"
