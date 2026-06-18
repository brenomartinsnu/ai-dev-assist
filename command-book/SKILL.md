---
name: command-book
description: >-
  Personal catalog of ready-to-run Nubank commands — nucli (`nu ...`), `ser curl`
  service calls, `kafka produce`, project setup, and observability queries. Use
  when the user asks "how do I <do X>", "what's the command / curl / nucli for
  <X>", or names a known recipe: produce a topic, create a customer, get/activate/
  create a card, refresh credentials, start a new nu-service, update Santa rules,
  or pull Alexandria logs. Recall the matching template, fill in the user's IDs,
  and hand back ONE ready-to-run command — do not execute it.
---

# Command Book

My personal catalog of commands I reuse but never remember verbatim.

Every recipe is written **template-first**: a single fenced block using
`<PLACEHOLDERS>`, followed by a concrete `Example`. This skill's job is
**recall & fill**, not execution.

## How to use this skill

1. **Match** the user's intent to a recipe below (search by keyword: card,
   topic, customer, creds, project, logs…).
2. **Fill** every `<PLACEHOLDER>` in the template from what the user gave you.
   If a *required* value is missing, ask for it — or leave the `<PLACEHOLDER>`
   in place and call it out explicitly. Never invent IDs. Use the `Example` only
   as a shape reference, never copy its literal ids/values.
3. **Output ONE ready-to-run command** in a copy-able code block.
4. **Do NOT run it.** Hand it to the user to execute. (If they explicitly say
   "run it", you may, but default to handing it over.)
5. **State your assumptions** in one line after the command — env, shard,
   account alias, and anything you defaulted.

### Placeholder legend

Every recipe draws its placeholders from this single table — keep them uniform.

| Placeholder | Meaning | Example value |
|---|---|---|
| `<ACCOUNT>` | Account alias prefix for nucli | `nu-mx` 🇲🇽 · `nu-br` 🇧🇷 · `nu-co` 🇨🇴 |
| `<ACCOUNT_ALIAS>` | Bare account alias (for `--account-alias`) | `br` · `mx` · `co` |
| `<SHARD>` | Shard for the service call | `s0` (sharded) · `global` (non-sharded) |
| `<SERVICE>` | Target service name | `crebito` · `kuchiyose` · `factorio` |
| `<METHOD>` | HTTP verb | `get` · `post` · `put` · `delete` |
| `<PATH>` | API route on the service | `/api/customers/<id>/all-cards` |
| `<ENV>` | Environment | `staging` (default); omit `--env` for prod |
| `<PROJECT_NAME>` | New nu-service name | `my-new-service` |
| `<CUSTOMER_ID>` | Customer UUID | from `factorio` create / customer record |
| `<CARD_ID>` | Card UUID | from the `all-cards` response |
| `<SAVINGS_ACCOUNT_ID>` | Savings account UUID | from the account record |
| `<CREDIT_ACCOUNT_ID>` | Credit account UUID | from the account record |
| `<CID>` | Correlation id (tracking) | any UUID; `$(uuidgen)` |
| `<LAST_FOUR>` | Last 4 digits of the physical card | `1234` |
| `<LIMIT>` | Credit limit-range max | `5000` |
| `<TOPIC>` | Kafka topic | `CARDS.FEATURE-CHANGED` |
| `<BODY_MESSAGE>` | JSON payload for the topic | the full message from a deadletter |
| `<UUID_TO_TRACE>` | Id to grep for in logs | the id you're following |

### Command grammar (for building variants not in the catalog)

- **Service call:** `<ACCOUNT> ser curl <METHOD> <SHARD> <SERVICE> <PATH> [--env <ENV>] [-f] [-d '<json>' | --data '<edn>' --content-type edn] [--cid <CID>]`
  - `-f` follows redirects / fails on error (keep it for reads).
  - `--env staging` targets staging; **omit `--env` for prod** (be careful).
  - JSON body → `-d '{...}'`. EDN body → `--data '{...}' --content-type edn`.
