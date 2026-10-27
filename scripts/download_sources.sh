#!/bin/bash
# Download enrichment sources to scratch (resumable; safe to re-run). Data is NOT committed.
#   bash scripts/download_sources.sh [SOURCE|all] [DEST]     DEST default /scratch/hamza95/bio_kg_data
# SOURCE: go mondo uniprot monarch opentargets optimuskg all.  Versions: Open Targets 26.09, Monarch "latest".
# Run through Slurm (scripts/download_sources.sbatch), never on the login node.
set -u
SRC=${1:-all}
DEST=${2:-/scratch/hamza95/bio_kg_data}
OT=https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.09/output
dl(){ mkdir -p "$1"; curl -fL --retry 5 --retry-delay 5 -C - -o "$1/$2" "$3" || echo "FAILED: $3"; }

do_go(){ dl $DEST/go go-basic.obo http://purl.obolibrary.org/obo/go/go-basic.obo; }
do_mondo(){ dl $DEST/mondo mondo.obo http://purl.obolibrary.org/obo/mondo.obo
            dl $DEST/mondo mondo.json http://purl.obolibrary.org/obo/mondo.json; }
do_uniprot(){  # streamed response can't resume: always restart cleanly
  F="accession,id,gene_primary,gene_names,protein_name,cc_function,go_id,xref_ensembl,xref_hgnc,xref_geneid,xref_string,xref_chembl,xref_mim"
  mkdir -p $DEST/uniprot; rm -f $DEST/uniprot/human_reviewed.tsv
  dl $DEST/uniprot human_reviewed.tsv "https://rest.uniprot.org/uniprotkb/stream?query=organism_id:9606+AND+reviewed:true&format=tsv&fields=$F"; }
do_monarch(){ for f in monarch-kg.tar.gz metadata.yaml monarch-kg-schema.yaml; do
                dl $DEST/monarch $f https://data.monarchinitiative.org/monarch-kg/latest/$f; done; }
do_opentargets(){
  for d in association_by_datasource_direct association_overall_direct target disease disease_phenotype go interaction; do
    mkdir -p $DEST/opentargets_26.09/$d
    for f in $(curl -s $OT/$d/ | grep -oE 'href="[^"]+\.(parquet|json)"' | sed 's/href="//;s/"//'); do
      dl $DEST/opentargets_26.09/$d $f $OT/$d/$f; done
  done; }
do_optimuskg(){  # Harvard Dataverse doi:10.7910/DVN/IYNGEV (41 files, ~0.8 GB)
  mkdir -p $DEST/optimuskg
  curl -s "https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/IYNGEV" |
  python3 -c "
import sys,json
for f in json.load(sys.stdin)['data']['latestVersion']['files']:
    print(f['dataFile']['id'], (f.get('directoryLabel','')+'/'+f['label']).lstrip('/'))" |
  while read id path; do
    mkdir -p "$DEST/optimuskg/$(dirname "$path")"
    curl -fL --retry 5 -C - -o "$DEST/optimuskg/$path" "https://dataverse.harvard.edu/api/access/datafile/$id" || echo "FAILED: optimuskg $path"
  done; }

if [ "$SRC" = all ]; then for s in go mondo uniprot monarch opentargets optimuskg; do do_$s; done; else do_$SRC; fi
echo "DONE $SRC $(date -u +%FT%TZ)"
