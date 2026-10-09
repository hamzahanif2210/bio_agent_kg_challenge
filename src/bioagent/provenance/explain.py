"""Edge lineage: answer 'why does A connect to B?'"""
from bioagent.schema.kg import read_kg


def explain(prefix, a, b):
    _, e = read_kg(prefix)
    hit = e[((e.subject == a) & (e.object == b)) | ((e.subject == b) & (e.object == a))]
    return hit[["subject", "predicate", "object", "source", "evidence",
                "confidence", "method", "timestamp"]].to_dict("records")
