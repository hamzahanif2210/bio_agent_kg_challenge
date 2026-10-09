# Literature and resource survey

Source: `documents/muse-1.md`, a survey produced by another LLM with web access (Oct 2026). **None of this has been independently verified by us.** The survey says it opened about 15 of the pages itself and that sub-agents opened the rest; items marked UNVERIFIED there are marked here too. Open the link and check the numbers before relying on any claim, and check licenses before reusing code or data.

Effort figures are the survey's estimates, not ours.

## Priority list (survey's ranking by expected score gain per hour)

| # | Item | Effort | Helps | Why |
|---|---|---|---|---|
| 1 | OptimusKG Parquet ingest | 0.5-1 d | link prediction, lineage | 21.8M typed, Biolink-aligned edges with provenance columns |
| 2 | Leakage-proof eval harness | 2-3 d | validity of results | Leakage inflates biomedical link-prediction metrics (see Risks) |
| 3 | Curated parameterized query templates (BiomedQA pattern) | 1 d | usability (40%) | Reported 98% vs 85% for raw text-to-Cypher |
| 4 | Schema-aware query checker (Pusch et al.) | 1-2 d | usability, explainability | Reported to lift GPT-4o from 1 to 40 correct of 50 |
| 5 | Enrichment ablation (KGOT-style) | 1-2 d | link prediction | Decides which edge types are worth adding |
| 6 | Biolink schema + `kgx validate` | hours-1 d | standards (10%), lineage | Nearly free conformance check |
| 7 | Scientific agent skills (ARAX, DB lookups) as tool templates | 4-8 h | ingest | MIT, 166 skills over 78 databases; very new repo |
| 8 | Open Targets evidence as scored edges | 2-3 d | link prediction, pruning | CC0; per-source evidence scores usable as pruning signals |
| 9 | GraphJudge fine-tuned triple judge | 3-5 d | pruning (30%) | MIT code; needs labelled triples |
| 10 | ChronoMedKG consensus + PMID/quote provenance | 2-4 d | pruning, lineage | 3.5% retention filter; multi-model consensus |
| 11 | FuseLinker LLM text embeddings as node features | 3-5 d | link prediction | Gains reported on four biomedical KGs |
| 12 | Monarch KGX ingest | 1-2 d | link prediction | 8.9M edges, CC0 |
| 13 | BioPathNet negative sampling and auxiliary edges | 3-5 d | link prediction | Nature BME 2026 |
| 14 | Graphiti bi-temporal invalidation | 3-4 d | maintain, lineage | Never delete contradicted edges; Apache-2.0 |
| 15 | G-Retriever subgraph retrieval | 3-5 d | usability, explainability | Ships in PyG 2.6+ |
| 16 | Counterfactual edge-occlusion explainer | 2-3 d | explainability (20%) | Model-agnostic "why does A connect to B" |
| 17 | Retrieval-first ontology mapping (Mavridis et al.) | 1-2 d | standards | Embedding retrieval, then LLM verification |

Lower-priority items from the survey: LLM_sim per-triple judge (no code), DRKG with pretrained TransE embeddings, GroundLens NLI verifier, Koza transforms (beta), iKraph daily-cutoff scheduler (pattern only; data is CC BY-NC-ND), AIME-2026 Shapley path attribution, a RAG-GNN rationale prototype (57% faithfulness), CypherTurn multi-turn stress test, UnKGCP conformal confidence (NC license), Quadruple-Shot proposition chunking, ATOM merge operator, KGHub kg-obo and kg-idg, CLEAR per-type embeddings, Hetionet as a regression graph, a UMLS GraphRAG paper (check UMLS licensing), OpenBioLink as an internal benchmark, KG-LLM-Bench for Filter regression tests, SPOKE (no bulk download).

## Papers and projects by topic

### LLM agents that build biomedical KGs
- **ChronoMedKG** (arXiv 2605.22734, May 2026): four agents; keeps triples agreed on by at least two LLMs, each with PMID, quote and credibility score. 460,497 triples kept from 13M raw (3.53%); 92.7% agreement vs Orphadata. https://arxiv.org/abs/2605.22734
- **Multi-LLM clinical KG construction** (arXiv 2601.01844): staged extraction, ontology mapping, relation refinement, trust scoring. No code; no numbers reported. http://arxiv.org/abs/2601.01844
- **Scientific agent skills** (arXiv 2609.00065; repo kim-autorobotics/claude_scientifi_skills): 166 MIT-licensed skills including NCATS ARAX. Three weeks old, 3 stars. https://github.com/kim-autorobotics/claude_scientifi_skills
- **LLM RDF construction via ontology mapping** (Frontiers in AI 2025): BioBERT retrieval, then LLM verifier; F1 96.26% on 108 terms. https://pubmed.ncbi.nlm.nih.gov/40352975/
- **Quadruple Shot** (arXiv 2508.03438): proposition chunking with a context variable; pilot scale. https://arxiv.org/abs/2508.03438

