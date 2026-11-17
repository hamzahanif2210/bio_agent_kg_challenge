"""Small local web interface: type names (or a question) in a box, get the answer and the interactive picture.

  python -m bioagent serve --graph sample/sample.whole          then open http://127.0.0.1:8000

Names are separated by commas ("EGFR, non-small cell lung carcinoma"). With LLM_BASE_URL and LLM_API_KEY set, a full
sentence also works. Listens on this machine only (127.0.0.1); on the cluster forward the port with ssh -L.
"""
import html
import json
import os
import tempfile
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from bioagent.provenance.explain import explain, load, resolve
from bioagent.qa.ask import answer, extract_entities
from bioagent.qa.visual import to_html

PAGE = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bio-agent knowledge graph</title>
<style>body{{font-family:system-ui,sans-serif;margin:1rem auto;max-width:60rem;padding:0 1rem}}
input[type=text]{{width:70%;padding:.4rem}}button{{padding:.4rem .8rem}}pre{{background:#f5f5f5;padding:.8rem;overflow:auto;white-space:pre-wrap}}
iframe{{width:100%;height:32rem;border:1px solid #ccc}}.n{{color:#555;font-size:.9rem}}</style>
<h1>Bio-agent knowledge graph</h1>
<form action="/" method="get"><input type="text" name="q" value="{q}" placeholder="BRCA1   or   EGFR, non-small cell lung carcinoma" autofocus>
<button>Ask</button></form>
<p class="n">Separate names with commas. Green edges were kept, dashed red edges were pruned; click an edge to see why.{llm}</p>
{body}"""


def entities_from(text, llm=None, model="gpt-oss"):
    if llm and "," not in text and len(text.split()) > 3:
        return extract_entities(llm, model, text)
    return [t.strip() for t in text.split(",") if t.strip()]


def make_handler(graph, prefix, llm, model):
    pics = {}

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
            q = urllib.parse.parse_qs(u.query).get("q", [""])[0].strip()[:300]
            body = ""
            if q:
                try:
                    ents = entities_from(q, llm, model)
                    text, sub = answer(prefix, ents, graph=graph)
                    body = f"<pre>{html.escape(text)}</pre>"
                    if sub.get("edge_rows"):
                        key = str(len(pics)); path = os.path.join(tempfile.gettempdir(), f"bioagent_pic_{os.getpid()}_{key}.html")
                        to_html(sub["edge_rows"], graph[0], " / ".join(ents), path)
                        pics[key] = open(path).read(); os.remove(path)
                        body += f'<iframe src="/pic/{key}"></iframe>'
                except Exception as ex:   # show the problem in the page rather than a blank screen
                    body = f"<pre>Something went wrong: {html.escape(type(ex).__name__)}: {html.escape(str(ex)[:200])}</pre>"
            self._send(PAGE.format(q=html.escape(q, quote=True), body=body,
                                   llm=" Full sentences are understood." if llm else " (Set LLM_API_KEY and LLM_BASE_URL to ask in full sentences.)"))

        def _json(self, obj, code=200):
            self._send(json.dumps(obj, default=str), "application/json", code)

        def _api(self, u):
            """JSON endpoints. All read-only: GET /healthz, /api/stats, /api/ask?q=, /api/explain?a=&b=, /api/node?q="""
            qs = {k: v[0].strip()[:300] for k, v in urllib.parse.parse_qs(u.query).items()}
            nodes, edges = graph
            try:
                if u.path == "/healthz":
                    return self._json({"ok": True})
                if u.path == "/api/stats":
                    kept = int((edges["verdict"] == "keep").sum()) if "verdict" in edges else None
                    return self._json({"nodes": len(nodes), "edges": len(edges), "kept": kept,
                                       "pruned": None if kept is None else len(edges) - kept})
                if u.path == "/api/ask":
                    if not qs.get("q"):
                        return self._json({"error": "missing q"}, 400)
                    ents = entities_from(qs["q"], llm, model)
                    text, sub = answer(prefix, ents, graph=graph)
                    return self._json({"entities": ents, "answer": text, "edges": sub.get("edge_rows", [])[:200]})
                if u.path == "/api/explain":
                    if not (qs.get("a") and qs.get("b")):
                        return self._json({"error": "missing a or b"}, 400)
                    return self._json(explain(prefix, qs["a"], qs["b"], graph=graph))
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
