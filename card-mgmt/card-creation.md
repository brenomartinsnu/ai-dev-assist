# Card Creation Platform

Confluence: https://nubank.atlassian.net/wiki/spaces/CARDCREATPLAT

Responsible for orchestrating card creation requests, eligibility validation, and PAN generation.

## Services

| Service | Description |
|---|---|
| **crebito** | Source of truth for card lifecycle — tracks block, cancellation, and activation statuses. Central service for all card operations. |
| **kuchiyose** | Main orchestrator for card creation flows. |
| **shinkiro** | Requests creation of a virtual card and validates customer eligibility. |
| **arnaldo** | Manages card reissue requests. |
| **gaara** | Orchestrates feature requests; entry point for combo card creation. |
| **gambit** | Entry point for single card creation. |
| **pandora** | Generates PAN numbers (the card's 16-digit number). |
| **hitaiate** | Source of truth for card parameters (e.g., product type, braille). |
| **daronco** | Validates eligibility for card issuance/reissuance. |
| **better-call-saul** | Virtual card eligibility service and API gateway for card profiles. Aggregates card data and handles business logic per card profile. Has geo-specific HTTP bookmarks per country (BR, CO, MX, CH) and Kafka consumers that invalidate eligibility caches on account lifecycle events (`new-savings-account`, `savings-account-status-updated`). |
| **piata** | Rules/authorization engine sitting in the tokenization flow (`lost-boy → saturn → piata`). Handles TAR (Tokenization Authorization Request) logic — decides GREEN/YELLOW/RED paths for digital wallet provisioning (Apple Pay, Google Pay, etc.), fetches anchor card data, and builds the DE124 response. TAR logic is currently being migrated from `lost-boy` into piata. |

## Card Types & Features

| Concept | Meaning |
|---|---|
| **primary** | The main card belonging to the account holder |
| **additional** | Card issued for a third party authorized by the account holder |
| **company** | Card associated with a PJ (business) account |
| **physical** | Embossed plastic card |
| **virtual** | Card number without a physical form |
| **combo** | Card with both credit and debit features enabled |
| **credit-only** | Card with credit feature only (common in 🇲🇽) |
| **debit-only** | Card with debit feature only (common in 🇲🇽) |

## crebito API patterns (via `nu ser curl`)

Always use `--cid` with a descriptive label for traceability in Splunk.

### Get card info
```bash
nu ser curl get <shard> crebito /api/cards/<card_id> --env <env>
```

### Activate card
```bash
nu ser curl post <shard> crebito /api/cards/<card_id>/activation \
  --env <env> --cid <trace-label> \
  -d '{"last_four":"XXXX"}'
```

### Reissue card
```bash
nu ser curl put <shard> crebito \
  /api/admin/customers/<customer_id>/cards/reissue/<card_type> \
  --env <env> --cid <trace-label>
```

### Cancel card
```bash
nu ser curl delete <shard> crebito /api/admin/cards/<card_id>/cancel \
  --env <env> --cid <trace-label> \
  -d '{"reason": "<reason>"}'
```

### Block card
```bash
nu ser curl put <shard> crebito /api/cards/<card_id>/block \
  --env <env> --cid <trace-label> \
  -d '{"reason": "<reason>"}'
```

> Valid block/cancel reasons are defined in crebito's `/schemata/feature.clj`.

## Key concepts

| Concept | Meaning |
|---|---|
| **PAN** | 16-digit card number |
| **Shard** | Partition of the crebito database (`s0`, `s1`, etc.) — required in `nu ser curl` commands |
| **CID** | Correlation ID for Splunk tracing — use `--cid` with a descriptive label on every operation |
