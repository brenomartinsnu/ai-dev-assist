# gilfoyle

Owned by the Authorizer squad. Keeps `common-pan-mapping` (the PAN ↔
card/customer mapping, DynamoDB-backed) up to date and exposes admin
lookups on top of it.

## Role

- "Service responsible for keeping the pan-mapping updated."
- Consumed by Rivendell's dataprep flow (`get-pan-clear!` — Rivendell's
  `prepare_card.clj` calls this via the shared `pan-mapping` component, not a
  direct HTTP call you'll see logged the same way as its other dependencies —
  it's a DynamoDB read, so it won't show up as an `out-request`/`out-response`
  pair in Alexandria the way Crebito/Pinboard/Hitaiate calls do).

## Useful admin endpoint

```bash
nu-<country> ser curl get <shard> gilfoyle /api/admin/card/<card-id>/get-pan-clear --cid <cid> --env prod
```
Requires the **`pci-pan`** scope (`nu sec scope add <user> pci-pan --use-iga
--reason "..."`), not `cards-admin`. Returns:
```json
[{"pan_clear": "...", "shard": "s18", "card_id": "...", "customer_id": "..."}]
```
- **`pan_clear` is a real secret — never print it in chat or logs.** Only
  report metadata (count of entries, presence/absence of an `application`
  tag, shard).
- A single PAN entry with **no `application` field** is normal for a
  `:combo` (credit+debit) card — Rivendell's
  `pan-with-default-application` explicitly handles this by defaulting the
  application from the card's profile (`:combo` → `:credit+debit`). Don't
  read a missing `application` tag as a data-quality signal on its own;
  confirmed identical between an affected and a control card in the
  CSEO-6946 investigation.
