"""Ontology classes and properties behind every Biolink class and predicate we use, and resolvable IRIs for node ids.

Biolink class and predicate names are the schema layer; this module adds the OBO-style terms they stand for, so that a node or edge
is recognisable as an existing ontology class or property (for example a protein-coding gene as SO:0001217, a protein as PR:000000001).
The mappings below are the ones declared in the Biolink model 4.4.6 (exact mappings, narrow mappings for predicates) plus the
specific protein-coding-gene class. A predicate with no declared OBO property (associated_with, gene_associated_with_condition) is left
empty on purpose: we do not invent a mapping.
"""
import re

CLASS_TERM = {
    "biolink:Protein": "PR:000000001",
    "biolink:Gene": "SO:0000704",
    "biolink:Disease": "MONDO:0000001",
    "biolink:SmallMolecule": "CHEBI:23367",      # molecular entity; Biolink SmallMolecule declares no exact mapping
    "biolink:BiologicalProcess": "GO:0008150",
    "biolink:MolecularActivity": "GO:0003674",
    "biolink:CellularComponent": "GO:0005575",
    "biolink:Pathway": "PW:0000001",
    "biolink:PhenotypicFeature": "UPHENO:0001001",
    "biolink:AnatomicalEntity": "UBERON:0001062",
}
PROTEIN_CODING_GENE = "SO:0001217"

PREDICATE_TERM = {
    "biolink:has_gene_product": "RO:0002205",
    "biolink:capable_of": "RO:0002215",
    "biolink:actively_involved_in": "RO:0002331",
    "biolink:located_in": "RO:0001025",
    "biolink:participates_in": "RO:0000056",
    "biolink:has_phenotype": "RO:0002200",
    "biolink:expressed_in": "RO:0002206",
    "biolink:subclass_of": "rdfs:subClassOf",
    "biolink:interacts_with": "RO:0002434",
    "biolink:physically_interacts_with": "RO:0002436",
}

OBO = {"SO", "PR", "MONDO", "GO", "UBERON", "UPHENO", "PW", "CHEBI", "RO", "HP", "BFO"}
IRI = {"rdfs": "http://www.w3.org/2000/01/rdf-schema#", "UniProtKB": "https://identifiers.org/uniprot:", "ENSEMBL": "https://identifiers.org/ensembl:",
       "REACT": "https://reactome.org/content/detail/", "PHAROS.LIGAND": "https://pharos.nih.gov/ligands/", "PHAROS": "https://pharos.nih.gov/ligands/"}


def iri(curie):
    """Resolvable IRI for a CURIE, or None if we do not know the prefix."""
    if not isinstance(curie, str) or ":" not in curie:
        return None
    p, local = curie.split(":", 1)
    if p in OBO:
        return f"http://purl.obolibrary.org/obo/{p}_{local}"
    if p in IRI:
        return IRI[p] + local
    return None


def node_class(category, biotype=None):
    """Ontology class for a node: protein_coding genes get the specific SO class."""
    if category == "biolink:Gene" and biotype == "protein_coding":
        return PROTEIN_CODING_GENE
    return CLASS_TERM.get(category)


def annotate_nodes(nodes):
    """Add ontology_class, ontology_class_iri and iri columns (nodes: id, category[, biotype])."""
    n = nodes.copy()
    bio = n["biotype"] if "biotype" in n.columns else [None] * len(n)
    n["ontology_class"] = [node_class(c, b) for c, b in zip(n.category, bio)]
    n["ontology_class_iri"] = n.ontology_class.map(iri)
    n["iri"] = n.id.map(iri)
    return n


def annotate_edges(edges):
    e = edges.copy()
    e["predicate_ontology"] = e.predicate.map(PREDICATE_TERM)
    e["predicate_iri"] = e.predicate_ontology.map(iri)
    return e