### Graph RAG and natural-language queries
- **G-Retriever** (NeurIPS 2024, arXiv 2402.07630): PCST subgraph retrieval; code at XiaoxinHe/G-Retriever. https://arxiv.org/abs/2402.07630
- **BiomedQA** (samyama-ai/biomedqa, Apache-2.0): MCP tool templates 39/40 vs text-to-Cypher 34/40. https://github.com/samyama-ai/biomedqa
- **CypherTurn** (arXiv 2609.36987): multi-turn text-to-Cypher benchmark; session-level correctness under 5%. https://arxiv.org/abs/2609.36987
- **Pusch and Conrad** (BioMedInformatics 2025): query checker for PrimeKG text-to-Cypher. https://www.mdpi.com/2673-7426/5/4/70
- **UMLS continual pretraining vs GraphRAG** (arXiv 2604.16422). https://arxiv.org/abs/2604.16422

### Pruning and cleaning
- **GraphJudge** (arXiv 2411.17388, EMNLP 2025; MIT): fine-tuned judge, over 90% accuracy on graph-judgement tasks. https://github.com/hhy-huang/GraphJudge
- **LLM_sim** (ACL GenAIK 2025): F1 0.951 noise detection on WN18RR; no code. https://preview.aclanthology.org/override-month/2025.genaik-1.9.pdf
- **UnKGCP** (arXiv 2510.24754): conformal prediction intervals for KG embeddings. https://arxiv.org/abs/2510.24754
- **GroundLens** (groundlens-dev/groundlens, Apache-2.0): NLI verification of claims against sources; 7 stars. https://github.com/groundlens-dev/groundlens

### Keeping the KG up to date
- **Zep / Graphiti** (arXiv 2501.13956; Apache-2.0): bi-temporal edges, invalidate rather than delete. https://github.com/getzep/graphiti
- **ATOM** (arXiv 2510.22590): incremental temporal KG merging; code and license unconfirmed. https://arxiv.org/abs/2510.22590
- **iKraph / BioKG** (Nature Machine Intelligence 2025): daily literature updates at scale; won the NIH LitCoin challenge. https://pmc.ncbi.nlm.nih.gov/articles/PMC10760044/

### Link prediction
- **BioPathNet** (Nature Biomedical Engineering, Jan 2026): path-based GNN, node-type-aware negative sampling. Repo unverified. https://link.springer.com/article/10.1038/s41551-025-01598-z
- **KGOT** (arXiv 2512.09365): enrichment ablation (Hits@1 36.3% to 53.4% as GO, protein family and pathway edges were added). No code. https://arxiv.org/abs/2512.09365
- **Brière et al., data leakage in KGE benchmarks** (HAL hal-04913469): redundancy control cut MRR by up to 46%. https://hal.science/hal-04913469v2
- **PrimeKG-RGCN-LinkPrediction** (arnold117, MIT): undirected-aware split; fixed a 71.5% reverse-edge leak. https://github.com/arnold117/PrimeKG-RGCN-LinkPrediction
- **BioGraphBench-PPI** (Frontiers in Bioinformatics, Oct 2026): hard-negative contracts; STRING and BioGRID share 423,528 pairs. https://www.frontiersin.org/journals/bioinformatics/articles/10.3389/fbinf.2026.1966469/full

### GNN + LLM hybrids and explainability
- **FuseLinker** (J. Biomedical Informatics 2024): LLM text embeddings plus ontology embeddings as GNN initialization. https://github.com/YKXia0/FuseLinker
- **CLEAR** (ayyucedemirbas/clear): per-type feature recipe (MoLFormer, BioBERT, ESM-2); license metadata conflicts. https://github.com/ayyucedemirbas/clear
- **Explainable KGE with path attribution** (AIME 2026): Shapley attribution; code unverified. https://link.springer.com/chapter/10.1007/978-3-032-30813-9_24
- **explainable-ai-adr** (himanshu-kr7, MIT): edge-occlusion explanations; AUC 0.9922 under random negatives vs 0.5087 under hard negatives. https://github.com/himanshu-kr7/explainable-ai-adr
- **559_rag-gnn** (course project, no license): rationale faithfulness only 57%. https://github.com/shouyuwang08/559_rag-gnn

## MICCAI 2026 additions

