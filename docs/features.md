# Features

What Penny does, grouped by area. [Architecture](architecture.md) explains
how and why it's built this way, and [Known limitations](known-limitations.md)
covers the gaps.

## Products, offers and referrals

- **Product suggestions.** Penny asks a clarifying question when it needs
  one, then suggests catalog products using what the user said, their
  purchase history and their saved guidance. Preferences carry across turns.
- **Catalog and purchase lookups.** Search by words in a product's name,
  category or description, browse the whole catalog, or list the user's own
  purchases, newest first.
- **Popular products.** Rankings of what families at the user's school buy,
  falling back to all users when no school is linked. This gives Penny
  somewhere to start with a new user.
- **Bonus Pennies offers.** The promotions running right now, soonest-ending
  first.
- **Cards.** Products appear as cards with an image, name and price; offers
  appear as cards with an image, title and description. Every field comes
  from the database. Penny presents products only through cards, never by
  naming them in text.
- **Referral help.** Penny explains the program's rules and steps, asks what
  went wrong when a referral didn't work, and fetches the user's own referral
  code. A user with no code is told so rather than given an invented one.
- **App help and handoff.** Penny answers questions about how the app works
  from its product-knowledge document. When it doesn't know, it says so and
  points the user to Greenpenny support.
- **Totals and paging.** List lookups return a total and a cursor, so Penny
  can say "showing 10 of 18" and fetch the next page when asked.

## Conversation and streaming

- **One continuous conversation per user,** kept in the database and loaded
  page by page, newest first.
- **Streaming replies.** Text and cards arrive as NDJSON events while the
  reply is written.
- **A fixed greeting** of two short bubbles, shown each time the chat opens
  and kept out of the history.
- **Stop.** The send button becomes a Stop button while a reply streams.
  Stopping keeps the partial reply and anything a tool already did, and the
  next message picks up from there.
- **Disconnect-safe.** Closing the page doesn't cancel a reply. It finishes,
  saves, and shows up when history reloads.
- **One reply at a time.** Each user can have one running turn; different
  users run concurrently.
- **Idempotent sends.** A retried send with the same key never starts a second
  reply. If the original has finished, it's replayed from storage.
- **Feedback.** Thumbs up or down on any assistant message, with an optional
  comment through the API. Ratings are stored for review and don't change
  Penny's behavior.
- **Local time.** Each request tells the model the user's local time, and
  dates in a message are read in the user's own time zone.
- **Demo client.** A plain-JavaScript page renders streamed text and card
  carousels, shows saved history, and lets you switch between sample users.
  It escapes HTML and renders only a small Markdown subset.

## Staying on topic and safe

- **Scope and voice.** A scope charter says what Penny helps with and what
  it declines. A persona document sets the voice: friendly, brief, English
  only, written in short paragraphs for a phone screen.
- **Do-no-harm policies.** An always-loaded safety core tells the model when
  to read one of five detailed policies: allergens and food safety, dietary
  and medical claims, child safety, product misuse, and crisis or distress.
  The model reads them with `read_document`.
- **No safety promises.** The catalog has no ingredient, allergen or
  nutrition data, so Penny never says a product is safe for an allergy or a
  condition and asks the user to check the label.
- **Enforced tool boundaries.** Strict input schemas, identity from the
  verified token, a per-turn tool-call limit and a result-size cap apply to
  every tool call. Product cards refuse unknown or avoided products, and
  promotion cards also refuse inactive offers.

## Saved guidance and the avoid list

- **Guidance notes.** When the user asks Penny to remember something, it
  saves a short note, and can update or remove it later. A note can expire on
  a given day. Active notes go to the model with each request as user data.
- **Avoid list.** The user can name products they never want suggested.
  They're filtered out of every catalog query and refused by card checks. The
  user can review the list and take products off it. If a name matches more
  than one product, nothing changes and Penny asks which one was meant.
