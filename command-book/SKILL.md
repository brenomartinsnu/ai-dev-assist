---
name: command-book
description: >-
  Personal catalog of ready-to-run Nubank commands — nucli (`nu ...`), `ser curl`
  service calls, `kafka produce`, project setup, and observability queries. Use
  when the user asks "how do I <do X>", "what's the command / curl / nucli for
  <X>", or names a known recipe: produce a topic, create a customer, get/activate/
  create a card, refresh credentials, start a new nu-service, update Santa rules,
  adjust a card's category/product type, or pull Alexandria logs. Recall the
  matching template, fill in the user's IDs,
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
   Apply the **Defaults** below for anything the user didn't specify. If a
   *required* value has no default and is missing, ask for it — or leave the
   `<PLACEHOLDER>` in place and call it out explicitly. Never invent IDs. Use the
   `Example` only as a shape reference, never copy its literal ids/values.
3. **Output ONE ready-to-run command** in a copy-able code block.
4. **Do NOT run it.** Hand it to the user to execute. (If they explicitly say
   "run it", you may, but default to handing it over.)
5. **Output only the command** — no assumptions / env / shard / account recap
   footer. Only call out a `<PLACEHOLDER>` you had to leave unfilled.

### Defaults

When the user doesn't say otherwise:
- **`<ACCOUNT>` → `nu-br`** (Brazil 🇧🇷).
- **`<ENV>` → `prod`, written explicitly as `--env prod`.** Never omit `--env`.
  Use `--env staging` only when the user explicitly asks for staging.

### Placeholder legend

Every recipe draws its placeholders from this single table — keep them uniform.

| Placeholder | Meaning | Example value |
|---|---|---|
| `<ACCOUNT>` | Account alias prefix for nucli | `nu-br` 🇧🇷 (default) · `nu-mx` 🇲🇽 · `nu-co` 🇨🇴 |
| `<ACCOUNT_ALIAS>` | Bare account alias (for `--account-alias`) | `br` · `mx` · `co` |
| `<SHARD>` | Shard for the service call | `s0` (sharded) · `global` (non-sharded) |
| `<SERVICE>` | Target service name | `crebito` · `kuchiyose` · `factorio` |
| `<METHOD>` | HTTP verb | `get` · `post` · `put` · `delete` |
| `<PATH>` | API route on the service | `/api/customers/<id>/all-cards` |
| `<ENV>` | Environment | `prod` (default) → write `--env prod`; `--env staging` for staging |
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
| `<PRODUCT_ID>` | Card product id (hitaiate) | from the `/product` lookup below |
| `<PRODUCT_TYPE>` | Target card product type | `gold` · `platinum` |
| `<COMBO_PRODUCT_TYPE>` | Target combo product type | `gold` · `platinum` |
| `<USER_ID>` | Nubank user email local-part (no `@nubank.com.br`) | `somebody.bla` |
| `<COUNTRY>` | Country/geography for `--country` flag | `br` (default) · `mx` · `co` |

### Command grammar (for building variants not in the catalog)

- **Service call:** `<ACCOUNT> ser curl <METHOD> <SHARD> <SERVICE> <PATH> [--env <ENV>] [-f] [-d '<json>' | --data '<edn>' --content-type edn] [--cid <CID>]`
  - `-f` follows redirects / fails on error (keep it for reads).
  - **Always write `--env` explicitly:** `--env prod` for prod (default),
    `--env staging` for staging. (Prod is live — be careful.)
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

### Get all cards for a customer (default — excludes canceled)
> All **non-canceled** cards, physical + virtual. Route `:all-cards-non-canceled-by-customer`.
> This is the default "get all cards" recipe. Use the **include-canceled** variant
> below only when the user explicitly asks to include canceled cards.
```bash
<ACCOUNT> ser curl get <SHARD> crebito /api/customers/<CUSTOMER_ID>/cards/all-cards-non-canceled --env <ENV> -f
```
_Example:_
```bash
nu-mx ser curl get s0 crebito /api/customers/<CUSTOMER_ID>/cards/all-cards-non-canceled --env staging -f
```
> Physical-only variant: swap the path for `/api/customers/<CUSTOMER_ID>/cards/non-canceled` (route `:non-canceled-cards-by-customer`).

### Get all cards for a customer, including canceled
> Returns **every** card (including canceled), sorted by tx instant. Route `:get-all-cards-by-customer`.
> Use only when the user explicitly asks for canceled cards to be included.
```bash
<ACCOUNT> ser curl get <SHARD> crebito /api/customers/<CUSTOMER_ID>/all-cards --env <ENV> -f
```
_Example:_
```bash
nu-mx ser curl get s0 crebito /api/customers/<CUSTOMER_ID>/all-cards --env staging -f
```

