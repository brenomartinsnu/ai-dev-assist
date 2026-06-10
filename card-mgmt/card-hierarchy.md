# Card Hierarchy

Service: **joker** (https://github.com/nubank/joker)

RFC: https://docs.google.com/document/d/1RUtU3_3tIFGmgyXJ09yzoc-UlmNYH3vVLrAd5Y83wIs

## Why it exists

Recurring payments and card-on-file transactions break when a registered card is canceled — even if the customer already has a new active card. Joker tracks the succession chain of customer cards so that:

- **ABU** (Automatic Billing Updater) can update card numbers stored at merchants
- **Digital wallets** can update tokens when a card changes

## How it works

Joker listens for card activation and cancellation messages and emits `CARD-CHAIN/NEW-EVENT` messages describing what happened to the chain.

It fetches previous card data from **crebito** when needed (e.g., to build a chain retroactively).

## Chain

A **chain** is an ordered sequence of cards linked to each other. Each customer can have multiple chains — one per chain type.

### Chain Type

A chain type is a composite key that identifies the category of chain:

```
<category>-card-<form>-<features>[-<label>]
```

| Field | Values |
|---|---|
| **category** | `primary`, `additional`, `company` |
| **form** | `physical`, `virtual` |
| **features** | `combo` (credit+debit capable), `credit-only`, `debit-only` |
| **label** (optional) | e.g., `netflix`, `online-purchases` |

**Examples:**
- `primary-card-physical-combo`
- `primary-card-virtual-credit-online-purchases`
- `additional-card-physical-debit`
- `company-card-virtual-combo-netflix`

> A card that _can_ activate debit but has only credit active is still a **combo** card. `credit-only` / `debit-only` only applies when debit can never be enabled (common in 🇲🇽).

## Chain Events

| Event | When |
|---|---|
| `chain-created` | First card of a chain type is activated for a customer, or a new chain is started after a fraud closure |
| `chain-updated` | A new card is activated and linked to the previous one in the chain |
| `chain-suspended` | A card in the chain is canceled |
| `chain-closed` | The previous card was frauded — a new chain starts instead of linking |

## Fraud detection

Before linking a newly activated card to the previous one, joker checks if the previous card was frauded:

### Physical cards
- Cancel reason is `fraud-confirmed` **or** `fraud-risk`

### Virtual cards
- Cancel reason is `fraud-confirmed` or `fraud-risk`
- **OR** the card has a credit chargeback with `fraud` reason on a **recurring purchase** (subscriptions)
  *(This chargeback check is only performed in 🇧🇷)*

> This virtual card exception exists because customers sometimes cancel the card before opening a chargeback, so the cancel reason alone doesn't reflect the fraud.

## Internal data model

| Entity | Description |
|---|---|
| **Customer** | Aggregates all chains for a customer. Holds `credit-account-id` (used to query chargebacks). |
| **Chain** | Aggregates events of the same chain type. Can be `open` or `closed`. |
| **Chain State** | Mutable object — tracks the last event, last card, and open/closed status. The active chain always has status `open`. |
| **Card** | Simple representation of a card within a chain. |
| **Event** | Immutable record of what happened to the chain. A chain is essentially a sequence of events. |

## Edge cases

- **Reactivated cards:** If a canceled card is reactivated, joker ignores it — cards are inserted in the chain only once.
- **Multiple chains of the same type:** Happens when a card is frauded. The frauded chain is closed and a new one starts for the same type.
- **Retroactive chain building:** If joker has no chain for a given type when a second card is activated, it fetches the previous card from crebito and builds the chain with both cards already linked.
