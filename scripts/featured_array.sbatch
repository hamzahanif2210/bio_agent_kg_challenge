#!/bin/bash
#SBATCH --account=def-nahee_cpu
#SBATCH --job-name=featured
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --array=0-155%24
#SBATCH --output=logs/featured_%A_%a.out
# Ablation of node features, context edges and models. 13 configs x 4 target types x 3 seeds = 156 tasks.
# Every task is scored on the same hidden Pharos edges (--ref pharos_evidence). Results: runs/ft_<config>_<target>_s<seed>.json
ALL=pathway,gene_phenotype,disease_phenotype,location,anatomy
P=data/processed
#  name | train graph | features | context | model | decoder
CONFIGS=(
"text|$P/pharos_pruned_v3.pruned|text||sage|dot"
"textseq|$P/pharos_pruned_v3.pruned|text,seq||sage|dot"
"ctxall|$P/pharos_pruned_v3.pruned||$ALL|sage|dot"
"full|$P/pharos_pruned_v3.pruned|text,seq|$ALL|sage|dot"
"fullgcn|$P/pharos_pruned_v3.pruned|text,seq|$ALL|gcn|dot"
"fullmlp|$P/pharos_pruned_v3.pruned|text,seq|$ALL|sage|mlp"
"plainfull|$P/pharos_evidence|text,seq|$ALL|sage|dot"
"plaintext|$P/pharos_evidence|text,seq||sage|dot"
"ctxpath|$P/pharos_pruned_v3.pruned||pathway|sage|dot"
"ctxpheno|$P/pharos_pruned_v3.pruned||gene_phenotype,disease_phenotype|sage|dot"
"ctxloc|$P/pharos_pruned_v3.pruned||location|sage|dot"
"ctxana|$P/pharos_pruned_v3.pruned||anatomy|sage|dot"
"fullmlpgcn|$P/pharos_pruned_v3.pruned|text,seq|$ALL|gcn|mlp"
)
TARGETS=("ppi|biolink:interacts_with|pharos:ppi" "disease|biolink:related_to|pharos:disease_association" "go|biolink:related_to|pharos:go" "ligand|biolink:interacts_with|pharos:ligand_activity")
C=${CONFIGS[$((SLURM_ARRAY_TASK_ID / 12))]}; R=$((SLURM_ARRAY_TASK_ID % 12))
T=${TARGETS[$((R / 3))]}; SEED=$((R % 3))
IFS='|' read CNAME GRAPH FEATS CTX MODEL DEC <<< "$C"
IFS='|' read NAME PRED EVID <<< "$T"
cd /project/rpp-nahee/hamza95/agent_challenge
source env.sh
python -W ignore -m bioagent.eval.featured "$GRAPH" "$PRED" "$EVID" --ref $P/pharos_evidence --seed $SEED --features "$FEATS" --context "$CTX" --model $MODEL --decoder $DEC > runs/ft_${CNAME}_${NAME}_s${SEED}.json
