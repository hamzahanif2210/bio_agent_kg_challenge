#!/usr/bin/env bash
# Put the bioagent-kg agent into a NemoClaw sandbox on a Brev instance and ask it one test question.
#   bash deploy/brev/setup.sh nemoclaw            # once: host fixes, web service
#   export NVIDIA_API_KEY=nvapi-...               # your key from build.nvidia.com (never commit it)
#   export NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1 # only after you have read and accepted NVIDIA's notice
#   bash deploy/brev/nemoclaw.sh [openclaw|hermes]
# Verified on Brev (cpu-e2.4vcpu-16gb, Ubuntu 24.04, NemoClaw v0.0.144, model nvidia/nemotron-3.5-super-vl-120b-a12b), 2026-11-17.
set -euo pipefail
AGENT="${1:-openclaw}"
SANDBOX="${SANDBOX:-bioagent-$AGENT}"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
: "${NVIDIA_API_KEY:?export NVIDIA_API_KEY first (build.nvidia.com)}"
umask 022
# The installer refuses group-writable folders on its PATH (the Brev image's umask 0002 creates them).
find "$HOME" -xdev -user "$(id -u)" -type d -perm /022 -exec chmod go-w {} +
export NEMOCLAW_PROVIDER=build NEMOCLAW_POLICY_MODE=suggested NEMOCLAW_NON_INTERACTIVE=1 NEMOCLAW_SANDBOX_NAME="$SANDBOX"

if ! command -v nemoclaw >/dev/null && [ ! -x "$HOME/.local/bin/nemoclaw" ]; then
  # Installs Node 22 (nvm), the NemoClaw CLI and OpenShell, then onboards a first OpenClaw sandbox.
  curl -fsSL https://www.nvidia.com/nemoclaw.sh | NEMOCLAW_AGENT="$AGENT" bash -s -- --non-interactive
fi
source "$HOME/.nvm/nvm.sh" >/dev/null; export PATH="$HOME/.local/bin:$PATH"
nemoclaw list 2>/dev/null | grep -q "$SANDBOX" || nemoclaw onboard --agent "$AGENT" --name "$SANDBOX" --non-interactive

# The sandbox blocks the internet by default; allow only PyPI so the slim requirements can be installed.
nemoclaw "$SANDBOX" policy add pypi --yes
# Upload a clean copy of the repo (no .venv / .git) to /sandbox/bio_agent_kg_challenge.
TMP="$(mktemp -d)"; tar -C "$(dirname "$REPO")" --exclude=.venv --exclude=.git -cf - "$(basename "$REPO")" | tar -C "$TMP" -xf -
[ "$(basename "$REPO")" = bio_agent_kg_challenge ] || mv "$TMP/$(basename "$REPO")" "$TMP/bio_agent_kg_challenge"
nemoclaw "$SANDBOX" upload "$TMP/bio_agent_kg_challenge" /sandbox
nemoclaw "$SANDBOX" skill install "$REPO/agents/bioagent-kg"
nemoclaw "$SANDBOX" exec --timeout 600 -- sh -c \
  "cd /sandbox/bio_agent_kg_challenge && python3 -m venv .venv && .venv/bin/pip install -q -r requirements-serve.txt"

Q="Use the bioagent-kg skill. The repository is at /sandbox/bio_agent_kg_challenge and its Python environment is \
/sandbox/bio_agent_kg_challenge/.venv (use .venv/bin/python with PYTHONPATH=src; do not pip install). \
How is EGFR connected to non-small cell lung carcinoma, and should I trust that link?"
if [ "$AGENT" = openclaw ]; then
  nemoclaw "$SANDBOX" agent --session-id bioagent-test -m "$Q"
else
  # Hermes answers through its OpenAI-compatible API on 127.0.0.1:8642 (model id "hermes-agent").
  T="$(nemoclaw "$SANDBOX" gateway-token --quiet | tail -1)"
  python3 - "$T" "$Q" <<'EOF'
import json, sys, urllib.request
tok, q = sys.argv[1], sys.argv[2]
req = urllib.request.Request("http://127.0.0.1:8642/v1/chat/completions",
    data=json.dumps({"model": "hermes-agent", "messages": [{"role": "user", "content": q}]}).encode(),
    headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
print(json.load(urllib.request.urlopen(req, timeout=600))["choices"][0]["message"]["content"])
EOF
fi
