# brecho

**Card design customization (skins).** Registry of which visual **skin/collection** each card uses; integrates with **digital wallets** (MDES product configuration) and **Piatã** (TAR / tokenization).

## Repository

- https://github.com/nubank/brecho

## ISA

- https://backoffice.ist.nubank.world/isa/#/services/brecho/overview

## What it does

- **Owns:** per-card selection (`card-id` → `skin-id`, `collection-id`, `selected-at`) in **Datomic**; static catalog of collections/skins (e.g. `brecho_config.json.base`).
- **Does not own:** Rosetta/visual assets (Heisenberg), eligibility tiers, payment for skins (future).
- **Consumers:** **Better Call Saul** (BFF): card details, summaries, PUT skin after VC creation; **Piatã** reads skin for TAR / `issuer-product-configuration-id` (DE124); **Faramir** reacts to skin changes for existing MDES tokens.
- **Events:** can publish **`CARD-SKIN-CHANGED`** (skin updates → downstream wallet artwork updates). See Card Creation Confluence epics (e.g. wallet template customization).

## API (typical)

- `GET /collections`, `GET /collections/{id}`, `GET /skins/{id}`
- `GET /cards/{id}/skin`, `GET /card-skins?card-ids=...`, `PUT /cards/{id}/skin`

## Related docs

- Service discovery in repo: `docs/service_discovery.md`
- Confluence (Card Creation space): skin + wallet flows with Piatã / Faramir
