# agents: the Agent Skill

`bioagent-kg/SKILL.md` packages the query tools (ask, explain, multi-hop, ingest-csv) as one Agent Skill that pi, OpenClaw, NemoClaw and Hermes Agent can use. Install it with `python scripts/compile_agent.py {pi,openclaw,nemoclaw,hermes} [--user]`, or inside a NemoClaw sandbox with `nemoclaw <sandbox> skill install agents/bioagent-kg`. How it was run on NVIDIA Brev: [deploy/README.md](../deploy/README.md).
