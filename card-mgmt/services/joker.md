# joker

**Card succession chains** — tracks **ordered chains** of cards per customer (by chain type) so **ABU** and **digital wallets** can follow PAN changes after cancel/replace.

## Repository

- https://github.com/nubank/joker

## ISA

- https://backoffice.ist.nubank.world/isa/#/services/joker/overview

## What it does

- Consumes activation/cancellation signals; emits **`CARD-CHAIN/NEW-EVENT`**; uses **crebito** to backfill card data when building chains.
- **Fraud / closure rules** decide whether to **close** a chain vs **link** a new card (see RFC linked from `card-hierarchy.md`).

## Data model (Datomic, 5 entities)

- **`chain`** (`joker.models.chain`): the succession identity. `:chain/id`, `:chain/customer` (ref), `:chain/type` (keyword, computed, not enumerated: concatenation of category + card-type + feature-type, e.g. `:chain.type/primary-card-physical-credit`, optionally suffixed with a temp-card id or a formatted label), `:chain/previous-chain` (self-ref, set when the chain was opened to replace one closed for fraud), `:chain/created-at`. Category enum (`:chain/category`, not stored on `chain` itself but used to build `:chain/type`): `additional-card`, `company-card`, `primary-card`, `extra-voucher-card`.
- **`chain-state`** (`joker.models.chain-state`): **1:1 with `chain`, mutated in place** (not a per-transition log — `chain-state-by-chain-id!` asserts a single result, and updates re-upsert the same `:chain-state/id`). Holds `:chain-state/chain` (ref), `:chain-state/last-event` (ref), `:chain-state/last-card` (ref), `:chain-state/chain-status` (`open`/`closed`). This is the current-pointer table drivers query against (by customer+chain-type, by chain-id, by card-id).
- **`event`** (`joker.models.event`): the actual append-only per-transition log. `:event/id`, `:event/chain` (ref), `:event/card` (ref), `:event/type` (`new`, `replacement`, `suspend`, `close`), `:event/previous-card` (ref, set on replacement/close so the prior PAN is traceable). `chain-status` only ever tracks open/closed, so `event/type` is the only place that records *why* a transition happened.
- **`customer`**: thin entity, just enough to attribute a chain to a customer id (fields lifted off the incoming crebito message).
- **`card`**: joker's own denormalized view of a card (id, label, virtual?, behavior/feature-type), backfilled from **crebito** when building/advancing a chain.
- Business logic (`joker.controllers.chain`): `new-chain-state!` mints a new `chain`+`chain-state`+`new`-event on a genuinely new card; `replace-card-in-chain!` keeps the same chain but swaps `last-card`/`last-event` (replacement event) when a card is replaced in place; `close-chain!` marks the current chain-state closed; `close-current-chain-and-create-new-one!` is the fraud path, it closes the old chain-state and opens a brand-new chain that points back via `chain/previous-chain`.
- Control/dedup: `joker.controllers.migration` + `joker.logic.migration` detect and fix **duplicated open chains** for the same customer+chain-type (keeps the most recent, retires the others), and support bulk chain-type remaps (e.g. migrating legacy credit/virtual types into a `-combo` type).

## Kafka / integration

- Producer (`joker.diplomat.producer`): `:card-chain/new-event` (external, partitioned by customer-id) fires on every chain-state upsert (new/replace/close) and is what **faramir** consumes to suspend/migrate tokenizations, and what **abu**/wallets follow to keep PAN references current. Internal-only topics: `:joker-internal/migrate-chain-type`, `:joker-internal/close-chain`.
- Downstream data modeling: joker's `chain`+`chain-state` are published together as the external entity **`card-chain`** (chain-state is the root because it carries the FK-able id and current pointers; `chain`'s own attributes get folded in), and `event` is published standalone as **`card-chain-event`** (kept separate because chain-state only points at the *last* event, so the full history isn't reconstructable from chain-state alone). See `nu-data-semantic-model` config for `core-banking/joker`.

## See also

- `card-hierarchy.md` (full model: chain types, events, fraud rules)
- `services/crebito.md`
