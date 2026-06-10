# radio-peao

Clojure microservice in the **card / data-subject rights** space: orchestrates **card-related personal data** for **access report** (LGPD-style data portability / subject access) requests.

## Repository

- https://github.com/nubank/radio-peao

## ISA

- https://backoffice.ist.nubank.world/isa/#/services/radio-peao/overview

## What it does

1. **Consumes** Kafka messages asking for access-report processing tied to a **process id** and **data subject identifiers** (prospect-id, customer-id, tax-id, etc., with shard/prototype).
2. **Chains two steps**:
   - On `request-access-report-data`, it **requests card data** by producing to `request-access-report-cards-data` (same payload shape as input).
   - On `request-access-report-cards-data`, it **resolves the customer** from identifiers, **fetches the customer’s cards** from **kageyose** over HTTP, builds an **access report** for the cards product, and **produces** the result on `access-report-data`.
3. Exposes a minimal **HTTP API** (e.g. `/api/version`); the main work is **async via Kafka**.

## Upstream / downstream

| Direction | System | Role |
|-----------|--------|------|
| HTTP client | **kageyose** | `GET` bookmark `:kageyose/customer-cards` — list cards for a customer (by id + shard). Wired in `radio-peao.diplomat.http-client`. |
| Kafka | Producers/consumers of access-report topics | See topics below. |

## Kafka topics (logical names in code)

Consumer handlers (`radio-peao.diplomat.consumer`):

| Topic | Handler purpose |
|-------|-----------------|
| `request-access-report-data` | Emit `request-access-report-cards-data` to pull card slice. |
| `request-access-report-cards-data` | Load cards via kageyose, build report, emit `access-report-data`. |

Producer (`radio-peao.diplomat.producer`):

| Topic | Notes |
|-------|--------|
| `request-access-report-cards-data` | Request payload: access-report request wire. |
| `access-report-data` | Output report; `edn+secure`, privacy group `data-subject-rights`. |

## Core models (names only)

- **AccessReportRequest**: `process-id`, `data-subject-identifiers` (type, prototype/shard, values).
- **AccessReport**: `product-name`, `process-id`, `data` (card report payload for cards flow).

## Diagrams

- BELA (VPN): https://bela.nubank.com.br/diagram/service/radio-peao

## Stack notes

- **Pedestal** HTTP, **Component** system, **common-kafka**, **common-http-client**, **card-definition** (NuBank lib).
- **Sachem** entry: `radio-peao.server/start-sachem-system` (see `resources/sachem.edn`).

## Gaps / TODOs for this doc

- README in repo is still mostly template; replace owner channel in README when publishing.
- Confirm exact Kafka topic names and env-specific config in ISA or deployment config if you need operations runbooks.
