# qa: ask, explain, multi-hop, web workbench

`ask.py` (names to subgraph), `hops.py` (multi-hop with filters), `serve.py` (web page and JSON API), `visual.py` (interactive picture with the cut-off slider).

### Server API endpoints (`src/bioagent/qa/serve.py`)

Read-only, JSON, no authentication; the server listens on `127.0.0.1:8000` unless `--host` or `HOST` says otherwise (`--port` or `PORT` for the port).

| Method and path | Parameters | Returns |
|---|---|---|
| `GET /` | `q` (names, comma-separated, or a sentence if an LLM is set) | HTML page with the answer and picture |
| `GET /pic/<n>` | | the interactive picture made for a page request |
| `GET /healthz` | | `{"ok": true}` |
| `GET /api/stats` | optional `threshold`, `g` | node, edge, kept and pruned counts; with `threshold`, the counts at that confidence cut-off |
| `GET /api/node` | `q` (id or exact name) | the node record |
| `GET /api/ask` | `q`; optional `hops` (1-5), `minconf`, `types` (comma list), `pruned=1`, `g` | `{entities, answer, edges[]}`: best-supported kept neighbours (or the connection) with verdicts; with `hops`, the multi-hop search and its filters |
| `POST /api/upload` | CSV text as the body (2 MB at most) | per-row verdicts and a `graph_id`; pass it as `g=` to the other endpoints to query your graph. Each upload is a private copy in memory: it never changes the shared graph and is not written to disk |
| `GET /api/explain` | `a`, `b` | direct edges and shared-neighbour paths between A and B with source, evidence, verdict, rule and reason |

The home page has the same options (hops, confidence, node types) and an upload box. Errors come back as `{"error": "..."}` with status 400 or 404. Example: `curl 'http://127.0.0.1:8000/api/explain?a=EGFR&b=non-small%20cell%20lung%20carcinoma'`.
