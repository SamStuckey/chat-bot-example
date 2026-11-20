# Known limitations

Penny runs locally against sample data. This page lists what it doesn't do,
or doesn't do well yet, grouped by practical effect, with what a production
version would need for each. [Features](features.md) describes what is
implemented.

## 1. Demo identity and deployment boundaries

JWT verification is implemented, but login and registration are not integrated
with a real identity service. The demo sign-in allows selecting any listed
account and obtaining a token without credentials. Signing keys are generated
locally, and Compose publishes the app and trace-viewer ports on the host.
Access to the demo can therefore grant access to demo accounts and consume
the configured model API quota.

A real deployment would swap the demo sign-in for that identity service,
establish key rotation and token-revocation requirements, and configure network
access, TLS, secrets, and trace-viewer access for the intended environment.

## 2. One application instance and local storage

SQLite, background turn tasks, response queues, and Stop cancellation tokens
all assume a single instance. Tasks and cancellation state live in the
application process. Multiple workers would not automatically share them,
and SQLite write contention limits scale.

A process failure can lose an in-progress reply. Startup marks abandoned turns
as errors; it does not resume their generation. Saved replies can be replayed,
but there is no durable event stream for resuming an interrupted live stream.

Penny also keeps the app's own data, the users, schools, products and
purchases, in its database and queries those tables directly. In a real
system that data belongs to the app, and the user's time zone in particular
has no way to be set through Penny's API; it's assumed to come from the app's
account data.

For a real service, choose storage and execution ownership around the
expected traffic and reliability needs. Compare reading app data through the
app's APIs or read-only views with sharing the app's database under clear
table ownership. Multiple instances would need
coordinated turn ownership, cancellation, and recovery, alongside a database
migration plan that accounts for SQLite-specific history search.

## 3. Policy adherence and free-text claims depend on the model

The main agent decides when to read a detailed safety policy and how to apply
it. There is no independent policy-routing model or runtime answer-review
stage. The agent may miss an indirect safety concern, misunderstand a follow-up,
or produce a claim that conflicts with its instructions. Separating untrusted
user data from instructions reduces exposure but does not guarantee resistance
to prompt injection or hallucination.

The catalog has no ingredient, allergen, or nutrition data. It cannot establish
that a product is safe for an allergy or medically suitable. The assistant is
instructed to disclose this and avoid making those promises.

Real deployment would require broader adversarial and multi-turn evaluations,
reviewed policies, and evidence for whether extra routing or output checks
improve safety enough to justify their latency and cost. New health-related
capabilities would also require appropriate authoritative product data.

## 4. Card contents are validated, but lookup provenance is not

Cards use database records, and the server rejects unknown IDs, avoided
products, and inactive promotions. However, it does not verify that a requested
ID came from a lookup the agent actually performed. A guessed but valid ID can
still produce a card. Free-text claims, card headings, and compliance with the
instruction to present products only through cards are not independently
verified against lookup results.

The next step would be server-issued references to user-scoped lookup results,
resolved and revalidated when displaying a card, together with a deliberate
policy for validating generated claims.

## 5. Search and recommendation relevance are basic

Catalog search, and naming a product to add to or remove from the avoid list,
use literal, case-insensitive substring matching. There is no synonym
expansion, typo tolerance, embeddings, or semantic retrieval. History
search uses words and dates and searches text only; cards are not searchable.
Suggestions can use purchases, saved guidance, and popularity, but there is no
trained recommendation system or automatic interest profile.

Popularity counts purchase records. School-level aggregation has no minimum
distinct-buyer threshold, so with real data a small cohort could reveal
household buying patterns even without returning names.

Improve retrieval and recommendations against representative queries and
feedback before choosing a more complex search system. Real purchase rankings
would need cohort-size rules and a broader fallback for sparse groups. **Semantic
product matching would likely be a must for this to be useful in production, for
recommending, preference matching, and safety alike.**

## 6. Memory is explicit, limited, and potentially lossy

Durable guidance is saved through explicit tool calls. Preferences mentioned
only in conversation can be lost or distorted through summarization. Conflicts
between guidance notes are not semantically reconciled; the model is instructed
to prefer newer notes. The persona's suggestion that it learns a user's habits
is broader than the implemented explicit-memory behavior.

Pagination cursors live in model context rather than persistent lookup state.
Clearing or summarization can lose the cursor needed for “show me more.” A
user has one continuous conversation, with no separate chat sessions or
New Chat workflow.

A richer profile system would need user-visible review, correction, and
removal of inferred preferences. Persistent lookup state and explicit chat
boundaries should be added when their user value warrants the extra state.

## 7. Compaction has quality, latency, and integration risks

Compaction uses an experimental, exactly pinned Harness integration. Persistence
depends on its summary marker and message layout. Required-heading validation
checks structure, not whether the summary preserves every important fact.
Compaction runs inline and can add latency to the turn that triggers it.

The history budget and thresholds are configurable defaults rather than
values calibrated against a representative workload. There is no pre-send
token estimator, automatic recovery from a provider context-limit rejection,
or provider-side truncation fallback. A failed summary or rejected request
can fail the turn.

Before deployment, measure recall and latency, validate upgrades against the
persistence contract, and decide whether to retain the integration or use a
more stable compaction mechanism. Any recovery strategy must preserve tool
exchanges and avoid repeating completed actions.

## 8. Business knowledge and catalog data are sample inputs

