#!/usr/bin/env bash
# Run on a fresh NVIDIA Brev instance (Ubuntu 24.04): bash deploy/brev/setup.sh [openclaw|nemoclaw|hermes|pi]
# Installs this repo's slim requirements, starts the web service on port 8000, installs the skill for the chosen agent,
# and fixes three things on the stock Brev image that make the NemoClaw installer fail (found on a real run, 2026-11-17):
#   1. `strings` (binutils) is missing           -> "'strings' (from binutils) is required"
#   2. umask 0002 leaves ~ group-writable        -> "Unsafe npm executable directory" / "Unsafe user-local executable directory"
#   3. ufw blocks the OpenShell Docker bridge    -> "Sandbox containers cannot reach the gateway at host.openshell.internal:8080"
# It never asks for or stores keys: the agent's own installer reads its model key.
set -euo pipefail
AGENT="${1:-openclaw}"
cd "$(dirname "$0")/../.."
umask 022
sudo apt-get update -y && sudo apt-get install -y python3-venv curl binutils
mkdir -p "$HOME/.local/bin"
find "$HOME" -xdev -user "$(id -u)" -type d -perm /022 -exec chmod go-w {} +   # ~, ~/.local, ~/.local/bin, ... (umask 0002 leftovers)
if sudo ufw status 2>/dev/null | grep -q "Status: active"; then
  # Only the OpenShell Docker bridge may reach the gateway port; nothing is opened to the internet.
  sudo ufw allow from 172.18.0.0/16 to 172.18.0.1 port 8080 proto tcp
fi
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-serve.txt
export PYTHONPATH="$PWD/src"
python scripts/compile_agent.py "$AGENT" --user
nohup env HOST=0.0.0.0 PORT=8000 python -m bioagent --graph sample/sample.whole serve > serve.log 2>&1 &
echo "web service: port 8000 (open it from the Brev instance page)."
case "$AGENT" in
  nemoclaw|openclaw) echo "next: export NVIDIA_API_KEY=...  then  bash deploy/brev/nemoclaw.sh openclaw" ;;
  hermes)            echo "next: export NVIDIA_API_KEY=...  then  bash deploy/brev/nemoclaw.sh hermes" ;;
  pi)                echo "next: npm install -g --ignore-scripts @earendil-works/pi-coding-agent   then run pi in this folder and /login" ;;
esac
