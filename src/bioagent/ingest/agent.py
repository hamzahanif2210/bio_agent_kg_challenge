"""TODO (ingest owner): Claude tool-use agent. Tools = fetchers for public
sources (UniProt, Open Targets, GO/MONDO, Monarch KGHub...). Each fetched
fact -> Biolink category/predicate + CURIE, written with provenance columns.
Only train edges may be used as seeds (no test leakage)."""
