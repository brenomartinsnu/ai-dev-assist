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
| **peter-pan** | active (Authorizer squad) | HSM interface — generates the actual CVV/PIN-block values Rivendell asks for. See `services/peter-pan.md`. |
| **gilfoyle** | active (Authorizer squad) | Keeps `common-pan-mapping` up to date; exposes an admin PAN lookup. See `services/gilfoyle.md`. |

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

## Security-data (CVV/PIN) dataprep flow

Rivendell's `PUT /api/cards/:id/prepare` (called by moria) does, synchronously,
in order: fetch card from **crebito**, fetch personalization from
**hitaiate** (a 404 here is normal — it just means no personalization
overrides exist for that customer), fetch encrypted PIN from **pinboard**,
resolve PAN from `common-pan-mapping` (via **gilfoyle**'s backing store — see
`services/gilfoyle.md`), then call **peter-pan**'s `POST
/api/operations/execute` to get the actual CVV1/CVV2/CVV3 + PIN block from the
HSM (see `services/peter-pan.md`). All of this happens inside one ~100–200ms
HTTP call; there is no caching or idempotency layer in Rivendell.

## Debug pattern: field correct upstream, wrong/missing in the embossed card, no error anywhere

This has happened at least twice with two different fields (braille
personalization; CVV) and the same shape both times: **every hop in the
pipeline returns 200, no deadletter, no alert — the data is just silently
empty by the time it reaches the embossing file.** Don't stop at the first
service where the symptom is visible (e.g. Balrog's embossing file) — that
service is usually just a symptom amplifier (its adapters default missing
fields with `(or false ...)`-style code with no error), not the origin.

Known root-cause shapes, roughly in the order to check them:
1. **Rivendell deploy-time config gap** (braille case, confirmed root cause):
   `rivendell/personalization/logic/personalization.clj`'s
   `allowed-personalizations` only lets `braille?`/`member-number` through for
   product types explicitly whitelisted in Rivendell's **production config**
   — which lives on a separate `config` git branch
   (`src/prod/rivendell_<country>_config.json`), **not** `main`. A missing
   entry for a given product type strips the field unconditionally, for
   every card of that type, 100% reproducible. `main`'s
   `resources/rivendell_config.json.base` is a local/test file with
   different sample data — don't use it to reason about production behavior.
2. **Asymmetric `assoc-some` vs. plain `assoc`** in a response-building
   adapter (CVV investigation, leading hypothesis, not yet proven for a
   specific case): `rivendell/adapters/card.clj`'s `applications->wire`
   builds `:cvv` with a plain hash-map literal (always included, even if
   `nil`) right next to `:magnetic-stripe`/`:pinblock` which use
   `misc/assoc-some` (only included if non-nil). A `nil` produced anywhere
   upstream (e.g. a missing key in peter-pan's `execute-operations`
   response) sails straight through as `"cvv": null` in a 200 response.
   Prismatic schema `:required true` on the internal model does **not**
   protect against this — `s/defn` validation typically isn't enforced at
   runtime in production, only in tests.
3. **HSM return-code `"01"`** on the specific operation (peter-pan
   `adapters/hsm.clj`) — resolves as a *successful* Future with value `:nok`,
   which becomes `nil` with no exception. Confirmed **ruled out** for the
   CSEO-6946 cards specifically (return-code was `"00"` throughout), but
   worth checking first for any future case since it's the cheapest to check
   (one Alexandria query, see `log-forensics` skill).

See the `log-forensics` skill for the actual queries (Databricks + Alexandria)
used to trace a card end-to-end and rule hypotheses in/out.
