# abu

**Automatic Billing Updater (ABU)** — Visa/Mastercard programs that push **updated card credentials** to merchants when a card is replaced, tied to **card chains** and token updates.

## Repository

- [https://github.com/nubank/abu](https://github.com/nubank/abu)

## ISA

- [https://backoffice.ist.nubank.world/isa/#/services/abu/overview](https://backoffice.ist.nubank.world/isa/#/services/abu/overview)

## Role in card creation ecosystem

- Not a “creation” service per se, but **downstream of issuance**: when customers get new PANs, ABU keeps **recurring** charges working. **joker** chains exist partly to support ABU + wallet continuity. Shuffle may expose **ABU** widgets via **mr-shuffle** experiments.

## What it does / stores

- Consumes card lifecycle signals and, per customer+chain-type, decides (via a **chain-option** entity: `opted-in?`) whether events actually get emitted to Mastercard for that chain.
- Each qualifying lifecycle change becomes an **`event`** (Datomic entity): `:event/id`, `:event/action` (`new`, `replacement`, `opt-out`, ...), `:event/card`, `:event/parent-card`, `:event/status` — progresses `pending -> :event.status/s3 -> :event.status/file` as the event is turned into a file line and then bundled into a sent file. See `abu.controllers.event`, `abu.controllers.chain`, `abu.controllers.opt`.
- Reason-code mapping from action to the Mastercard R274 reason code (`N`=new, `R`=replacement, `C`=closed, `O`=opt-out/delete, ...) lives in `abu.logic.file` (`abu-action->reason-code` / `file-type->reason-code`), driven by `:event/action` (Datomic enum, `abu.models.event`, 6 values incl. `:event.action/close` -> `C` and `:event.action/opt-out` -> `O`).
- **Code O deletes the PAN chain at Mastercard, irrecoverable, and has a much higher error rate than C** (12-month prod data: O = 1.93M sent / 4.59% error vs C = 30.9M sent / 0.0000065% error). But **closing a chain (C) also makes Mastercard revoke that chain's wallet tokenizations (Apple Pay/etc.) — this cannot be suppressed**, so C is only safe to send when the card is genuinely canceled, not as a generic "opted-out" signal.

### One chain per card for opted-out customers (CARD-1764/1765/1766, PR #849)

Opted-in customers keep the existing model: a chain persists across reissues (`replacement`/`R`, token-safe — Mastercard just repoints the PAN, no token revocation).

Opted-out customers get **no chain continuity at all**: every card is registered (`N`) when created and closed (`C`) when canceled, with no exceptions — including reissues. `replace-card!` (`chain.clj`) branches on `chain-option/opted-in?`: if opted-in, same `replacement`/R as before; if opted-out, it closes the previous card (`C`) and registers the new card from scratch (`N`), as if it were a brand-new chain. `new-card!`/`close-card!` don't need to branch — they already behave identically regardless of opt status (register on creation, close on cancellation), only `replace-card!` has opt-status-dependent behavior, since only it has to choose between continuity (R) and no-continuity (C+N).

- `new-card!`/`close-card!` (`chain.clj`) no longer gate on `opted-in?` — opted-out customers' cards are registered/closed through their normal lifecycle instead of being silently dropped.
- `opt-out-card!` is removed. It used to fire a `close` (C) event at the moment of opt-out for whatever card was in use — since C revokes tokens, this killed tokens on cards that were still active and never actually canceled. That bug is what prompted this redesign.
- `opt-in-card!` renamed `register-card!` (it only ever sent a registration/`new` event) and reused by both the opt-in and opt-out legacy backfills (`legacy.clj`) — an opted-out customer's unregistered card needs registering, not closing.
- `:event.action/opt-out` / reason code `O` has no new callers left but was kept (not deleted) since historical `O` events may still need to round-trip through file generation.

### Opt-out migration backfill (CARD-1756/1758, PR #848, separate from the above)

One-time backfill for the **historical population**: cards created *before* the fix above shipped, belonging to customers who were already opted-out, that never got an ABU registration (silently dropped by the old `opted-in?` gate). `close-opted-out-customer-card!` (`chain.clj`) sends `N` (not `C`) when the card has no ABU history yet or its last action was `opt-out`; no-op otherwise. Driven by a Databricks-extracted population (`abu__account_on_abu_history`, `account__on_abu = false`, with an approved credit/debit transaction in the last 12 months) fed through the `close-cards-for-opted-out-customer` migration-id / admin endpoint. Independent of the go-forward fix — stays reachable via its own dedicated migration consumer/admin endpoint regardless of what new-card!/opt-out-card! do.
- Rollout: batch by day/shard (BR has 20 shards) to avoid spiking the daily R274 file (`s3_file.clj:115-141`); monitor T275 confirmation parsing per reason code.

## File generation (R274/T275)

- Per-event fixed-width **record lines** are built in `abu.controllers.lines` (`new-line!`) — chooses the ICA by card BIN (`s3-lines-by-ica`) or the shard default ICA (`s3-lines`) — and written to an intermediate **S3 “lines” store**, keyed by `event-id`, under `{env}/{shard}/lines/[{ica}/]{as-of}`. Writing a line flips the event to `:event.status/s3` (`abu.controllers.event/update-event-on-s3!`).
- Daily/on-demand, `abu.controllers.s3-file` (`new-file-decoded!`) and its per-ICA sibling `s3-file-by-ica` fetch all pending lines for `as-of`, build the file **header** (`abu.logic.file/build-header`: `H` + ICA + fillers + reason-code-of-file-type) and concatenate header+records with `\r` separators, using the `AbuFile$` Scala module (`scala_ipm.io`) to write the fixed-width blocks.
- Filename convention (`abu.logic.file/abu-filename`): `R274`/`R278`(test) + ICA + julian day of `as-of` + 2-digit cycle (shard index + cycle-increment). Confirmation files come back from Mastercard as `T275` (`R278`/`T279` in the MTF test environment).
- The generated file is stored to S3 (`store-file-on-s3!`) under a bucket prefix `projects/logs/{env}/{aws-account-alias}/nu-tick-tock/abu-files/{year}/{month}/{day}`, the `abu-file` Datomic entity is inserted (`abu.db.datomic.abu-file`, with `:abu-file/type` = `:abu-file.type/blank` or `:abu-file.type/initial`), and every bundled event is batch-updated to `:event.status/file` (`c-event/update-events-w-abu-file!`).
- Finally the file path is handed to **Brasero** for actual transfer to Mastercard: `abu.diplomat.producer/brasero-send-file!` produces onto the `:brasero/send-file`-style topic with `subtopic :abu`; Brasero's own fixtures (`brasero/test/.../transfer.clj`) show the same bucket-path convention and a `status-update-message` callback flow (received/sent/etc. statuses land back under the same S3 prefix by status folder).
- Files can optionally be **encrypted** before transfer via `common-abu.components.abu-file-handler` (`create-file!`/`upload-file!` to the Mastercard MIP host/port); a mock component (`abu-file-handler-mock`) exists for tests.
- Confirmation processing / opt-out endpoints are exposed over HTTP in `abu.service` (`abu.service.clj`) for manual/operational triggers (e.g. the migration endpoints CARD-1756/1758 are adding).

## See also

- `embossing.md` (ABU mention)
- `card-hierarchy.md`
- `services/joker.md`