- **Writes are immediate and disclosed.** Penny saves right away and tells
  the user what changed. Note length, note count and avoid-list size each
  have a configured limit.

## Context management and recall

- **Separate transcript and model history.** What the user saw is never
  rewritten; only the model's working view changes.
- **Request-only context.** Account details and local time are added to each
  model request without being saved into history.
- **Tool-result clearing.** Past a token threshold, old tool results are
  replaced with a placeholder while the calls stay visible.
- **Summaries.** When clearing isn't enough, a separate, cheaper model
  summarizes older history using a template with required headings, checked
  before the summary is used. The chat model defaults to `gpt-6.1-terra` and
  the summarizer to `gpt-6-luna`, at about a tenth of the input price in the
  configured estimates.
- **Saved summaries.** Each summary is stored with the point it covers, so
  later turns reload the same context. The visible transcript is untouched.
- **History search.** A user-scoped full-text search finds earlier messages
  by words, a range of the user's local calendar days, or both, and returns
  short snippets.
- **Prompt caching.** Fixed instructions come first in every request, and an
  opaque per-user key lets the provider cache them.

## Content publishing

- **Markdown sources and a manifest.** Persona, scope, safety policies,
  program knowledge, the greeting and the summary template are Markdown
  files. Only files listed in the manifest are published.
- **Versioned publishing.** Ingestion strips authoring comments, normalizes
  whitespace and hashes each body. Changed documents get a new row, removed
  ones are deactivated, and unchanged ones are left alone, all in one
  transaction. Published bodies are never edited.
- **Changes apply between turns.** The next turn reads the new set; a turn
  already running keeps its snapshot to the end.
- **Program knowledge.** Three short documents cover Greenpenny's referral
  rules, a referral FAQ, and how the app works: Pennies, linking a school,
  scanning receipts, Bonus Pennies and reaching support.

## Identity and isolation

- **Token verification on every request.** RS256 signatures checked against a
  public key, with expiry, issuer, audience and subject required, and the user
  confirmed to exist.
- **Everything scoped to the token's user.** Transcripts, saved guidance, the
  referral code, feedback and history search all filter by the verified user
  ID. No tool takes a user ID, so the model can't ask for someone else's data.
  Stop and feedback check ownership too.
- **Demo sign-in.** Picking a user on the demo page issues a signed token with
  no password. From then on, requests go through the normal verification.

## Observability and checks

- **Traces.** OpenTelemetry spans for each turn, model request and tool call,
  with timing, time to first token, token usage, estimated cost, outcome and
  compaction events, viewable in a local Jaeger. Message content capture is
  off.
- **Tool audit.** Every tool call is saved with its outcome, latency and
  arguments, with free-text arguments replaced by their length.
- **No provider storage.** Chat and summary requests both opt out of OpenAI
  response storage.
- **Tests.** Scripted models stand in for the provider, so the suite needs no
  network. It covers user isolation, streaming, Stop and continuation,
  idempotency, publishing, memory limits, compaction persistence and the API
  schema.
- **Lint and types.** Ruff for linting and formatting, Pyright in strict mode.
- **Real-model evals.** One checks that the right safety policy is read for
  eight prompts; the other uses an LLM judge on three answers. Both run on a
  temporary copy of the database and fail on any failed case.

## Local setup

- **Docker Compose** runs the app and Jaeger, with SQLite on a named volume.
- **Automatic setup.** Before the app starts, a setup service creates signing
  keys, creates the database, runs the migration, adds sample data and
  publishes the content. It's safe to run again.
- **Generated sample data.** Eight schools, 39 households with distinct
  shopping habits, 70 products with images, about six months of purchase
  history with seasonal patterns, and a mix of running, ended and upcoming
  offers. The [developer reference](development.md#sample-data) describes it.
- **Development image.** Tests, lint, type checks and evals run in their own
  image. Commands are in [How to use Penny](how-to-use.md#tests-and-evals).
