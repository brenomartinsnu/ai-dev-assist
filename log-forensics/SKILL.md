---
name: log-forensics
description: >-
  Investigate a production incident/bug across Nubank services by correlating
  Databricks (`etl.<country>__contract`), Alexandria/Grafana logs (`nu.logs.k8s`),
  and Datomic. Use when the user asks to "investigate" a ticket/incident, trace
  an entity (card, customer, transaction) end-to-end through multiple services,
  find where a silent data-correctness bug happened (no error/deadletter), or
  needs the exact `nu databricks sql` / `nu alexandria search` syntax and its
  gotchas. Distilled from the CSEO-6946 investigation (cards embossed with a
  missing/zero CVV).
---

# Log Forensics — Databricks + Alexandria/Grafana + Datomic

Methodology for tracing one entity (a card, a customer, a transaction) through
several Nubank services when something went wrong silently — no exception, no
deadletter, no alert — and you need to reconstruct what actually happened from
logs and tables.

## The core technique: trace-id correlation, not time-window guessing

**Don't** try to find a request by guessing a narrow time window (`time BETWEEN
X AND X+1s`) and searching by entity id alone. Two reasons:
1. Narrow time-window queries against `nu.logs.k8s` are **unreliable from the
   CLI** — they can silently return 0 rows, or hang for 10+ minutes, even when
   the same query with a wider window or via Grafana Explore returns instantly.
   This produced multiple false "X was never called" conclusions in the
   CSEO-6946 investigation that later turned out to be tooling artifacts, not
   real absence.
2. A service's outbound calls to *other* services often don't carry the entity
   id in the URL (e.g. a POST body has the id, not the URL) — so an id-based
   `LIKE` filter misses them even when the call really happened.

**Do** this instead:

1. Find ONE log line that ties your entity id (card-id, customer-id) to a
   **trace-id**. The easiest anchor is usually an outbound GET call whose URL
   embeds the id (e.g. `.../api/customers/<id>/personalization-data`):
   ```sql
   SELECT date, time, log_type, cid, log
   FROM nu.logs.k8s
   WHERE country = 'br'
     AND date IN (DATE '<d1>', DATE '<d2>')
     AND service = '<service-that-calls-out-with-the-id-in-the-url>'
     AND log LIKE '%<entity-id>%'
   ORDER BY time
   ```
2. Pull `data.trace-id` out of any matching line.
3. Re-query across **every service you care about** filtering on that
   `trace-id` (it propagates through the whole call chain, service to service):
   ```sql
   SELECT date, time, service, log_type, cid, log
   FROM nu.logs.k8s
   WHERE country = 'br'
     AND date IN (DATE '<d1>', DATE '<d2>')
     AND service IN ('<service-a>', '<service-b>', '<service-c>')
     AND log LIKE '%<trace-id>%'
   ORDER BY time
   ```
   This single query reconstructs the entire request: every out-request/
   out-response, every downstream service's in-request/in-response, and the
   Istio `access-log` lines (which carry `response_code`/`duration` even for
   the raw envoy hop).
4. **Batch multiple entities in one query** with `OR log LIKE '%<id>%' ...` —
   cheaper than one query per id, and lets you eyeball whether N different
   entities show the *same* pattern (control vs. affected) side by side.

### Reading the result

- `in-request`/`in-response` (logger `common-io.interceptors.logging`) — what
  a service received and returned, with `path`, `status`, `timing-ms`.
- `out-request`/`out-response` (logger `common-http-client.components.http`) —
  what that service called downstream, with `url`, `endpoint`, `status`.
- `access-log` (logger `istio`) — the mesh-level envoy record; has
  `response_code`, `duration`, `path` even when the app-level log is thin.
- **A `status: 200` at every hop does not mean the data was correct** — HTTP
  success only proves no exception was thrown. A field can be `nil`/empty
  inside a 200 body and never show up in any log (bodies are not logged,
  correctly, for PCI/PII reasons). If every hop is 200 and the bug still
  reproduces, the defect is silent-data-loss inside a "successful" call —
  see the debug pattern below.

## `nu alexandria search` — syntax and gotchas

Schema of `nu.logs.k8s`: `time` (timestamp), `log` (raw JSON string), `level`,
`logger`, `log_type`, `host`, `cid`, `metadata`, `env`, `country`, `account`,
`stack_id`, `prototype`, `service`, `date`, `alexandria_idx`.

```bash
cat <<'EOF' > /tmp/q.sql
SELECT date, time, log_type, cid, log
FROM nu.logs.k8s
WHERE country = 'br'
  AND date = DATE '2026-08-10'
  AND service = 'peter-pan'
  AND log_type = 'hsm-response-code'
  AND json_extract_scalar(log, '$.data.command') = 'CW'
  AND time BETWEEN TIMESTAMP '2026-08-10 10:46:00' AND TIMESTAMP '2026-08-10 10:47:00'