The business documents (the referral rules, the referral FAQ and the app
help) are short Markdown files written for a fictional program. Real source
documents tend to be longer, older and less consistent: a FAQ and a rules
page that disagree, or example amounts that read like promises. Penny has no
way to notice that; it repeats whatever was published.

Publishing validates manifest structure and normalizes text, but it does not
check factual accuracy, contradictions, sensitive content, or missing source
material. There is no administrator editor, approval workflow, automated
document conversion, or passage-level retrieval. Documents are loaded whole. That
matters for security as well as accuracy: documents loaded as instructions
are effectively part of the prompt, so whoever can publish them controls
Penny's behavior. Products,
promotions, purchases, and images are generated sample data rather than live
integrations, and the seeded promotions expire within two months of setup.

A real integration would establish authoritative sources and ownership,
connect live application data, and introduce reviewed publishing with previews
and rollback. Passage retrieval becomes relevant if approved documents grow
beyond the current short source set.

## 9. Removing guidance is not comprehensive data erasure

Removing a guidance note or avoided product deletes that saved record. It
does not erase the original conversation, model history, search index, or
summaries that may contain the same information. Stopping a reply also retains
its partial output and does not undo completed tool actions.

Penny has no complete retention, export, or targeted-redaction workflow.
Messages and model context persist locally, and relevant context is sent to
the model provider. Disabling trace content and opting out of response storage
do not replace a full privacy and data-retention design.

For real user data, define these behaviors explicitly and propagate deletion
or redaction through every stored representation, backups, and applicable
provider handling.

## 10. Writes disclose their result without an approval step

Current action tools change only saved guidance and avoided products. They
execute immediately and return the outcome for the assistant to disclose;
there is no user-confirmation step. The assistant cannot apply referral codes,
change accounts, make payments, or issue refunds. Support handoff is guidance
in a reply, not an integrated support ticket or human-agent transfer.

Before adding business-changing tools, define confirmation according to impact
and reversibility, recheck eligibility at execution, and prevent duplicate
side effects on retries. Send-level idempotency alone is not a complete
transaction design for external actions.

## 11. Production operations and spending controls are incomplete

The app has per-turn timeouts, tool-call and result-size limits, bounded
provider retries, and database readiness checks. It has no application-level
traffic quotas, tenant spending caps, provider failover, production alerting,
or deployment pipeline. Only OpenAI is wired in. A database health check does
not establish that the model provider can answer requests. A tool result over
the size limit is refused rather than returned in slices; no current tool needs
more, but a tool reading files or web pages would.

Traces and the local viewer support investigation, but aggregate dashboards,
alert thresholds, sampling, retention, and retry visibility need deployment
design. Cost is an estimate: aggregate turn usage is priced at chat-model
rates even when a cheaper compaction model contributed tokens.

Integrate checks and releases with real deployment infrastructure, add access and
budget controls, and attribute usage per model before relying on the estimate
for billing or spending enforcement.

## 12. Evaluation and audience coverage are limited

Automated tests use scripted models to verify application behavior. Real-model
evals cover a small set of policy-selection cases and three answer-quality
rubrics. The judge is not calibrated against a human-labeled benchmark, and
passing these cases does not establish general answer correctness, safety, or
recall after compaction. Stored thumbs-up/down feedback is not an automatic
learning or evaluation loop.

The assistant is instructed to reply in English. Multilingual behavior,
age-specific account controls, and supported-region requirements have not been
developed as complete product capabilities. The browser client demonstrates
the API; there is no native mobile client.

Deployment readiness would require representative multi-turn datasets, human
review, retrieval and memory-recall evaluation, and explicit audience and
regional requirements. Quality claims should be tied to measured results.

## 13. Stored replies suit replay, not analysis

Each message is saved as an ordered JSON list of parts, with text and cards
exactly as the client received them. That makes replay and history simple,
but questions across conversations are awkward. "How many times was this
product recommended?" means opening every saved reply and inspecting each
card's items.

The tool audit offers a partial answer: `show_products` and `show_promotions`
calls keep their product and promotion IDs. But it records what the model asked
to show, including refused requests, so it is not a reliable count of what
users saw.

If recommendation analytics matter, record each card item shown as its own row
(user, turn, product or promotion, time), written in the same transaction as
the reply. The transcript format can stay as it is.

## 14. Duplicate-send protection depends on the client

Penny prevents a retried message from starting a second reply only if the
client sends the same `Idempotency-Key` for the retry. The contract assumes
the app creates one key per message the user meant to send and reuses it only
for retries of that message. A client that creates a new key for every attempt
can produce duplicate turns, and two intentional sends with identical text
need different keys.

Before relying on this with a real client, confirm the app can keep a key
across retries, including after an app restart. Compare it with alternatives
such as a client-generated message ID or a status lookup for an ambiguous
send.

## What comes next

In rough priority order, before putting real users on it:

1. Ingestion that reads the business's own source documents and flags
   contradictions, gaps and placeholder values for the content owner, since
   Penny's answers are only as good as those documents.
2. Semantic product search behind the existing search tool, measured against
   the current literal search.
3. Cards only for products the turn actually looked up.
4. Evals for facts surviving compaction, and a larger set of multi-turn and
   adversarial cases reviewed by people.
5. Per-user spending limits and a second model provider for failover.

Then, for production: a real identity service, a managed database with turn
ownership and Stop that work across instances, a content workflow with review
and rollback, retention and deletion that reach every stored copy, and
dashboards and alerts on the existing traces. Later still: a confirmation
step once tools can do things with consequences, richer memory the user can
review and correct, recommendations that learn from feedback, and languages
other than English.
