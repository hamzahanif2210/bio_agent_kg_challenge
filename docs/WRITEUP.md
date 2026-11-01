# Write-up draft: Bio-Agent Knowledge Graph (open-source track)

DRAFT. Numbers are from the final graph build; update them after the last rebuild.

## What we built

A pipeline that turns Pharos (targets, diseases, ligands, GO, protein interactions) into a Biolink-aligned knowledge graph, decides for every edge whether to keep or prune it, and records why.

- **Whole graph:** 3,089,014 edges, each with `verdict`, `verdict_confidence`, `rule`, `reason` and `needs_review`.
- **Pruned graph:** 2,901,057 kept edges. 187,957 edges pruned.
- **Formats:** KGX TSV and PyTorch Geometric `HeteroData`, for both the whole and the pruned graph. A gene-split variant (Ensembl Gene nodes, `has_gene_product`) is also built.
- **Use:** one command to run (`scripts/run_pipeline.sbatch`), a small sample graph (`sample/`) that works from a clone, `bioagent ask` for questions answered from the graph with an interactive picture, and `bioagent explain` for a single edge.
- **Maintenance:** edge diffing (`ingest/update.py`) re-fetches targets and reports added, removed and changed edges.

## How pruning decides

1. Rules from the sources themselves: interaction scores and database counts, Open Targets support, UniProt GO annotations and the GO hierarchy.
2. Obsolete GO/MONDO terms that name a replacement are renamed (10,006 edges); the rest are pruned.
3. CRAPome: BioPlex-only interactions with a frequent AP-MS contaminant are pruned (4,574).
4. PubMed co-mention tiers for weak disease links: none means pruned (139,301); 10 or more means a candidate rescue.
5. An LLM judge (gpt-oss) reads PubMed titles, the UniProt function and the MONDO definition. A keep needs `p_real` of at least 0.8. It judged 5,000 weak links (2,595 rescued, 1,052 pruned). A second judge pass over the 10+ co-mention rescues is running (job 1800013); a rescue will need the judge to agree, and this section must be updated with its result.
6. GO links absent from UniProt are kept at confidence 0.45 and flagged for review, because reviewers found most of them plausible.

The LLM never creates edges. Every edge traces to a source record.

## What we checked, and how far it can be trusted

- **Standards:** an in-house checker validates predicate, domain and range against Biolink 4.4.6 (0 problems on the gene-split graph). It is not `kgx validate`; that package would not install here.
- **Blind LLM review:** eight models rated a 64-edge sample and a 150-edge GO sample. Keeps and the no-literature and CRAPome prunes were well supported. The models lean toward "plausible", so this is a smoke test, not an accuracy figure.
- **Link prediction:** GraphSAGE on plain Pharos, pruned, gene-split and ontology-enriched graphs shows no difference beyond seed noise. We do not claim a prediction gain. The case for the submission is cleaner, standards-valid, explained data.

## Known limits (state these plainly)

- The pruning priors are heuristics. They are not calibrated against a gold set and no human domain expert has reviewed them.
- About 30,000 weak disease links with 1 to 9 co-mentions were never judged. They keep the rule verdict and are flagged `needs_review`.
- 504 disease edges with obsolete MONDO terms are still pruned as invalid identifiers. Only 188 of them have a single suggested current term (`consider`), and a suggestion is not a rename, so we did not remap them.
- The PubMed count is a co-mention of names. It rescued a wrong edge once (SHOC2 and Costello syndrome); the judge check on the rescues was added for that reason (result pending).
- The maintenance mode found no changes in its one test, so it is not shown to detect a real change.
- The HTML pictures have not been checked in a browser.
- Full graphs are about 2.5 GB and are not in the repository; the sample graph is.

## For the organizers

Open question: what delivery format and gold-set comparison they will use, so we can report a real accuracy number.
