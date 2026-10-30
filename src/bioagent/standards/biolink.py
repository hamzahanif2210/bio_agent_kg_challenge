"""Biolink specialisation: replace the generic predicates the ingest step writes (`related_to`, `interacts_with`)
with the most specific Biolink predicate each edge type supports. Node classes are already specific
(Protein, Disease, SmallMolecule/Drug, MolecularActivity, BiologicalProcess, CellularComponent).

Rules (subject class -> object class, evidence):
  Protein  - Protein          physically_interacts_with  when a physical-interaction source supports it (BioPlex AP-MS,
                              Reactome); interacts_with when only STRING (functional association, not always physical)
  Protein  - Disease          gene_associated_with_condition (Biolink: GeneOrGeneProduct -> Disease)
  Chemical - Protein          physically_interacts_with   (ligand activity)
  Protein  - MolecularActivity   enables
  Protein  - BiologicalProcess   actively_involved_in
  Protein  - CellularComponent   located_in
The original predicate is kept in `original_predicate`.
"""
import pandas as pd

GO_PREDICATE = {"biolink:MolecularActivity": "biolink:enables",
                "biolink:BiologicalProcess": "biolink:actively_involved_in",
                "biolink:CellularComponent": "biolink:located_in"}
PHYSICAL_SOURCES = ("BioPlex", "Reactome")


def specialise(nodes, edges):
    e = edges.copy()
    e["original_predicate"] = e.predicate
    cat = dict(zip(nodes.id, nodes.category))
    ev = e.evidence
    ppi = ev.str.startswith("pharos:ppi:")
    physical = ppi & ev.str.contains("|".join(PHYSICAL_SOURCES))
    e.loc[physical, "predicate"] = "biolink:physically_interacts_with"
    e.loc[ev == "pharos:disease_association", "predicate"] = "biolink:gene_associated_with_condition"
    e.loc[ev == "pharos:ligand_activity", "predicate"] = "biolink:physically_interacts_with"
    go = ev == "pharos:go"
    e.loc[go, "predicate"] = e.object[go].map(cat).map(GO_PREDICATE).fillna("biolink:related_to")
    return e


def used_classes(nodes, edges):
    """What the standards score looks at: the classes and predicates actually in the graph, with counts."""
    return {"node_classes": nodes.category.value_counts().to_dict(), "predicates": edges.predicate.value_counts().to_dict()}
