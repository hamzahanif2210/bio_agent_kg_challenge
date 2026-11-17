"""Small local web interface: type names (or a question) in a box, get the answer and the interactive picture.

  python -m bioagent serve --graph sample/sample.whole          then open http://127.0.0.1:8000

Names are separated by commas ("EGFR, non-small cell lung carcinoma"). With LLM_BASE_URL and LLM_API_KEY set, a full
sentence also works. Listens on this machine only (127.0.0.1); on the cluster forward the port with ssh -L.
"""
import html
import json
import os
import secrets
import tempfile
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from bioagent.provenance.explain import explain, load, resolve
from bioagent.qa.ask import answer, extract_entities
from bioagent.qa.visual import to_html
from bioagent.ingest.csv_ingest import format_report, ingest_csv

MAX_UPLOAD = 2_000_000   # bytes
MAX_UPLOADS = 10         # kept in memory, oldest dropped

PAGE = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bio-agent knowledge graph</title>
<style>body{font-family:system-ui,sans-serif;margin:1rem auto;max-width:60rem;padding:0 1rem}
input[type=text]{width:70%;padding:.4rem}button{padding:.4rem .8rem}pre{background:#f5f5f5;padding:.8rem;overflow:auto;white-space:pre-wrap}
iframe{width:100%;height:34rem;border:1px solid #ccc}.n{color:#555;font-size:.9rem}details{margin:.6rem 0}textarea{width:100%;height:7rem;font-family:monospace}
label{margin-right:1rem}</style>
<h1>Bio-agent knowledge graph</h1>
<form action="/" method="get"><input type="text" name="q" value="@@Q@@" placeholder="BRCA1   or   EGFR, non-small cell lung carcinoma" autofocus>
<button>Ask</button><input type="hidden" name="g" value="@@G@@">
<details @@OPEN@@><summary>Options: more hops and filters</summary>
<label>Hops <select name="hops"><option value="">auto (1-2)</option>@@HOPS@@</select></label>
<label>Min confidence <input type="text" name="minconf" value="@@MC@@" size="4"></label>
<label>Node types <input type="text" name="types" value="@@TY@@" size="22" placeholder="Protein, Disease"></label>
<label><input type="checkbox" name="pruned" value="1" @@PR@@> include pruned edges</label>
<div class="n">Hops, confidence and types apply from 3 hops (or whenever hops is set). Two names: the shortest paths up to that many hops.</div></details></form>
<p class="n">Separate names with commas. Green edges were kept, dashed red edges were pruned; click an edge to see why, and drag the cut-off slider to see what a stricter or looser rule would do.@@LLM@@</p>
@@BODY@@
<details><summary>Upload your own measurements (CSV)</summary>
<form action="/upload" method="post"><p class="n">Columns: <b>subject</b>, <b>object</b> (names or ids such as UniProtKB:P00533); optional predicate, subject_category,
object_category, score (0-1), pmid, source. Each row gets a keep/prune verdict with a reason. Your upload is private to this session's
link and is not saved on disk.</p>
<input type="file" id="f" accept=".csv,.tsv,.txt"><textarea name="csv" id="c" placeholder="subject,object,predicate,score,pmid&#10;EGFR,non-small cell lung carcinoma,associated_with,0.8,12345678"></textarea>
<button>Add to the graph</button></form>
<script>document.getElementById('f').onchange=e=>{const r=new FileReader();r.onload=()=>document.getElementById('c').value=r.result;r.readAsText(e.target.files[0])}</script>
</details>"""


def entities_from(text, llm=None, model="gpt-oss"):
    if llm and "," not in text and len(text.split()) > 3:
        return extract_entities(llm, model, text)
    return [t.strip() for t in text.split(",") if t.strip()]


def _opts(qs):
    """hops / min confidence / node types / include pruned from a query string -> keyword arguments for answer()."""
    try:
        hops = int(qs.get("hops") or 0) or None
    except ValueError:
        hops = None
    try:
        mc = min(max(float(qs.get("minconf") or 0), 0.0), 1.0)
    except ValueError:
        mc = 0.0
    types = [x.strip() for x in (qs.get("types") or "").split(",") if x.strip()] or None
    if (mc or types or qs.get("pruned")) and not hops:
        hops = 3
    return dict(hops=min(hops, 5) if hops else None, kept_only=not qs.get("pruned"), min_conf=mc, types=types)


def make_handler(graph, prefix, llm, model):
    pics = {}
    uploads = {}      # id -> (nodes, edges): each upload is its own copy, so one visitor cannot change what another sees

    def graph_for(qs):
        return uploads.get(qs.get("g", ""), graph)

    def add_upload(text, name):
        nodes, edges, rep = ingest_csv(text, graph[0], graph[1], name)
        gid = secrets.token_hex(6)   # unguessable, so one visitor's upload link does not reveal another's
        uploads[gid] = (nodes, edges)
        for old in list(uploads)[:-MAX_UPLOADS]:
            uploads.pop(old)
        return gid, rep

    class H(BaseHTTPRequestHandler):
        def _send(self, body, ctype="text/html; charset=utf-8", code=200):
            data = body.encode()
            self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path.startswith("/pic/") and u.path[5:] in pics:
                return self._send(pics[u.path[5:]])
            if u.path.startswith("/api/") or u.path == "/healthz":
                return self._api(u)
            if u.path != "/":
                return self._send("not found", "text/plain", 404)
            qs = {k: v[0].strip()[:300] for k, v in urllib.parse.parse_qs(u.query).items()}
            q, g = qs.get("q", ""), qs.get("g", "") if qs.get("g", "") in uploads else ""
            body = ""
            if q:
                try:
                    gr = graph_for({"g": g})
                    ents = entities_from(q, llm, model)
                    text, sub = answer(prefix, ents, graph=gr, **_opts(qs))
                    body = f"<pre>{html.escape(text)}</pre>"
                    if sub.get("edge_rows"):
                        key = str(len(pics)); path = os.path.join(tempfile.gettempdir(), f"bioagent_pic_{os.getpid()}_{key}.html")
                        to_html(sub["edge_rows"], gr[0], " / ".join(ents), path)
                        pics[key] = open(path).read(); os.remove(path)
                        body += f'<iframe src="/pic/{key}"></iframe>'
                except Exception as ex:   # show the problem in the page rather than a blank screen
                    body = f"<pre>Something went wrong: {html.escape(type(ex).__name__)}: {html.escape(str(ex)[:200])}</pre>"
            self._send(self._page(q, g, qs, body))

        def _page(self, q, g, qs, body):
            esc = lambda s: html.escape(s, quote=True)
            sel = qs.get("hops", "")
            hops = "".join(f'<option value="{n}"{" selected" if sel == str(n) else ""}>{n}</option>' for n in range(1, 6))
            note = " Full sentences are understood." if llm else " (Set LLM_API_KEY and LLM_BASE_URL to ask in full sentences.)"
            if g:
                note += " You are looking at your uploaded graph."
            adv = any(qs.get(k) for k in ("hops", "minconf", "types", "pruned"))
            return (PAGE.replace("@@Q@@", esc(q)).replace("@@G@@", esc(g)).replace("@@OPEN@@", "open" if adv else "")
                    .replace("@@HOPS@@", hops).replace("@@MC@@", esc(qs.get("minconf", ""))).replace("@@TY@@", esc(qs.get("types", "")))
                    .replace("@@PR@@", "checked" if qs.get("pruned") else "").replace("@@LLM@@", note).replace("@@BODY@@", body))

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            if u.path not in ("/upload", "/api/upload"):
                return self._send("not found", "text/plain", 404)
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_UPLOAD:
                return self._json({"error": f"upload too large (limit {MAX_UPLOAD // 1000} kB)"}, 413)
            raw = self.rfile.read(n).decode("utf-8", "replace")
            ctype = self.headers.get("Content-Type", "")
            text = urllib.parse.parse_qs(raw).get("csv", [""])[0] if "urlencoded" in ctype else raw
            try:
                gid, rep = add_upload(text, "upload.csv")
            except Exception as ex:
                if u.path == "/api/upload":
                    return self._json({"error": f"{type(ex).__name__}: {str(ex)[:200]}"}, 400)
                return self._send(self._page("", "", {}, f"<pre>Could not read the table: {html.escape(str(ex)[:300])}</pre>"), code=400)
            if u.path == "/api/upload":
                return self._json({"graph_id": gid, **rep})
            first = rep["rows"][0] if rep["rows"] else None
            link = (f'<p><a href="/?g={gid}&amp;q={urllib.parse.quote(first["subject"])}">Look at {html.escape(first["subject"])} in your graph</a></p>'
                    if first else "")
            body = f"<pre>{html.escape(format_report(rep))}</pre>{link}"
            self._send(self._page("", gid, {}, body))

        def _json(self, obj, code=200):
            self._send(json.dumps(obj, default=str), "application/json", code)

        def _api(self, u):
            """JSON endpoints: GET /healthz, /api/stats[?threshold=], /api/ask?q=[&hops=&minconf=&types=&pruned=1], /api/explain?a=&b=, /api/node?q=;
            POST /api/upload (CSV text) returns the per-row verdicts and a graph_id to pass as g=. Uploads never change the shared graph."""
            qs = {k: v[0].strip()[:300] for k, v in urllib.parse.parse_qs(u.query).items()}
            nodes, edges = graph_for(qs)
            gr = (nodes, edges)
            try:
                if u.path == "/healthz":
                    return self._json({"ok": True})
                if u.path == "/api/stats":
                    kept = int((edges["verdict"] == "keep").sum()) if "verdict" in edges else None
                    out = {"nodes": len(nodes), "edges": len(edges), "kept": kept, "pruned": None if kept is None else len(edges) - kept}
                    if qs.get("threshold") and "verdict_confidence" in edges:
                        th = float(qs["threshold"])
                        k = int((edges["verdict_confidence"].fillna(0) >= th).sum())
                        out.update({"threshold": th, "kept_at_threshold": k, "pruned_at_threshold": len(edges) - k})
                    return self._json(out)
                if u.path == "/api/ask":
                    if not qs.get("q"):
                        return self._json({"error": "missing q"}, 400)
                    ents = entities_from(qs["q"], llm, model)
                    text, sub = answer(prefix, ents, graph=gr, **_opts(qs))
                    return self._json({"entities": ents, "answer": text, "edges": sub.get("edge_rows", [])[:200]})
                if u.path == "/api/explain":
                    if not (qs.get("a") and qs.get("b")):
                        return self._json({"error": "missing a or b"}, 400)
                    return self._json(explain(prefix, qs["a"], qs["b"], graph=gr))
                if u.path == "/api/node":
                    if not qs.get("q"):
                        return self._json({"error": "missing q"}, 400)
                    nid = resolve(nodes, qs["q"])
                    row = nodes[nodes.id == nid].iloc[0].to_dict()
                    return self._json(row)
            except Exception as ex:
                return self._json({"error": f"{type(ex).__name__}: {str(ex)[:200]}"}, 400)
            return self._json({"error": "not found"}, 404)

        def log_message(self, *a):
            pass
    return H


def serve(prefix, port=8000, llm=None, model="gpt-oss", host="127.0.0.1"):
    """host stays 127.0.0.1 unless you choose otherwise (a hosted deployment sets 0.0.0.0 and puts its own proxy in front)."""
    graph = load(prefix, standard=True)
    srv = HTTPServer((host, port), make_handler(graph, prefix, llm, model))
    print(f"open http://{host}:{port}  (Ctrl-C to stop)", flush=True)
    srv.serve_forever()
