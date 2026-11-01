"""Upload the full graphs (exports/) to a PRIVATE Hugging Face dataset repo. The token is read from a file, never printed.

  python scripts/upload_hf.py [--repo hamzahanif/bio-agent-kg] [--token-file /project/rpp-nahee/hamza95/.h5_token]

Makes the repo private if it does not exist (it never changes visibility of an existing repo).
"""
import argparse, json
from huggingface_hub import HfApi

ap = argparse.ArgumentParser()
ap.add_argument("--repo", default="hamzahanif/bio-agent-kg"); ap.add_argument("--token-file", default="/project/rpp-nahee/hamza95/.h5_token")
ap.add_argument("--dir", default="exports"); ap.add_argument("--summary", default="data/processed/pharos_pruned_v3.summary.json")
a = ap.parse_args()
api = HfApi(token=open(a.token_file).read().strip())
api.create_repo(a.repo, repo_type="dataset", private=True, exist_ok=True)
s = json.load(open(a.summary))
card = f"""---
license: other
pretty_name: Bio-agent knowledge graph (Pharos, pruned)
---
# Bio-agent knowledge graph

Pharos targets, diseases, ligands, GO terms and protein interactions as a Biolink-aligned graph. Every edge has a keep / prune
verdict with `rule`, `reason` and `verdict_confidence`. Code: https://github.com/hamzahanif2210/bio_agent_kg_challenge

- `whole.*`: all {s['whole_edges']:,} edges with verdicts. `pruned.*`: the {s['kept_edges']:,} kept edges ({s['pruned_edges']:,} pruned).
- `genes_whole.*`, `genes_pruned.*`: the same with Ensembl Gene nodes split from proteins (`has_gene_product`).
- Each as KGX TSV (`*.kgx/nodes.tsv`, `edges.tsv`) and PyTorch Geometric (`*.pyg.pt`, load with `torch.load(path, weights_only=False)`).

Underlying sources (Pharos, Open Targets, UniProt, GO, MONDO, STRING, BioPlex, Reactome, CRAPome, PubMed) keep their own licences;
check them before redistributing. Verdicts are heuristic and partly LLM-judged: see the write-up in the code repository.
"""
api.upload_file(path_or_fileobj=card.encode(), path_in_repo="README.md", repo_id=a.repo, repo_type="dataset")
api.upload_large_folder(repo_id=a.repo, repo_type="dataset", folder_path=a.dir)
print("uploaded to", a.repo, "(private)")
