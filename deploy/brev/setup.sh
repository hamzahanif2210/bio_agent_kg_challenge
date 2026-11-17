#!/usr/bin/env bash
# Run on a fresh NVIDIA Brev instance (Ubuntu): bash deploy/brev/setup.sh [openclaw|nemoclaw|hermes|pi]
# Installs this repo's slim requirements, starts the web service on port 8000, and installs the skill for the chosen agent.
# It never asks for or stores keys: the agent's own installer prompts for its model key.
set -euo pipefail
AGENT="${1:-openclaw}"
cd "$(dirname "$0")/../.."
sudo apt-get update -y && sudo apt-get install -y python3-venv curl
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-serve.txt
export PYTHONPATH="$PWD/src"
python scripts/compile_agent.py "$AGENT" --user
nohup env HOST=0.0.0.0 PORT=8000 python -m bioagent --graph sample/sample.whole serve > serve.log 2>&1 &
echo "web service: port 8000 (open it from the Brev instance page)."
case "$AGENT" in
  nemoclaw) echo "next: curl -fsSL https://nvidia.com/nemoclaw.sh | bash   then   nemoclaw onboard" ;;
  openclaw) echo "next: install OpenClaw (see docs.openclaw.ai), then   openclaw onboard" ;;
  hermes)   echo "next: install Hermes Agent (github.com/NousResearch/hermes-agent), then start a new session and run /skills" ;;
  pi)       echo "next: npm install -g --ignore-scripts @earendil-works/pi-coding-agent   then run pi in this folder and /login" ;;
esac
