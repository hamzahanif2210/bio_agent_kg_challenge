"""Minimal reader for the Biolink model YAML (no linkml needed): class ancestry, slot domain/range with inheritance.
The model file is data/external/biolink-model.yaml (download: raw.githubusercontent.com/biolink/biolink-model/master/biolink-model.yaml).
"""
import re

import yaml


class Biolink:
    def __init__(self, path):
        m = yaml.safe_load(open(path))
        self.version, self.classes, self.slots = m["version"], m["classes"], m["slots"]
        self.alias = {n.replace("_", " "): n.replace("_", " ") for n in {**self.classes, **self.slots}}

    @staticmethod
    def _name(curie):
        n = curie.split(":", 1)[1] if ":" in curie else curie
        return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", n.replace("_", " ")).lower()   # SmallMolecule -> small molecule

    def class_ancestors(self, name):
        out, stack = set(), [name]
        while stack:
            c = stack.pop()
            if c in out or c not in self.classes:
                continue
            out.add(c)
            d = self.classes[c]
            stack += [d.get("is_a")] + list(d.get("mixins") or [])
        out.discard(None)
        return out

    def _inherited(self, slot, key):
        while slot:
            d = self.slots.get(slot)
            if d is None:
                return None
            if d.get(key):
                return d[key]
            slot = d.get("is_a")
        return None

    def check_class(self, curie):
        n = self._name(curie)
        return n in self.classes and not self.classes[n].get("deprecated")

    def check_edge(self, subject_class, predicate, object_class):
        """(predicate ok, domain ok, range ok). Unconstrained domain/range count as ok."""
        p = self._name(predicate)
        if p not in self.slots or self.slots[p].get("deprecated"):
            return False, False, False
        dom, rng = self._inherited(p, "domain"), self._inherited(p, "range")
        return (True,
                dom is None or dom in self.class_ancestors(self._name(subject_class)),
                rng is None or rng in self.class_ancestors(self._name(object_class)))

    def predicates_for(self, subject_class, object_class, under="related to"):
        """Slots under `under` whose domain/range accept these classes (to pick the most specific valid predicate)."""
        out = []
        for s in self.slots:
            anc, x = [], s
            while x:
                anc.append(x); x = (self.slots.get(x) or {}).get("is_a")
            if under in anc and not self.slots[s].get("deprecated"):
                ok = self.check_edge(subject_class, "biolink:" + s.replace(" ", "_"), object_class)
                if all(ok):
                    out.append((len(anc), s))
        return [s for _, s in sorted(out, reverse=True)]
