"""Biolink specialisation: replace the generic predicates the ingest step writes (`related_to`, `interacts_with`)
with the most specific Biolink predicate each edge type supports. Node classes are already specific
(Protein, Disease, SmallMolecule/Drug, MolecularActivity, BiologicalProcess, CellularComponent).

Rules (subject class -> object class, evidence):
  Protein  - Protein          physically_interacts_with  when a physical-interaction source supports it (BioPlex AP-MS,
                              Reactome); interacts_with when only STRING (functional association, not always physical)
  Protein  - Disease          associated_with   (the Biolink 4.4.6 gene-disease predicate gene_associated_with_condition has
                              domain `gene`, so it does not fit a Protein node; it becomes valid once we add gene nodes)
  Chemical - Protein          physically_interacts_with   (ligand activity)
  Protein  - MolecularActivity   capable_of     (`enables` has domain `physical entity`, which Protein does not satisfy)
  Protein  - BiologicalProcess   actively_involved_in
  Protein  - CellularComponent   located_in
The original predicate is kept in `original_predicate`. Checked against the Biolink model with scripts/validate_biolink.py.
"""
import pandas as pd

GO_PREDICATE = {"biolink:MolecularActivity": "biolink:capable_of",
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
    dis = ev == "pharos:disease_association"
    e.loc[dis, "predicate"] = "biolink:associated_with"
    e.loc[dis & (e.subject.map(cat) == "biolink:Gene"), "predicate"] = "biolink:gene_associated_with_condition"
    e.loc[ev == "pharos:ligand_activity", "predicate"] = "biolink:physically_interacts_with"
    go = ev == "pharos:go"
    e.loc[go, "predicate"] = e.object[go].map(cat).map(GO_PREDICATE).fillna("biolink:related_to")
    return e


def used_classes(nodes, edges):
    """What the standards score looks at: the classes and predicates actually in the graph, with counts."""
    return {"node_classes": nodes.category.value_counts().to_dict(), "predicates": edges.predicate.value_counts().to_dict()}
