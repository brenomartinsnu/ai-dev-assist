# joker

**Card succession chains** — tracks **ordered chains** of cards per customer (by chain type) so **ABU** and **digital wallets** can follow PAN changes after cancel/replace.

## Repository

- https://github.com/nubank/joker

## ISA

- https://backoffice.ist.nubank.world/isa/#/services/joker/overview

## What it does

- Consumes activation/cancellation signals; emits **`CARD-CHAIN/NEW-EVENT`**; uses **crebito** to backfill card data when building chains.
- **Fraud / closure rules** decide whether to **close** a chain vs **link** a new card (see RFC linked from `card-hierarchy.md`).

## See also

- `card-hierarchy.md` (full model: chain types, events, fraud rules)
- `services/crebito.md`