Source: `documents/miccai.md`, a second survey by another LLM covering MICCAI 2026 main and satellite indexes. It found **no paper that does biomedical KG construction or link prediction directly** (zero title hits for "knowledge graph" and "link prediction"), so the value is in transferable methods. Same caveat as above: unverified, check before relying on it.

- **NeRD** (MICCAI 2026, arXiv:2606.15617): distills LLM reasoning into compact ontology-grounded concept chains (6 concepts vs 28/32, about 20x faster inference). Idea: short ontology-based explanation paths for prune and predict decisions. Targets pruning, explainability and standards together. No code seen.
- **ClinRAG-GRAPH** (MICCAI 2026, arXiv:2607.00798, code available): relation-aware GCN on a clinical-prior graph plus LLM subgraph retrieval for evidence-grounded interpretation (AUC 0.815). Idea: use the encoder for the link-prediction head and the subgraph pattern for provenance.
- **ConceptAlignE-G** (MICCAI 2026 early accept, code available): probabilistic concept edges with clinician intervention that propagates without retraining. Idea: a pattern for the Clean loop; edge weights double as pruning scores.
- **GraphRAG vs RAG-only vs KG-only** (MDPI Bioengineering 2026): negative result. KG-only retrieval scored 50.9% vs 96.4% for RAG-only. Lesson: don't rely on raw KG lookup for the natural-language interface; a hybrid is better.
- **KGLMQA** (PeerJ 2026): KG-RAG module blueprint for the natural-language filtering and querying step.

The survey's conclusion is that the top-5 plan above is unchanged. MICCAI refines three steps: NeRD-style explanation paths (Clean and explainability), a relation-aware GCN encoder (link-prediction head), and ConceptAlignE-G edge weights (pruning signals).

About 15 workshop titles (CLAP-4-QnA, PathTrace, Grounded Ontology Walker, MEC, DermAgent, CURA and others) appeared in the indexes but could not be opened. Do not cite them.

## Resources and tooling

| Resource | Size / role | License | Notes |
|---|---|---|---|
| Pharos / TCRD | GraphQL API; MySQL dumps at juniper.health.unm.edu/tcrd/download | UNVERIFIED | Already in use |
| OptimusKG | 192,813 nodes, 21.8M edges, Parquet (`pip install optimuskg`) | Code MIT; data inherits source terms (some non-commercial) | https://github.com/mims-harvard/optimuskg |
| Monarch KG | 1.12M nodes, 8.91M edges, KGX TSV | CC0 | https://data.monarchinitiative.org/monarch-kg/ |
| Open Targets | GraphQL and bulk | CC0 | https://platform-docs.opentargets.org/ |
| PrimeKG | 129,375 nodes, 4.05M edges | MIT | Superseded by OptimusKG; skip |
| Hetionet | 47k nodes, 2.25M edges, frozen 2017 | CC0 | Regression-test graph only |
| DRKG | 97k entities, 5.87M triplets; pretrained TransE | Apache-2.0 | Frozen 2020 |
| SPOKE | 27M nodes | UNVERIFIED | No bulk download |
| KGHub | 40+ Biolink KGs | varies | Sometimes unavailable |
| Biolink Model | classes, predicates, provenance slots | NOASSERTION | https://github.com/biolink/biolink-model |
| KGX | validate / merge / transform | BSD-3 | `kgx validate` as a conformance check |
| LinkML | schema to validators | Apache-2.0 | Optional |
| Koza | per-source transforms | BSD-3, beta | Optional |

## Prior competitions

NIH LitCoin NLP Challenge (KG from literature), BioASQ, BioCreative, DREAM Multi-Targeting Drug Challenge, OpenBioLink (leaderboard), BioKGBench (agents that find factual errors in KGs). The survey reported no public rules page for this challenge; confirm with the organizers.

## Risks

- **Test-edge leakage via enrichment** is the main risk. External KGs may contain held-out Pharos edges. Check every enrichment edge against the held-out set.
- **Reverse-edge leakage:** no edge or its reverse in more than one split.
- **Random negatives overstate performance:** two reports saw about 0.99 AUC drop to about 0.51 under hard negatives. Report AUPRC and calibration, not only AUROC.
- **LLM rationales hallucinate:** ground every rationale in retrieved paths and check it.
- **Licenses:** OptimusKG inherits non-commercial upstream terms; some preprints are NC or ND; several repos have no clear license; check UMLS-derived graphs.
- **Stale sources:** PrimeKG superseded, Hetionet 2017, DRKG 2020.
- **Cost:** per-triple LLM calls are expensive at scale; limit to low-confidence edges.
- **No-code papers** (LLM_sim, KGOT) mean reimplementation risk.
- **Young tooling:** Koza (beta), GroundLens, the agent-skills repo.

## Questions for the organizers

See the "Open questions" section of the README.
