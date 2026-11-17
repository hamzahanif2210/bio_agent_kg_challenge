# standards: Biolink and OBO

### Adherence to ontological standards (OBO Foundry and Monarch Biolink)

- **Biolink 4.4.6.** Nodes use Biolink classes (`biolink:Protein`, `Gene`, `Disease`, `SmallMolecule`, `BiologicalProcess`, ...). Edges use specific Biolink predicates (`physically_interacts_with`, `actively_involved_in`, `capable_of`, `located_in`, `gene_associated_with_condition`, with `associated_with` and `related_to` as the general fall-backs) rather than one generic link; `standards/biolink.py` checks every predicate and its subject and object classes against the model.
- **Gene and protein are separate.** A gene-disease link is attached to the gene node, not the protein (`standards/genes.py`). Without the split the graph mixes the two, which Biolink does not allow.
- **OBO terms and IRIs.** `ontology_class`, `ontology_class_iri` and `iri` columns map each node class to an OBO term (protein `PR:000000001`, protein-coding gene `SO:0001217`, disease `MONDO:0000001`, GO branches, ...) and each CURIE to a resolvable IRI. A predicate with no declared OBO property stays empty: we do not invent mappings (`standards/ontology.py`).
- **Identifiers.** UniProtKB, MONDO, GO, ChEMBL and PHAROS CURIEs. Obsolete GO and MONDO terms are remapped to their replacement, the old id kept in `original_object`.
- **Real validator.** `kgx validate` 2.6.0 (run in a container, `scripts/kgx_container.sbatch`) first flagged one problem: Biolink's context has `PHAROS` but not `PHAROS.LIGAND`. The export now writes `PHAROS:`; the pruned graph then validates with no errors (`runs/kgx_validate_pruned.txt`).
- **Provenance on every edge:** `source`, `evidence`, `confidence`, `method`, `timestamp`, plus `verdict`, `rule`, `reason`.
