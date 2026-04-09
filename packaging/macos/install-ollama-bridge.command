#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${HOME}/Applications/WebmasterOS/OllamaBridge"
CONFIG_ROOT="${HOME}/Library/Application Support/WebmasterOS/OllamaBridge"
CONFIG_PATH="${CONFIG_ROOT}/config.json"
PYTHON_CMD="${PYTHON_CMD:-python3}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BRIDGE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

mkdir -p "${INSTALL_ROOT}" "${CONFIG_ROOT}"
cp "${BRIDGE_ROOT}/bridge.py" "${INSTALL_ROOT}/bridge.py"
cp "${BRIDGE_ROOT}/config/default-config.json" "${INSTALL_ROOT}/default-config.json"

if [[ ! -f "${CONFIG_PATH}" ]]; then
cat > "${CONFIG_PATH}" <<EOF
{
  "host": "127.0.0.1",
  "port": 19081,
  "ollama_url": "${OLLAMA_URL}",
  "allow_origins": [],
  "auto_detect_upstream": true
}
EOF
fi

cat > "${INSTALL_ROOT}/run-ollama-bridge.command" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec "${PYTHON_CMD}" "${INSTALL_ROOT}/bridge.py" --config "${CONFIG_PATH}"
EOF
chmod +x "${INSTALL_ROOT}/run-ollama-bridge.command"

echo "Installed WebmasterOS Ollama Bridge to ${INSTALL_ROOT}"
echo "Config path: ${CONFIG_PATH}"
echo "Run with: ${INSTALL_ROOT}/run-ollama-bridge.command"
