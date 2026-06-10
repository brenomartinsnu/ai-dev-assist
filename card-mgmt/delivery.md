# Delivery Platform

Confluence: https://nubank.atlassian.net/wiki/spaces/CARDDELVPLAT

Responsible for physical card logistics — from handing cards to carriers until the customer receives them.

## Services

| Service | Status | Description |
|---|---|---|
| **frodo** | active (migration) | New service for delivery lifecycle management. Replacing sendman for new deliveries. Migration in progress. |
| **norn** | active | Selects the best carrier for delivery based on predefined rules. |
| **hel** | active | Handles delivery problems and resolution flows. |
| **batchman** | active | Batch aggregator — also used by the Embossing Platform. Centralizes delivery problem solutions sent to carriers. |
| **delivery-address** | active (to deprecate) | Stores all addresses where a delivery was attempted. Will be replaced by a registry platform. |
| **sendman** | ⚠️ legacy | Original central delivery service. Also handles embossing supplier routing for old flows. Being replaced by frodo. |

## Carrier Integration Services

| Service | Carrier | Country |
|---|---|---|
| **estafeta-client** | Estafeta | 🇲🇽 |
| **domesa-client** | Domesa | 🇨🇴 |
| **domina-client** | Domina | 🇨🇴 |
| **dhl-client** | DHL | 🇧🇷 / multi |
| **flash-client** | Flash | 🇧🇷 |
| **mobi-client** | Mobi | 🇧🇷 |

## Card Tracking Flow

```
1. Card created in our systems
2. Embossing file sent to embosser (one line per card)
3. Embosser returns "in file"  → confirms receipt, manufacturing starts
4. Embosser returns "out file" → cards completed and handed to carrier
5. Carrier is queried for delivery status updates
6. "Delivered" event received from carrier → customer notified
```

## Old vs New carrier tracking flow

Historically, sendman handled all carrier communication. A new architecture gives each carrier its own client service.

| Flow | Carriers | How it works |
|---|---|---|
| **Old flow** | `correios`, `loggi`, `flash`, `icourier`, `dhl` | sendman handles all logic internally; scheduled via tempo |
| **New flow** | `domesa`, `estafeta`, `domina` | Dedicated `<carrier>-client` service handles communication and event mapping |

### Old flow (sendman) carrier details

| Carrier | Request pattern |
|---|---|
| DHL | First fetches hawb number using `card-tracking-id` (falls back to `card-id`), then fetches events using hawb |
| Flash | Uses `:dispatch-code` as `:numEncCli` |
| iCourier | Uses `:dispatch-code` as `:numEncCli` |
| Loggi | Uses `:dispatch-code` as `:tracking-key` |

## Key concepts

| Concept | Meaning |
|---|---|
| **Dispatch code** | Identifier used to query a carrier's tracking API |
| **HAWB number** | DHL-specific identifier used to query shipping events |
| **Delivery problem** | When a card cannot be delivered — handled by hel, may involve sending batch instructions to the carrier |
| **Welcome kit** | Packaged delivery combining multiple cards (e.g., duo-card used in 🇲🇽 and 🇨🇴) |
