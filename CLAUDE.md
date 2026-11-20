# Penny

A chat assistant for Greenpenny, a fictional app. FastAPI, Pydantic AI, OpenAI,
SQLite. Start with the [README](README.md); conventions are in
[docs/code-standards.md](docs/code-standards.md).

## Checks

Python 3.14 and the dependencies are installed with uv. Run these before
committing:

```bash
uv run pytest -q
uv run ruff check && uv run ruff format --check
uv run pyright
```

Tests use scripted models and never call OpenAI. After changing an API route
or schema, regenerate `tests/penny/openapi.json` (see
[docs/development.md](docs/development.md#evals-and-the-api-contract)).

## Docker in Claude Code cloud sessions

Docker is installed but its daemon isn't running when a session starts, and
the session reaches the internet through a proxy. Before using Docker:

```bash
.claude/cloud/docker-up.sh
export COMPOSE_FILE=compose.yaml:.claude/cloud/compose.cloud.yaml
```

The script starts the daemon, builds a base image that trusts the proxy, and
creates `.env` if it's missing. The Compose override puts builds, the app and
the dev tools on host networking. After that the usual commands work:
`docker compose up --build -d`, `docker compose run --rm dev pytest`, and the
evals. The proxy adds the real OpenAI key to requests, so the evals and real
chats work with the placeholder key in `.env`. Evals spend real tokens; run
them when a change calls for it.

None of this is needed, or used, outside cloud sessions.