ORDER BY time
LIMIT 200
EOF
nu alexandria search --country br --env prod /tmp/q.sql
```

Gotchas, in order of how often they bite:

- **Use `TIMESTAMP '...'` / `DATE '...'` literals, not `TIMESTAMP('...')` /
  `DATE('...')` function calls.** The engine (Trino) rejects the function
  form with `Function 'timestamp' not registered`.
- **Extract JSON fields with `json_extract_scalar(log, '$.data.<field>')`**,
  not `json_value(log, 'lax $.data.<field>')` (that's a Grafana-dashboard-only
  dialect quirk seen in some older saved queries — `json_extract_scalar` is
  the one that works from `nu alexandria search`).
- **Run the command via `Bash` with `run_in_background: true`**, not inline —
  these queries commonly take 30s–2min+, and a couple of them hung for 10+
  minutes in this investigation before returning a real (non-empty) result.
  Poll with `Monitor` (`until ! pgrep -f "...sql" ...`), never assume a fast
  empty result is a true negative.
- **A 0-row result from a narrow time window is not trustworthy on its own.**
  Before concluding "X never happened", either (a) widen the window and
  confirm the base rate of that log line elsewhere, or (b) switch to
  trace-id/customer-id correlation (above) instead of a time guess. In this
  investigation, an apparent "peter-pan was never called" from a narrow
  window turned out to be false — the same query, run manually through
  **Grafana Explore** (the UI backing Alexandria) instead of the CLI wrapper,
  came back with the real data in seconds. **When the CLI tool is slow or
  returns a suspicious empty result, hand the exact SQL to the user and ask
  them to run it in Grafana Explore directly** — it's frequently faster and
  more reliable than the `nu alexandria search` wrapper.
- Don't combine a UUID `LIKE` filter with a `time BETWEEN` range in the same
  query if you can avoid it — this combination has been observed to time out
  even over narrow (150–250ms) windows. Prefer exact-match filters
  (`service = '...'`, `log_type = '...'`) plus the `LIKE`, and scan the
  (small) result set by eye instead of narrowing further with time.
- `--cid` on `nu-<country> ser curl` is for *your own* correlation id when
  making a live call, not a filter for past logs.

## `nu databricks sql` — card/entity tracing recipes

Auth: `nu aws credentials refresh --aws-accounts br` (or your country) if you
get `403`/`400 Bad Request` on `HeadObject`-style errors — that's almost always
an expired AWS token, not a real permissions problem. Databricks itself needs
`databricks auth login --profile <profile>` (interactive browser OAuth — ask
the user to run this themselves, don't attempt it for them).

```bash
nu databricks sql "SELECT ..." --profile <your-databricks-profile>
```

### Card → PAN-mapping → embossing-file join (BR example)

```sql
-- 1. Resolve the card + customer + shard
SELECT card__id, customer__id, card__product_type, card__created_at, prototype
FROM etl.br__contract.crebito__cards
WHERE lower(card__id) IN ('<card-id-1>', '<card-id-2>', ...)

-- 2. Card → embossing request → embossing file
SELECT er.embossing_request__id, er.embossing_request__created_at,
       ef.embossing_file__filename, ef.embossing_file__embosser, ef.embossing_file__sent_at,
       ef.embossing_file__pre_processed_s_3_path, ef.embossing_file__post_processed_s_3_path
FROM etl.br__contract.balrog__embossing_requests er
LATERAL VIEW explode(er.embossing_request__cards) c AS card_id
JOIN etl.br__contract.balrog__embossing_files ef ON ef.embossing_file__id = er.embossing_file__id
WHERE lower(card_id) IN ('<card-id-1>', '<card-id-2>', ...)

-- 3. Card's features (credit/debit) — note: pan__id in this table is NULL by
--    design for essentially every card; do not treat a null here as a signal.
SELECT card__id, feature__type, feature__status, pan__id
FROM etl.br__contract.crebito__features
WHERE card__id = '<card-id>'
```

Known schema quirks (worth re-checking, don't assume they're still exactly
this in a future session):
- `embossing_request__cards` is an `ARRAY` — use `LATERAL VIEW explode(...)`
  or `SIZE(...)` for counts, never compare it to a scalar directly.
- `balrog__embossing_files.embossing_file__source_id` is the batch UUID, NOT
  the filename UUID inside `NUBANK_..._<uuid>.TXT` — don't join on it expecting
  filename correlation.
- Join `balrog__embossing_requests` to `balrog__embossing_files` on
  `embossing_file__id`, not by filename.

### Reading a raw embossing file (PCI — read this before touching S3)

- Bucket: `s3://nu-balrog-<country>/`. Needs an S3 bucket-level grant, which is
  **separate from application scopes** (`cards-admin`, `pci-pan`, etc. do not
  grant S3 read) — this is an AWS IAM/bucket-policy request, not an
  `nu sec scope add`. Don't assume one covers the other.