- **Kafka:** `<ACCOUNT> kafka produce <TOPIC> '<BODY_MESSAGE>' --content-type json --shard <SHARD>`
- **EDN gotcha:** UUIDs are tagged literals: `#uuid "..."`. Sets use `#{...}`.
  Single-quote the whole `--data '...'` so the inner `"..."` need no escaping.
  To auto-fill a generated `source-id`, prefix the command with
  `uuidgen | xargs -I__SID__` and write `#uuid "__SID__"` in the payload — xargs
  substitutes the marker even inside the single quotes (uppercase is fine for `#uuid`).

---

## Daily

### Refresh credentials
```bash
nu dev bd
```

### Refresh AWS credentials (when things break with 403 / expired creds)
```bash
nu aws credentials refresh
```
Alternative — web-console role for a specific account:
```bash
nu aws shared-role-credentials web-console --account-alias=<ACCOUNT_ALIAS>
```
_Example:_
```bash
nu aws shared-role-credentials web-console --account-alias=br
```

### Start a new project (nu-service + Datomic)
```bash
nu lein new nu-service <PROJECT_NAME> -- +datomic
```
_Example:_
```bash
nu lein new nu-service my-new-service -- +datomic
```

### Update Santa rules (when ITSec programs are blocked)
```bash
santactl sync
```

---

## Messaging & service calls

### Produce a Kafka topic
```bash
<ACCOUNT> kafka produce <TOPIC> '<BODY_MESSAGE>' --content-type json --shard <SHARD>
```
_Example:_
```bash
nu-mx kafka produce CARDS.FEATURE-CHANGED '<message copied from the deadletter>' --content-type json --shard s0
```

### Create a customer (factorio)
```bash
<ACCOUNT> ser curl POST <SHARD> factorio /api/customers -d '{"limit-range-max": <LIMIT>}' --env <ENV>
```
_Example:_
```bash
nu-mx ser curl POST global factorio /api/customers -d '{"limit-range-max": 5000}' --env staging
```
> `factorio` is non-sharded (`<SHARD>` = `global`). Returns the new `customer-id` — chain it into the card recipes below.

---

## Card management

### Get all cards for a customer
```bash
<ACCOUNT> ser curl get <SHARD> crebito /api/customers/<CUSTOMER_ID>/all-cards --env <ENV> -f
```
_Example:_
```bash
nu-mx ser curl get s0 crebito /api/customers/<CUSTOMER_ID>/all-cards --env staging -f
```

### Activate a card
```bash
<ACCOUNT> ser curl post <SHARD> crebito /api/cards/<CARD_ID>/activation --env <ENV> -f -d '{"last-four": "<LAST_FOUR>"}'
```
_Example:_
```bash
nu-mx ser curl post s0 crebito /api/cards/<CARD_ID>/activation --env staging -f -d '{"last-four": "1234"}'
```

### Create a card — Debit (gold)
> `uuidgen | xargs -I__SID__` auto-fills `source-id` at runtime — no need to pre-generate it.
```bash
uuidgen | xargs -I__SID__ \
  <ACCOUNT> ser curl post <SHARD> kuchiyose /api/admin/customers/<CUSTOMER_ID>/manual-card-request \
  --data '{:card-profile :debit-single :features-to-activate #{:debit} :savings-account-id #uuid "<SAVINGS_ACCOUNT_ID>" :product-type :gold-debit :virtual? true :source-type :primary-card :source-id #uuid "__SID__"}' \
  --content-type edn --env <ENV> --cid <CID>
```
_Example:_
```bash
uuidgen | xargs -I__SID__ \
  nu-mx ser curl post s0 kuchiyose /api/admin/customers/<CUSTOMER_ID>/manual-card-request \
  --data '{:card-profile :debit-single :features-to-activate #{:debit} :savings-account-id #uuid "69efad12-3a82-4686-a454-0317f6fae9ba" :product-type :gold-debit :virtual? true :source-type :primary-card :source-id #uuid "__SID__"}' \
  --content-type edn --env staging --cid <CID>
```

