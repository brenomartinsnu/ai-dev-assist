# piata

**Rules / authorization engine in the tokenization path** — sits in the chain **`lost-boy → saturn → piata`** for **TAR** (Tokenization Authorization Request): **GREEN / YELLOW / RED** paths for digital wallets (Apple Pay, Google Pay, etc.), anchor card data, **DE124** / issuer product configuration.

## Repository

- https://github.com/nubank/piata

## ISA

- https://backoffice.ist.nubank.world/isa/#/services/piata/overview

## What it does

- Central place for **TAR decision rules**; logic has been **migrated from lost-boy** into piata over time.
- Integrates with **brecho** for **card skin → product-configuration-id** when building wallet responses (see Card Creation Confluence: wallet template customization).
- Works with **saturn** and **lost-boy** for embedded data and downstream MDES behavior.

## See also

- `card-creation.md` (platform table)
- `services/brecho.md`, `services/faramir.md`
