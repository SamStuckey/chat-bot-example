#!/usr/bin/env bash
# Start Docker in a Claude Code cloud session and build the proxy-aware base image.
# Safe to run more than once. Then use Compose with the cloud override:
#   docker compose -f compose.yaml -f .claude/cloud/compose.cloud.yaml up --build -d
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"

if ! docker info >/dev/null 2>&1; then
  nohup dockerd >/var/log/dockerd.log 2>&1 &
  for _ in $(seq 1 30); do
    docker info >/dev/null 2>&1 && break
    sleep 1
  done
fi
docker info >/dev/null 2>&1 || { echo "dockerd didn't start; see /var/log/dockerd.log" >&2; exit 1; }

# The session's proxy adds the real OpenAI key to requests, so .env only needs a placeholder.
env_file="$here/../../.env"
if [ ! -f "$env_file" ]; then
  printf 'OPENAI_API_KEY=proxy-injected\nPENNY_CACHE_KEY_SECRET=%s\n' "$(openssl rand -hex 32)" >"$env_file"
fi

cp /root/.ccr/ca-bundle.crt "$here/proxy-ca.crt"
docker build -q -t penny-cloud/python:3.14.4-slim-bookworm \
  -f "$here/python-base.Dockerfile" "$here" >/dev/null
echo "docker: ready"
