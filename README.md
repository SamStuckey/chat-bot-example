# Penny

Penny is a chat assistant for Greenpenny, a made-up app where families raise
money for their schools through everyday shopping: each participating product
they buy earns Pennies for the school they've linked. Penny suggests products
based on what a household buys and what it has asked Penny to remember, finds
the Bonus Pennies offers running now, and explains the referral program,
including the user's own referral code. Replies stream back as Markdown text
and as product and promotion cards.

It's a Python service built with FastAPI and Pydantic AI on OpenAI models,
backed by SQLite, with a small browser client and a Jaeger trace viewer. The
whole thing runs locally with one Docker Compose command. The schools,
families, products and six months of purchase history are all generated
sample data.

## How it works

Each user has one long-running conversation, so most of the engineering is
about what the model sees on each request and how that stays useful as the
conversation grows.

- **Two records of every conversation.** The transcript is what the user saw,
  stored once and never changed. The model history is what the model works
  from. Clearing and summarizing only ever change the model's view.
- **Context that isn't saved.** The user's name, school, saved guidance and
  local time are added to each outgoing request and never written into
  history, so they can't go stale or end up summarized.
- **Clear, then summarize.** At 75% of a token budget, old tool results are
  replaced with a placeholder. If that isn't enough, a cheaper model
  summarizes older history using a fixed template, and the summary is
  rejected if a required heading is missing. The summary and the point it
  covers are saved, so later turns reload exactly the same context. History
  is never truncated silently.
- **Looking back.** A full-text search tool lets the model find earlier
  messages by words or by dates in the user's own time zone.

Around that:

- **Grounded answers.** Products and promotions appear only as cards built
  from database records. The model picks IDs, and the server refuses unknown
  products, expired offers and anything on the user's avoid list.
- **Narrow, user-scoped tools.** Fifteen typed tools cover lookups, cards,
  safety policies and saved preferences. The user ID comes from the verified
  token, never from a tool argument. Every call is counted against a per-turn
  limit, size-checked and audited with free text redacted.
- **Content as data.** Persona, scope, safety policies and program knowledge
  are Markdown files published into a versioned table. Each turn reads one
  snapshot, and a content change applies from the next turn without a
  restart.
- **Safety.** An always-loaded core tells the model when to read a detailed
  policy on allergies, dietary claims, children, product misuse or crisis.
  The catalog has no ingredient data, so Penny never promises a product is
  safe.
- **A real streaming API.** NDJSON events, a Stop button that keeps the
  partial reply, generation that survives a dropped connection, and
  idempotent sends that replay instead of running twice.
- **Traces without content.** OpenTelemetry records timings, token usage,
  estimated cost and compaction events, never message text.

[Architecture](docs/architecture.md) covers the design and the API in depth.

## Stack

| Part | Built with |
|---|---|
| API | FastAPI, streaming NDJSON |
| Agent | Pydantic AI, with `pydantic-ai-harness` for clearing and compaction |
| Models | OpenAI Responses API: `gpt-6.1-terra` for chat, `gpt-6-luna` for summaries (both configurable) |
| Storage | SQLite through async SQLAlchemy, Alembic migrations, FTS5 for history search |
| Auth | RS256 bearer tokens, verified on every request |
| Tracing | OpenTelemetry, exported to Jaeger |
| Client | One page of plain JavaScript, no build step |
| Checks | pytest with scripted models, Ruff, Pyright in strict mode, pip-audit, real-model evals |

## Quick start

You need Docker with Compose v2 and an OpenAI API key. Ports 8000 and 16686
must be free. Python runs inside Docker, so there's nothing else to install.

1. Clone the repository:

   ```bash
   git clone https://github.com/SamStuckey/chat-bot-example.git
   ```

   ```bash
   cd chat-bot-example
   ```

2. Copy the configuration template:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set `OPENAI_API_KEY` and `PENNY_CACHE_KEY_SECRET`. The
   secret can be any long random string; `openssl rand -hex 32` makes one.
   `.env` is ignored by git.

3. Build and start everything:

   ```bash
   docker compose up --build -d
   ```

   The first build takes a few minutes. A setup step creates signing keys,
   prepares the database, loads the sample data and publishes the content.
   Run `docker compose ps` and wait for `penny` to show `(healthy)`.

4. Open [localhost:8000](http://localhost:8000/), pick a user and start
   chatting. Traces are at [localhost:16686](http://localhost:16686/).

The [walk-throughs](docs/walk-throughs.md) go from a chat message to its trace
and the rows it saved. [How to use Penny](docs/how-to-use.md) covers the demo
users, Jaeger, everyday commands, troubleshooting, tests and evals.

## Configuration

Settings come from `PENNY_*` environment variables in `.env`; run
`docker compose up -d` after changing them. The ones you're most likely to
touch are `PENNY_CHAT_MODEL`, `PENNY_COMPACTION_MODEL` and
`PENNY_HISTORY_BUDGET_TOKENS`. [config.py](src/penny/config.py) lists every
setting with its default.

## Layout

```text
src/penny/          the service: API routes, agent and tools, context management, domain modules
src/content_bundle/  the content table, shared by the service and ingestion
src/ingestion/       publishes the documents listed in content/manifest.toml
content/             persona, scope, safety policies, program knowledge, summary template
alembic/             schema migration
scripts/             setup, sample data, OpenAPI export
tests/               tests, mirroring src/
evals/               real-model evals
docs/                the documents below
```

## Documentation

- [Features](docs/features.md): what Penny does.
- [Architecture](docs/architecture.md): how it's built, the design choices and their costs, and the API.
- [Diagrams](docs/diagrams/): the [system overview](docs/diagrams/system-overview.md), [the agent loop](docs/diagrams/agent-loop.md), and [content updates](docs/diagrams/content-updates.md).
- [How to use Penny](docs/how-to-use.md): the demo, Jaeger, commands, tests and evals.
- [Walk-throughs](docs/walk-throughs.md): guided examples from chat to traces and SQL.
- [Developer reference](docs/development.md): containers, sample data, database access, dependencies.
- [Code standards](docs/code-standards.md): the conventions the code follows.
- [Privacy](docs/privacy.md): what's stored, what's sent to the model provider, and what stays out of logs.
- [Known limitations](docs/known-limitations.md): gaps, and what a production version would need.
