# faramir

**Digital wallet tokenization (Mastercard MDES)** — owns **tokenization** state in **Datomic**, drives **MDES** over HTTP (`faramir.components.mdes-http`), exposes **customer + admin HTTP** APIs, and publishes **tokenization lifecycle** events on Kafka.

## Repository

- https://github.com/nubank/faramir

## ISA

- https://backoffice.ist.nubank.world/isa/#/services/faramir/overview

> **Logical topic keys** below come from `faramir.diplomat.{consumer,producer}`. Many producers use **`json+secure`**. Resolve literal cluster topic names via ISA/deployment config.

---

## What it does (high level)

- Ingests **MDES ISO8583-style messages** (new tokenization request, events, completion, activation codes) via Kafka, with **subtopics** routing TAR vs event vs completion vs activation-code.
- Surfaces **user** flows: confirm/cancel tokenization, lookup by TUR / app-to-app params / app instance id, activation codes, wallet token lists.
- **Admin / CS:** block, unblock, cancel, force MDES sync, replace token card binding, notify pending/unused tokens, read MDES token + history.
- **Migrations:** republish customers, backfill tokenizations, soft confirm/cancel, retract.
- **Related domains:** listens to **card feature** changes and **joker** `card-chain/new-event`; produces **announcements** (activation code popups), **voucher** events, and many **tokenization/** topics.

---

## HTTP API (summary)

Defined in `faramir.service/routes` + handlers in `faramir.diplomat.http-in`. Scopes vary by route—see code for `auth/allow?`.

### Discovery

| Method | Path |
|--------|------|
| `GET` | `/api/discovery` |
| `GET` | `/api/version` |
| `GET` | `/api/admin/discovery` |

### Customer / app (selection)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/customer/:id/mobile-activation-code` | Mobile activation code |
| `POST` | `/api/customer/:id/latest-activation-code` | Latest activation code |
| `PUT` | `/api/customer/:id/mobile-activation-code/announcement/dismiss` | Dismiss activation UI |
| `PUT` | `/api/tokenization/search-by-app-to-app-params` | Tokenization by app-to-app (legacy path) |
| `PUT` | `/api/customer/:id/tokenization-by-app-to-app-params` | Same, with customer id (`ohashi` + path match) |
| `PUT` | `/api/tokenization/search-by-token-unique-reference` | By TUR (legacy) |
| `PUT` | `/api/customer/:id/tokenization-by-token-unique-reference` | By TUR + customer |
| `PUT` | `/api/tokenization/search-by-payment-instance-id` | By app instance id (legacy) |
| `PUT` | `/api/customer/:id/tokenizations-by-payment-instance-id` | By app instance id + customer |
| `GET` | `/api/tokenization/:id` | Get tokenization |
| `GET` | `/api/cards/:card-id/tokenization/:id` | Get tokenization scoped by card |
| `POST` | `/api/cards/:card-id/tokenization/:id/confirm/:authentication-method` | User confirms pending tokenization |
| `POST` | `/api/tokenization/:id/cancel` | User cancels |
| `POST` | `/api/cards/:card-id/tokenization/:id/cancel` | Cancel with card scope |
| `GET` | `/api/customer/:id/wallet/:wallet/tokenizations` | List by wallet |
| `GET` | `/api/customer/:id/wallet/:wallet/active-tokenizations-count` | Active count |

### Admin (selection)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/admin/card/:id/tokenization-by-token-hash` | Lookup by card + token hash |
| `GET` | `/api/admin/tokenization/:id` | Admin get |
| `GET` | `/api/admin/tokenization/:id/events` | Event history |
| `GET` | `/api/admin/mdes-http/system-status` | MDES connectivity status |
| `GET` | `/api/admin/tokenization/:id/mdes-token` | MDES token snapshot |
| `GET` | `/api/admin/token-unique-reference/:token-unique-reference/mdes-token` | MDES by TUR |
| `GET` | `/api/admin/token-unique-reference/:token-unique-reference/mdes-token-history` | Status history |
| `POST` | `/api/admin/tokenization/:id/{block,unblock,cancel}` | Lifecycle controls |
| `POST` | `/api/admin/tokenization/:id/confirm` | Defer confirmation (admin) |
| `POST` | `/api/admin/tokenization/:id/force-sync` | Force sync from MDES |
| `POST` | `/api/admin/tokenization/:id/replace/:card-id` | Rebind token to new card |
| `POST` | `/api/admin/wallet/:wallet/notify-pending-tokenizations` | Notify pending (async) |
| `POST` | `/api/admin/wallet/:wallet/tokenization/notify-unused-tokens` | Unused-token nudge |
| `GET` | `/api/admin/token-connect/eligible-token-requestors` | Token Connect probe |
| `POST` | `/api/admin/token-connect/issuer-assets` | Issuer assets |
| `GET` | `/api/admin/customer/:id/tokenizations` | All for customer |
| `POST` | `/api/admin/migration/...` | soft-confirm, soft-cancel, retract, republish-all, backfill-all, republish customer |

---

## Kafka — consumed topics

From `faramir.diplomat.consumer/settings`:

| Topic key | Role |
|-----------|------|
| `:tokenization/new-message` | New MDES message envelope (subtopic: request / event / complete / activation-code) |
| `:tokenization/retrigger-new-message` | Retry of the above after failures |
| `:tokenization/activate-by-tur` | Activate using TUR |
| `:tokenization/force-sync-from-mdes` | Force DB sync from MDES |
| `:tokenization/verify-unused-tokenization` | Verify unused-token campaign |
| `:tokenization/call-mdes` | Explicit MDES action dispatch |
| `:tokenization/cancel-tokenization` | Cancel tokenization + event type |
| `:tokenization-mig/republish-customer` | Migration republish (leaky-bucket throttled) |
| `:tokenization-mig/backfill-tokenizations` | Backfill one tokenization id |
| `:tokenization/backfill-token` | Backfill token hash |
| `:voucher/pan-decrypted` | Voucher flow after PAN decrypt |
| `:voucher/create` | Create voucher |
| `:cards/feature-changed` | Block/unblock tokenizations on card feature change |
| `:card-chain/new-event` | **joker** chain events — update tokens on card changes |
| `:migration.create-token/migrate-entry` | Migration create entry |
| `:migration.sync-token/migrate-entry` | Migration sync entry |

Plus `:token-revoked`, `:all-tokens-revoked`, `:experiment-updated`.

---

## Kafka — produced topics

From `faramir.diplomat.producer` functions and `settings`:

| Topic key | Role |
|-----------|------|
| `:deliver-announcement` | Push/in-app announcement (e.g. mobile activation code) |
| `:cancel-announcement` | Dismiss matching announcement |
| `:tokenization/authentication-code-request` | Email auth code path |
| `:tokenization/authentication-code-mobile-request` | Mobile auth code path |
| `:tokenization/completed` | Tokenization reached completed state |
| `:tokenization/request` | Outbound “tokenization requested” (incl. denied reasons) |
| `:tokenization/authorization-update` | Auth decision updates |
| `:tokenization/notify-pending-tokenization` | Pending-token notifications |
| `:tokenization/verify-unused-tokenization` | Unused-token verification pass |
| `:tokenization/notify-unused-tokenization` | Unused-token customer comms |
| `:tokenization/activate-by-tur` | Activation by TUR |
| `:tokenization/force-sync-from-mdes` | Internal force-sync |
| `:tokenization/call-mdes` | Scheduled / retried MDES calls |
| `:tokenization/retrigger-new-message` | Defer retry of consumer message |
| `:tokenization/cancel-tokenization` | Cancel path (suspended in MDES, etc.) |
| `:tokenization-mig/republish-customer` | `{ :customer-id :card-id }` migration |
| `:tokenization-mig/customer` | Full customer migration payload |
| `:tokenization-mig/backfill-tokenizations` | `{ :tokenization-id }` |
| `:voucher/new-created` | OPC / push provisioning voucher created |

---

## Card creation ecosystem

- **brecho** skin changes → **`CARD-SKIN-CHANGED`** (and Piatã TAR) can drive **MDES token update** flows; faramir is the service that speaks MDES and holds tokenization rows.
- **piata** / **lost-boy** / **saturn** sit **upstream** of MDES messages that faramir consumes.

## See also

- `services/brecho.md`
- `services/piata.md`
- `services/sindarin.md`
- `card-hierarchy.md` (`card-chain/new-event`)
