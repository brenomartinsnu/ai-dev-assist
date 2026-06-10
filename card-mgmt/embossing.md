# Embossing Platform

Confluence: https://nubank.atlassian.net/wiki/spaces/CARDEMBPLAT

Responsible for physical card manufacturing — preparing card data and coordinating with embossers (third-party card manufacturers such as Thales and Valid).

## Services

| Service | Status | Description |
|---|---|---|
| **rivendell** | active | Dataprep: retrieves PAN in clear, generates security data (CVVs, PIN block via Peterpan), formats card names (printed-name and back-name), validates personalization combos (e.g., UV Metal + braille), handles chip homologation experiments. |
| **galadriel** | active | Controls physical card aggregation with country-specific rules. Holds the "Packaging" entity — aggregated cards tracked through the factoring and delivery process. |
| **moria** | active | Core embossing orchestration and source of truth for card production. Tracks factoring events from integration clients and produces a lifecycle for each relevant factoring update. |
| **balrog** | active | Parses and exchanges batch files with embossers. Configurable per country and embosser. |
| **batchman** | active | Batch aggregator for suppliers that use file-based communication. Translates raw data entries into batch files on-demand. Also used by the Delivery Platform. |
| **gemalto-client** | ⚠️ deprecated | Was the integration client for Thales embosser. Migration in progress per country. |
| **valid-client** | ⚠️ deprecated | Was the integration client for Valid embosser. |
| **thales-client** | ⚠️ deprecated | Replaced by the new embosser integration approach. |

## Embossing Flow

```
Card Creation
    │
    ▼
rivendell        ← dataprep: PAN clear, CVVs, PIN block, name formatting
    │
    ▼
galadriel        ← aggregation with country-specific packaging rules
    │
    ▼
moria            ← orchestration, source of truth for production status
    │
    ▼
balrog           ← generates embossing file (batch), sends to embosser
    │
    ▼
Embosser (Thales / Valid)
    │
    ├── "in file"  → embosser confirms receipt and is manufacturing
    └── "out file" → cards completed and handed to carrier
```

## File-based communication

| File | Direction | Meaning |
|---|---|---|
| **Embossing file** | Nubank → Embosser | One line per card. Contains all data needed to manufacture the card. |
| **In file** | Embosser → Nubank | Confirms the embosser received the cards and started manufacturing. |
| **Out file** | Embosser → Nubank & Carrier | Cards are completed and handed to the delivery carrier. Triggers the start of delivery tracking. |

## Key concepts

| Concept | Meaning |
|---|---|
| **Embosser** | Third-party manufacturer that physically produces the cards (prints, chips, etc.) |
| **Dataprep** | The step where card data is prepared and security credentials generated before sending to the embosser |
| **Factoring** | The card manufacturing/production process at the embosser side |
| **Packaging** | Entity in galadriel representing aggregated cards (e.g., duo-card welcome kits used in 🇲🇽 and 🇨🇴) |
| **Chip homologation** | Experiment that may swap the card plastic while validating a new chip with an embosser |
| **ABU** | Automatic Billing Updater — updates stored card numbers at merchants for recurring billing when cards change |