- `.pre.TXT` = JSON-lines internal representation. `.post.TXT` = positional,
  embosser-specific layout — this is the one that matches what was actually
  sent to the factory; parse it with that country/embosser's codec
  (`balrog/src/balrog/<country>/<embosser>/embossing_file_codec.clj` in the
  `balrog` repo defines exact byte offsets per field).
- **Never print PAN / CVV / tracks / pinblock to the terminal or into chat.**
  Extract only the field(s) you need programmatically, and delete the local
  file immediately after. A raw PAN was accidentally echoed once during this
  investigation via a pretty-printed `curl -f` JSON response (the `-f` flag
  adds coloring that also breaks `json.load` — drop `-f` when piping to a
  script, and redact before printing either way).

### Gilfoyle — PAN-mapping lookup (needs `pci-pan` scope)

```bash
nu-br ser curl get <shard> gilfoyle /api/admin/card/<card-id>/get-pan-clear --cid <cid> --env prod
```
Returns `[{pan_clear, shard, card_id, customer_id}]` — **redact `pan_clear`
before showing it to anyone**; it's the only field here that's a real secret
(a card missing an `application` tag on a single PAN entry is *normal* for a
`:combo` profile card, not a bug signal by itself).

## Debug pattern: "silent field loss, no deadletter"

If a report says a field (CVV, braille, a name) is correct in one system's
source of truth but wrong/missing in the final artifact, and there is no
deadletter, no error log, no controlinho — assume the loss happened inside a
"successful" (200) response, in application code that doesn't null-check an
optional/defaulted field:

1. Trace the full request end-to-end (technique above). Confirm every hop is
   really 200 with no errors — if so, stop looking for infra/HSM/network
   causes and start reading the adapter code that builds each hop's response.
2. Look specifically for asymmetric use of `assoc-some` (only-if-non-nil) vs.
   plain `assoc`/hash-map literal on fields in the same response-building
   function — a required field built with plain `assoc` right next to
   optional fields built with `assoc-some` is the single highest-signal code
   smell for this bug class. It means "this field is trusted to never be nil"
   — which is exactly the assumption that silently breaks.
3. Check whether the owning service enables Prismatic/`schema.core`
   `s/with-fn-validation` in production — most Clojure services here declare
   `:required true` schemas on `s/defn` but do **not** enforce them at
   runtime (only in tests), so a `nil` sailing through a "required" field is
   often possible even though the schema says otherwise.
4. Also check deploy-time **config** (not just app code) for the service one
   hop upstream of where the symptom surfaces — e.g. Rivendell's real
   production personalization config lives on a separate `config` git branch
   (`src/prod/rivendell_<country>_config.json`), not `main`. A missing entry
   for a specific product-type/plastic there silently strips a field with the
   exact same "no error anywhere" signature. `git log origin/config -- <path>`
   to see if it changed recently.

## Real example queries from this investigation (CSEO-6946)

Kept here as copy-paste-ready references, not because the specific ids matter:

```sql
-- HSM return-code for a specific command, across several cards' windows
SELECT date, time, cid, log
FROM nu.logs.k8s
WHERE country = 'br'
  AND date IN (DATE '2026-08-10', DATE '2026-08-11')
  AND service = 'peter-pan'
  AND log_type = 'hsm-response-code'
  AND json_extract_scalar(log, '$.data.command') = 'CW'
  AND json_extract_scalar(log, '$.data.return-code') != '00'
  AND (time BETWEEN TIMESTAMP '2026-08-10 10:40:00' AND TIMESTAMP '2026-08-10 12:15:00'
       OR time BETWEEN TIMESTAMP '2026-08-11 15:00:00' AND TIMESTAMP '2026-08-11 16:20:00')
ORDER BY time

-- Batched trace-id correlation across 8 entities at once
SELECT date, time, service, log_type, cid, log
FROM nu.logs.k8s
WHERE country = 'br'
  AND date IN (DATE '2026-08-10', DATE '2026-08-11')
  AND service IN ('rivendell', 'peter-pan')
  AND (log LIKE '%<trace-id-1>%' OR log LIKE '%<trace-id-2>%' OR ... )
ORDER BY time
```

$ARGUMENTS
