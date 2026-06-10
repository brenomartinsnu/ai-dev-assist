# crebito

**Card lifecycle source of truth** — **the** central service for **card** records: status, block, cancel, activation, reissue hooks, shards, and most **`nu ser curl`** operational APIs.

## Repository

- https://github.com/nubank/crebito

## ISA

- https://backoffice.ist.nubank.world/isa/#/services/crebito/overview

## Role in card creation

- After orchestration generates PAN and parameters, **crebito** persists and tracks the card for its lifetime.
- **joker** reads from crebito for chain history; **kageyose** surfaces customer card lists; agents use crebito via tools and **mr-shuffle**.

## Operations

- See **`card-creation.md`** for `nu ser curl` patterns (get card, activate, reissue, cancel, block) and **shard** usage.

## See also

- `card-hierarchy.md` (joker + crebito)
