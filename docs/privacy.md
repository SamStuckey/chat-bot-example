# Privacy

What Penny stores, what it sends to the model provider, what it keeps out of
logs and traces, what users can remove, and what a production deployment
would still need. Some of it repeats [Features](features.md) and
[Known limitations](known-limitations.md) so this page stands on its own.

## Principles

1. **The token decides whose data it is.** The user ID comes only from the
   verified token. Every query for user data filters by it in the data layer,
   and no tool takes a user ID, so the model can't ask for someone else's
   data. Tests check cross-account isolation across the endpoints, the
   user-data services and the tools.
2. **Send the model only what the turn needs.** Account details go into each
   request but are never written into the conversation history or summaries.
3. **Keep content out of operational data.** Traces, logs and the tool audit
   record IDs, counts and timings, not what people wrote.
4. **Say what removal does and doesn't do.** Removing a saved note deletes the
   note, not every place the same words appear.

## What Penny stores

Everything lives in one SQLite database in the `penny-data` Docker volume.

### Data Penny reads from the app's tables

| Data | Used for |
|---|---|
| User name, linked school, time zone | The account context sent with each request, and local dates |
| Purchase history | The `get_my_purchases` tool, and school-level popularity counts |
| Products | Catalog lookups and cards |

Penny doesn't use the user's email, and never sends it to the model.

### Data Penny writes

| Table | Holds | Notes |
|---|---|---|
| `messages`, `messages_fts` | The conversation as the user saw it: their messages, Penny's text and cards. The search index holds the text only. | Append-only. |
| `model_messages` | The model's history: prompts, replies, tool calls with their arguments and results. | Append-only. Tool results can include purchases, the referral code and history-search snippets. |
| `summaries` | Compaction summaries of older history, written by the compaction model. | One row per compaction; older rows are kept. |
| `guidance_notes` | What the user asked Penny to remember. | Can hold sensitive details, such as an allergy, because users choose what to save. Removal deletes the row. |
| `avoided_products` | Products the user asked not to see. | Removal deletes the row. |
| `message_feedback` | Thumbs up or down, and an optional comment. | One per message; a new rating replaces the old one. |
| `tool_calls` | The audit of every tool call: tool, status, latency, arguments. | Free-text arguments (`text`, `query`, `product_name`) are replaced by their length. IDs, dates and policy names are kept. |
| `turns` | Each turn's status, timings, model, content version and app version. | Stores a SHA-256 hash of the message text (to detect a reused idempotency key), not the text. |

Nothing is deleted on a schedule. There is no retention period.

### Data about other people

Users mention other people: a friend they're referring, a child's allergy.
That text is stored and scoped like any other message, under the user who
wrote it. Penny doesn't detect or treat it differently.

## What goes to OpenAI

Each chat-model request carries:

| Part | Contents |
|---|---|
| Instructions | Penny's persona, scope, safety core and knowledge documents. No user data. |
| Tool definitions | Fixed; no user data. |
| Account context | Name, linked school, saved guidance notes with their dates. |
| Turn context | The user's local time. |
| History | The latest summary and the messages after it, including tool calls and results. |

The compaction model receives the older history it's summarizing, with the
summary template.

Not sent: the internal user ID, email, or any other user's data. Popularity
rankings are aggregate counts with no names.

Request settings:

- **`store: false`** on every request, the summarizer's included, so OpenAI
  doesn't keep response state for later retrieval. Penny owns the
  conversation state.
- **The prompt cache key** is an HMAC-SHA256 of the user ID with a secret, so
  provider-side caching is separated per user without revealing who they
  are.
- **No provider-side conversation state** or truncation. Penny sends what it
  decided to send.
- OpenAI's own data-retention policy for API traffic still applies, separately
  from `store: false`. A deployment would need to confirm the account's
  terms, such as zero data retention.

## What stays out of logs, traces and the audit

- **Traces** (Jaeger) record the turn ID, the opaque user key, the model,
  content version, token counts, estimated cost, timings, tool names, status,
  and clearing and compaction events. The agent's instrumentation runs with
  message content capture off, so prompts, replies, tool arguments and tool
  results never reach a span. A test checks that a message's text appears in
  no span.
- **Failures** are recorded by category (`context_limit`, `model_api_error`,
  `timeout`, …) and the provider's error code. The provider's error message,
  which can echo the request, is never logged or traced.
- **Database errors** exclude bound values, so a logged SQL error can't carry
  a message's text.
- **Logs** are for startup and errors.
- Jaeger keeps traces in memory only; they're gone when it restarts.

## What users can remove

| Action | What changes | What stays |
|---|---|---|
| Remove a saved note | The note is deleted | The conversation where it was said, the model history, summaries, the search index |
| Take a product off the avoid list | The row is deleted | The same |
| Stop a reply | Generation stops | The partial reply, and any change a tool already made |

Penny says so when removing a note ("I removed that from your saved
guidance"), but there's no way yet to erase a conversation, redact part of
it, or export a user's data.

## Safety-related data

- A saved note can hold health information. Penny uses it to personalize
  replies but never as a safety guarantee: the catalog has no ingredient or
  allergen data, and the instructions and policies say so.
- Text from users, saved notes, summaries and history-search results is
  labelled as data, not instructions, when it reaches the model. Summaries
  record requests as reported speech ("The user asked Penny to…"), so a
  stored request can't later act as an instruction.

## The demo

- The demo sign-in lets anyone who can open the page act as any listed user,
  without a password. It stands in for a real identity service and must not
  ship.
- Compose publishes the app (port 8000) and the trace viewer (port 16686) on
  the host. Anyone on the network who can reach them can use the demo.
- Signing keys are generated locally into the data volume.
- All the data is generated: the people, schools, products and purchases are fictional.

## What production would need

1. **Retention and deletion:** a retention period, and deletion or redaction
   that reaches every copy: the transcript, model history, summaries, the
   search index, the tool audit, backups and the provider.
2. **User rights:** access and export, and targeted forgetting ("forget what I
   told you about my brother").
3. **Notice and consent:** telling users what the assistant stores and sends
   to a model provider.
4. **Audience rules:** children using a parent's account, and regional
   requirements.
5. **Provider terms:** a data processing agreement and confirmed retention
   settings with the model provider.
6. **Access control:** for the database, backups and the trace viewer, and
   encryption at rest.
7. **Aggregate thresholds:** a minimum number of buyers before school-level
   popularity is shown, so a small school can't reveal one family's
   purchases.
8. **Data minimization review:** whether every field in the account context
   and tool results needs to reach the model.

See [Known limitations](known-limitations.md) §1, §5 and §9 for the related
gaps.
