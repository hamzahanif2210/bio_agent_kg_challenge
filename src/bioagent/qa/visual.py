"""Interactive picture of an answer: a self-contained HTML page (open it in any browser). Nodes are coloured by class, edges by
verdict (green keep, red dashed prune); click an edge to see its lineage: source, evidence, scores, verdict and reason.
The page loads the vis-network library from cdnjs, so it needs internet to draw.
"""
import html
import json

VIS = "https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/standalone/umd/vis-network.min.js"
COLORS = {"Protein": "#4e79a7", "Disease": "#e15759", "SmallMolecule": "#76b7b2", "Drug": "#76b7b2", "Gene": "#59a14f",
          "BiologicalProcess": "#edc948", "MolecularActivity": "#b07aa1", "CellularComponent": "#ff9da7"}


def _num(x):
    return None if x is None or x != x else round(float(x), 3)


def to_html(edge_rows, nodes, title, path):
    """edge_rows: dicts with subject, object, predicate, source, evidence, confidence, verdict, verdict_confidence, reason."""
    name, cat = dict(zip(nodes.id, nodes.name)), dict(zip(nodes.id, nodes.category))
    seen, vn, ve = {}, [], []
    for r in edge_rows:
        for i in (r["subject"], r["object"]):
            if i not in seen:
                seen[i] = True
                c = str(cat.get(i, "")).replace("biolink:", "")
                vn.append({"id": i, "label": str(name.get(i, i)), "title": f"{i} ({c})", "color": COLORS.get(c, "#999999")})
        pruned = r.get("verdict") == "prune"
        ve.append({"from": r["subject"], "to": r["object"], "arrows": "to", "dashes": pruned,
                   "color": "#d62728" if pruned else "#2ca02c", "label": str(r.get("predicate", "")).replace("biolink:", "")[:24],
                   "info": {"predicate": r.get("predicate"), "source": r.get("source"), "evidence": r.get("evidence"),
                            "source score": _num(r.get("confidence")), "verdict": r.get("verdict"),
                            "verdict confidence": _num(r.get("verdict_confidence")), "reason": r.get("reason"),
                            "rule": r.get("rule"), "PubMed co-mentions": _num(r.get("pubmed_count"))}})
    page = f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>body{{font-family:system-ui,sans-serif;margin:0;display:flex;flex-direction:column;height:100vh}}
h1{{font-size:1rem;margin:.6rem 1rem}}#g{{flex:1;border-top:1px solid #ccc}}#d{{padding:.6rem 1rem;border-top:1px solid #ccc;min-height:6rem;font-size:.9rem}}
td{{padding:0 .8rem 0 0;vertical-align:top}}</style>
<h1>{html.escape(title)}</h1><div id="g"></div><div id="d">Click an edge to see where it comes from and why it is kept or pruned.</div>
<script src="{VIS}"></script>
<script>
const nodes=new vis.DataSet({json.dumps(vn)}), edges=new vis.DataSet({json.dumps(ve)}.map((e,i)=>({{...e,id:i}})));
const net=new vis.Network(document.getElementById('g'),{{nodes,edges}},{{physics:{{stabilization:true}},edges:{{font:{{size:9}},smooth:true}},nodes:{{shape:'dot',size:14,font:{{size:12}}}}}});
net.on('click',p=>{{const d=document.getElementById('d');if(!p.edges.length)return;const i=edges.get(p.edges[0]).info;
d.innerHTML='<table>'+Object.entries(i).filter(([k,v])=>v!==null&&v!==undefined).map(([k,v])=>'<tr><td><b>'+k+'</b></td><td>'+String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</td></tr>').join('')+'</table>'}});
</script>"""
    with open(path, "w") as f:
        f.write(page)