### Get one card (by card id)
> Single card with profile + activation status. Keyed by `<CARD_ID>`, on the card owner's `<SHARD>`. Route `:one-card` → `in/one-card+profile+activation-status`.
```bash
<ACCOUNT> ser curl get <SHARD> crebito /api/cards/<CARD_ID> --env <ENV> -f
```
_Example:_
```bash
nu-mx ser curl get s0 crebito /api/cards/<CARD_ID> --env staging -f
```

### Activate a card
```bash
<ACCOUNT> ser curl post <SHARD> crebito /api/cards/<CARD_ID>/activation --env <ENV> -f -d '{"last-four": "<LAST_FOUR>"}'
```
_Example:_
```bash
nu-mx ser curl post s0 crebito /api/cards/<CARD_ID>/activation --env staging -f -d '{"last-four": "1234"}'
```

### Create a card — Debit
> `uuidgen | xargs -I__SID__` auto-fills `source-id` at runtime — no need to pre-generate it.
> **`<PRODUCT_TYPE>` is country-specific** — see the table below. Don't assume
> `gold-debit` applies outside BR/MX; US uses a flat `debit-card` type.
```bash
uuidgen | xargs -I__SID__ \
  <ACCOUNT> ser curl post <SHARD> kuchiyose /api/admin/customers/<CUSTOMER_ID>/manual-card-request \
  --data '{:card-profile :debit-single :features-to-activate #{:debit} :savings-account-id #uuid "<SAVINGS_ACCOUNT_ID>" :product-type <PRODUCT_TYPE> :virtual? true :source-type :primary-card :source-id #uuid "__SID__"}' \
  --content-type edn --env <ENV> --cid <CID>
```
_Example (BR/MX — gold):_
```bash
uuidgen | xargs -I__SID__ \
  nu-mx ser curl post s0 kuchiyose /api/admin/customers/<CUSTOMER_ID>/manual-card-request \
  --data '{:card-profile :debit-single :features-to-activate #{:debit} :savings-account-id #uuid "69efad12-3a82-4686-a454-0317f6fae9ba" :product-type :gold-debit :virtual? true :source-type :primary-card :source-id #uuid "__SID__"}' \
  --content-type edn --env staging --cid <CID>
```
_Example (US — flat debit product):_
```bash
uuidgen | xargs -I__SID__ \
  nu-us-staging ser curl post s0 kuchiyose /api/admin/customers/<CUSTOMER_ID>/manual-card-request \
  --data '{:card-profile :debit-single :features-to-activate #{:debit} :savings-account-id #uuid "6890f198-4020-40d8-89b7-0e09c7837b88" :product-type :debit-card :virtual? true :source-type :primary-card :source-id #uuid "__SID__"}' \
  --content-type edn --env staging --cid <CID>
```

#### `<PRODUCT_TYPE>` by country (debit)
| Country | `<PRODUCT_TYPE>` |
|---|---|
| BR / MX | `:gold-debit` |
| US | `:debit-card` |
> US has no gold/platinum debit tiering — confirm against the target account's
> product catalog before assuming other countries follow BR's tiered values.

### Create a card — Credit (gold)
> `uuidgen | xargs -I__SID__` auto-fills `source-id` at runtime — no need to pre-generate it.
> This is a **BR/MX example** (`:product-type :gold`). Not yet confirmed for US —
> don't assume it carries over; check the target country's product catalog first.
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

## Card category / product type (hitaiate)

> Use when a card issued with the wrong category (e.g. gold vs platinum), a
> virtual card came out wrong, an up/downgrade didn't take, or before reissuing
> a physical card with the correct product type. Required scope:
> `update-card-parameters`. Two-step: look up the current `product_id` first,
> then post the correction.

### Check the current product
```bash
<ACCOUNT> ser curl get <SHARD> hitaiate /api/customers/<CUSTOMER_ID>/product --env <ENV> -f
```
_Example:_
```bash
nu-br ser curl get s0 hitaiate /api/customers/<CUSTOMER_ID>/product --env prod -f
```
> Save the `product_id` field from the response for the next step.

