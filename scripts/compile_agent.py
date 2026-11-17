"""Install the bioagent-kg skill for an agent harness.  python scripts/compile_agent.py {pi,openclaw,nemoclaw,hermes} [--user]

All four read the same SKILL.md format (a folder with SKILL.md, YAML name + description), so "compiling" is copying
agents/bioagent-kg into the folder each one scans. Project install (default) writes inside the repo; --user writes to the home folder.
  pi        .agents/skills/                 (user: ~/.agents/skills/)
  openclaw  skills/                         (user: ~/.openclaw/skills/)      NemoClaw runs OpenClaw in its sandbox, so use this one
  nemoclaw  skills/                         same as openclaw
  hermes    ~/.hermes/skills/research/      (always the user folder; Hermes keeps its skills there)
Folder names follow each project's docs; run the agent's own skill listing afterwards to confirm it was picked up.
"""
import argparse, pathlib, re, shutil, sys

SRC = pathlib.Path(__file__).resolve().parents[1] / "agents" / "bioagent-kg"
ROOT = SRC.parents[1]
DEST = {"pi": (ROOT / ".agents/skills", pathlib.Path.home() / ".agents/skills"),
        "openclaw": (ROOT / "skills", pathlib.Path.home() / ".openclaw/skills"),
        "nemoclaw": (ROOT / "skills", pathlib.Path.home() / ".openclaw/skills"),
        "hermes": (pathlib.Path.home() / ".hermes/skills/research", pathlib.Path.home() / ".hermes/skills/research")}


def check(md):
    m = re.match(r"---\n(.*?)\n---\n", md, re.S)
    if not m:
        sys.exit("SKILL.md has no frontmatter")
    meta = dict(l.split(":", 1) for l in m.group(1).splitlines() if ":" in l)
    name, desc = meta.get("name", "").strip(), meta.get("description", "").strip()
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64 or not desc or len(desc) > 1024:
        sys.exit("name must be lowercase-hyphen (<=64 chars) and description 1..1024 chars")
    return name


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", choices=sorted(DEST)); ap.add_argument("--user", action="store_true")
    a = ap.parse_args(argv)
    name = check((SRC / "SKILL.md").read_text())
    out = DEST[a.target][1 if a.user else 0] / name
    shutil.copytree(SRC, out, dirs_exist_ok=True)
    print(f"installed {name} for {a.target}: {out}")


if __name__ == "__main__":
    main()