### Create a card — Credit (gold)
> `uuidgen | xargs -I__SID__` auto-fills `source-id` at runtime — no need to pre-generate it.
```bash
uuidgen | xargs -I__SID__ \
  <ACCOUNT> ser curl post <SHARD> kuchiyose /api/admin/customers/<CUSTOMER_ID>/manual-card-request \
  --data '{:card-profile :credit-single :features-to-activate #{:credit} :savings-account-id #uuid "<SAVINGS_ACCOUNT_ID>" :product-type :gold :virtual? true :source-type :primary-card :source-id #uuid "__SID__" :credit-account-id "<CREDIT_ACCOUNT_ID>"}' \
  --content-type edn --env <ENV> --cid <CID>
```
_Example:_
```bash
uuidgen | xargs -I__SID__ \
  nu-mx ser curl post s0 kuchiyose /api/admin/customers/<CUSTOMER_ID>/manual-card-request \
  --data '{:card-profile :credit-single :features-to-activate #{:credit} :savings-account-id #uuid "69efad12-3a82-4686-a454-0317f6fae9ba" :product-type :gold :virtual? true :source-type :primary-card :source-id #uuid "__SID__" :credit-account-id "69efad11-127a-4d15-ab4f-5204cb12a660"}' \
  --content-type edn --env staging --cid <CID>
```
> `<SAVINGS_ACCOUNT_ID>` / `<CREDIT_ACCOUNT_ID>` in the example are sample values —
> always swap for real ones. `source-id` is generated fresh by `uuidgen` each run.

---

## Tokenization & fraud

### Check the public-transport tokenization-fraud rule (piatã)
> piatã `/tokenization-requests/validate` runs **only the public-transport
> fraudster rule** and returns `{"result":"approved"|"denied"}`. It is NOT the
> orange-path / device-score TAR decision — those live in lost-boy's tokenization
> authorizer and piatã's `activation-path`, both gated by
> `:apple-pay-deny-orange-path-{manual,push}-provisioning` (keyed by customer-id).
> `<CUSTOMER_ID>` is the card's resolved customer — for an **additional card that's
> the TITULAR (owner), not the holder** — on the titular's `<SHARD>`.
> `uuidgen | xargs -I__AID__` auto-fills a throwaway `authorization-id`.
```bash
uuidgen | xargs -I__AID__ \
  <ACCOUNT> ser curl post <SHARD> piata /api/tokenization-requests/validate \
  --data '{"customer-id":"<CUSTOMER_ID>","authorization-id":"__AID__"}' -f
```
_Example:_
```bash
uuidgen | xargs -I__AID__ \
  nu-br ser curl post s3 piata /api/tokenization-requests/validate \
  --data '{"customer-id":"5b799d26-efbf-4b0b-ae75-56527d49fe5b","authorization-id":"__AID__"}' -f
```

---

## Queries

### Alexandria log (Grafana SQL — find a topic message by id)
```sql
SELECT
  *
FROM
  nu.logs.k8s
WHERE
  $__timeRange()
  AND service = '<SERVICE>'
  AND json_value(log, 'lax $.data.topic') LIKE '%<TOPIC>%'
  AND log LIKE '%<UUID_TO_TRACE>%'
ORDER BY
  time DESC
LIMIT
  100
```
_Example:_ `<SERVICE>` = `manic-mailman`, `<TOPIC>` = `CARDS.FEATURE-CHANGED`,
`<UUID_TO_TRACE>` = the id you're following. `$__timeRange()` is the Grafana
dashboard time picker — leave it as-is.

---

## Adding a new command

Keep the **template-first + `Example`** shape: one fenced template using only
placeholders from the legend, then one concrete `Example`. One recipe = one
runnable command. Add any new placeholder to the legend so names stay uniform.
If a section grows past comfortable scanning, split it into its own `<topic>.md`
next to this file and link it from here.

$ARGUMENTS