### Update the card parameters
```bash
<ACCOUNT> ser curl post <SHARD> hitaiate /api/admin/card-parameters/customer/<CUSTOMER_ID> \
  -d '{
    "document": {
      "product_id": "<PRODUCT_ID>",
      "product_type": "<PRODUCT_TYPE>",
      "combo_product_type": "<COMBO_PRODUCT_TYPE>"
    }
  }' --env <ENV> --cid <CID>
```
_Example:_
```bash
nu-br ser curl post s0 hitaiate /api/admin/card-parameters/customer/<CUSTOMER_ID> \
  -d '{
    "document": {
      "product_id": "<PRODUCT_ID>",
      "product_type": "gold",
      "combo_product_type": "gold"
    }
  }' --env prod --cid CARD-1234
```
> `<CID>` here is the ticket ID for tracking (e.g. `CARD-1234`), not a UUID.

### Default `<PRODUCT_ID>` values (BR)
> Observed defaults for standard BR products — confirm against the `/product`
> lookup for the specific customer before trusting these for an edge case.

| `<PRODUCT_TYPE>` | `<PRODUCT_ID>` (BR) |
|---|---|
| `platinum` | `ff98fb1b-b502-4634-b7e9-fe841373af6d` |
| `gold` | `d1cc5be8-de2a-4f83-9323-b0a2209b9216` |

---

## Card features (enable / eligibility)

### Check debit-feature eligibility (batuta)
> Programmatic debit-eligibility check for a customer. Pairs with "Enable the
> debit feature" below. `batuta` is the debit-eligibility service.
```bash
<ACCOUNT> ser curl get <SHARD> batuta /api/customers/<CUSTOMER_ID>/debit-feature-eligibility --env <ENV> -f
```
_Example:_
```bash
nu-br ser curl get s19 batuta /api/customers/5b799d26-efbf-4b0b-ae75-56527d49fe5b/debit-feature-eligibility --env prod -f
```

### Enable the debit feature (crebito)
> Admin route, keyed by `<CARD_ID>`. **Before enabling:** confirm the customer's
> debit account is **requested and active** in the "Nuconta" widget (3rd column).
> Empty body: `--data '{}'`.
```bash
<ACCOUNT> ser curl put <SHARD> crebito /api/admin/cards/<CARD_ID>/features/debit/enable --data '{}' --env <ENV>
```
_Example:_
```bash
nu-br ser curl put s0 crebito /api/admin/cards/69c1a764-e413-47fa-a452-5f19cc9bb5cd/features/debit/enable --data '{}' --env prod
```

### Enable the credit feature (crebito)
> Admin route, keyed by `<CARD_ID>`. **Before enabling:** confirm a credit account
> exists for the customer in the "Conta" widget (2nd column). Empty body: `--data '{}'`.
```bash
<ACCOUNT> ser curl put <SHARD> crebito /api/admin/cards/<CARD_ID>/features/credit/enable --data '{}' --env <ENV>
```
_Example:_
```bash
nu-br ser curl put s0 crebito /api/admin/cards/69c1a764-e413-47fa-a452-5f19cc9bb5cd/features/credit/enable --data '{}' --env prod
```

### Fix confirmed-shipping-status mismatch (crebito migration)
> Use when the physical card's feature(s) are already **active** in crebito but
> shuffle still shows shipping status as **entregue** (stuck, not reflecting
> activation) — a stale card-tracking sync, not a feature-enablement gap.
> **Validate first:** confirm in crebito that the feature(s) are active, and
> confirm shuffle still shows "entregue" for that card. Only then run the
> migration below.
```bash
<ACCOUNT> ser curl put <SHARD> crebito /api/admin/migration/cards/<CARD_ID>/fix-confirmed-shipping-status --env <ENV>
```
_Example:_
```bash
nu-br ser curl put s2 crebito /api/admin/migration/cards/6a33ffa4-13d6-4cd4-88be-a8999c6bc9a5/fix-confirmed-shipping-status --env prod
```

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

### Add customer to Apple Pay orange-path exception list
> `nu` top-level CLI subcommand (not the `ser curl` grammar) — allowlists a
> customer against the orange-path / device-score TAR deny decision described
> above.
```bash
nu card orange-path-allow <CUSTOMER_ID>
```
_Example:_
```bash
nu card orange-path-allow 5b799d26-efbf-4b0b-ae75-56527d49fe5b
```

---

## Security / access scopes

### Show a user's scopes (by country)
> Lists scopes currently granted to a user, plus (for yourself) a comparison
> against the scopes on your live access token. `<USER_ID>` is the email
> local-part (no `@nubank.com.br`). Omit `<USER_ID>` to check your own scopes.
> Re-run with a different `--country` to check another geography (`br`/`mx`/`co`).
```bash
nu security scope show <USER_ID> --country <COUNTRY> --env <ENV>
```
_Example:_
```bash
nu security scope show somebody.bla --country mx --env prod
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
