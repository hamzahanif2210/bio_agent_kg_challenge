"""One entry point for the things a user does:

  python -m bioagent ask "How is EGFR connected to non-small cell lung carcinoma?"
  python -m bioagent ask --entities BRCA1
  python -m bioagent explain EGFR "non-small cell lung carcinoma"
  python -m bioagent export                 (KGX + PyTorch Geometric files for the whole and pruned graphs)

`ask` needs an LLM only to pick the names out of a sentence: set LLM_API_KEY and LLM_BASE_URL (and optionally LLM_MODEL),
or pass --entities to skip the LLM. The graph is data/processed/pharos_pruned_v3 unless --graph says otherwise.
Large graphs need a few GB of memory: on the cluster run these inside a Slurm job (see README).
"""
import argparse
import os
import sys

DEFAULT_GRAPH = "data/processed/pharos_pruned_v3.whole"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bioagent", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graph", default=DEFAULT_GRAPH, help="whole-graph prefix (default: %(default)s)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ask", help="plain-language question -> the relevant part of the graph")
    a.add_argument("question", nargs="?"); a.add_argument("--entities", nargs="+")
    a.add_argument("--html", help="also write an interactive picture to this file")
    a.add_argument("--model", default=os.environ.get("LLM_MODEL", "gpt-oss"))
    a.add_argument("--base-url", default=os.environ.get("LLM_BASE_URL"))
    x = sub.add_parser("explain", help="why does A connect to B? (sources, evidence, verdicts)")
    x.add_argument("a"); x.add_argument("b")
    sub.add_parser("export", help="write KGX + PyTorch Geometric files to exports/")
    args = ap.parse_args(argv)

    if args.cmd == "ask":
        from bioagent.provenance.explain import load
        from bioagent.qa.ask import answer, extract_entities
        ents = args.entities
        if not ents:
            if not (args.question and args.base_url and os.environ.get("LLM_API_KEY")):
                sys.exit("give a question plus LLM_BASE_URL and LLM_API_KEY, or use --entities NAME [NAME]")
            from bioagent.ingest.harness import openai_llm
            ents = extract_entities(openai_llm(args.base_url, os.environ["LLM_API_KEY"]), args.model, args.question)
            print("entities from the question:", ents)
        graph = load(args.graph, standard=True)
        text, sub = answer(args.graph, ents, graph=graph)
        print(text)
        if args.html and sub.get("edge_rows"):
            from bioagent.qa.visual import to_html
            to_html(sub["edge_rows"], graph[0], " / ".join(ents), args.html)
            print("picture written to", args.html)
    elif args.cmd == "explain":
        from bioagent.provenance.explain import explain, format_explanation
        print(format_explanation(explain(args.graph, args.a, args.b)))
    elif args.cmd == "export":
        import subprocess
        base = args.graph.rsplit(".", 1)[0]
        for part in ("whole", "pruned"):
            subprocess.run([sys.executable, "-m", "bioagent.export.formats", f"{base}.{part}", f"exports/{part}"], check=True)


if __name__ == "__main__":
    main()
