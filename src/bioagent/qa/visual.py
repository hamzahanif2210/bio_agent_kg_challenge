"""Interactive picture of an answer: a self-contained HTML page (open it in any browser). Nodes are coloured by class, edges by
verdict (green keep, red dashed prune); click an edge to see its lineage: source, evidence, scores, verdict and reason.
The vis-network library (v9.1.9, Apache-2.0 / MIT, see assets/NOTICE) is embedded in the page, so it draws offline.
"""
import html
import json
import os

VIS_JS = os.path.join(os.path.dirname(__file__), "assets", "vis-network.min.js")
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
                   "vc": _num(r.get("verdict_confidence")), "keep0": not pruned,
                   "info": {"predicate": r.get("predicate"), "source": r.get("source"), "evidence": r.get("evidence"),
                            "source score": _num(r.get("confidence")), "verdict": r.get("verdict"),
                            "verdict confidence": _num(r.get("verdict_confidence")), "reason": r.get("reason"),
                            "rule": r.get("rule"), "PubMed co-mentions": _num(r.get("pubmed_count"))}})
    page = f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>body{{font-family:system-ui,sans-serif;margin:0;display:flex;flex-direction:column;height:100vh;overflow:hidden}}
h1{{font-size:1rem;margin:.6rem 1rem}}#g{{flex:1 1 0;min-height:0;position:relative;overflow:hidden;border-top:1px solid #ccc}}#d{{flex:none;max-height:30vh;overflow:auto;padding:.6rem 1rem;border-top:1px solid #ccc;min-height:3rem;font-size:.9rem}}#s{{flex:none}}
td{{padding:0 .8rem 0 0;vertical-align:top}}</style>
<h1>{html.escape(title)}</h1>
<div id="s" style="padding:.3rem 1rem;font-size:.9rem"><b>What if the cut-off were different?</b>
<input id="t" type="range" min="0" max="1" step="0.05" value="0.4" style="vertical-align:middle;width:12rem">
cut-off <b id="tv">0.40</b>: <span id="cnt"></span>
<label><input id="hp" type="checkbox"> hide pruned</label> <button id="rs">original verdicts</button>
<span style="color:#555"> Edges below the cut-off turn red and dashed. The pipeline's own cut-off is 0.40.</span></div><div id="g"></div><div id="d">Click an edge to see where it comes from and why it is kept or pruned.</div>
<script>{open(VIS_JS, encoding="utf-8").read()}</script>
<script>
const nodes=new vis.DataSet({json.dumps(vn)}), edges=new vis.DataSet({json.dumps(ve)}.map((e,i)=>({{...e,id:i}})));
const net=new vis.Network(document.getElementById('g'),{{nodes,edges}},{{physics:{{stabilization:true}},edges:{{font:{{size:9}},smooth:true}},nodes:{{shape:'dot',size:14,font:{{size:12}}}}}});
const T=document.getElementById('t'),HP=document.getElementById('hp'),CNT=document.getElementById('cnt');
function paint(useOrig){{const t=parseFloat(T.value);document.getElementById('tv').textContent=t.toFixed(2);let k=0,p=0;
edges.update(edges.get().map(e=>{{const keep=useOrig||e.vc===null?e.keep0:e.vc>=t;keep?k++:p++;
return {{id:e.id,dashes:!keep,color:keep?'#2ca02c':'#d62728',hidden:!keep&&HP.checked,info:{{...e.info,'at this cut-off':keep?'keep':'prune'}}}}}}));
CNT.textContent=k+' kept, '+p+' pruned'+(useOrig?' (original verdicts)':'')}}
T.oninput=()=>paint(false);HP.onchange=()=>paint(false);
document.getElementById('rs').onclick=()=>{{T.value=0.4;paint(true)}};paint(true);
net.on('click',p=>{{const d=document.getElementById('d');if(!p.edges.length)return;const i=edges.get(p.edges[0]).info;
d.innerHTML='<table>'+Object.entries(i).filter(([k,v])=>v!==null&&v!==undefined).map(([k,v])=>'<tr><td><b>'+k+'</b></td><td>'+String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</td></tr>').join('')+'</table>'}});
</script>"""
    with open(path, "w") as f:
        f.write(page)
