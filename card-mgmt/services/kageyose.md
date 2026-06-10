# kageyose

**Customer-scoped card list API** — returns a customer’s **cards** (metadata) for a shard; used by BFFs, tools, and **data** flows that need “all cards for customer X”.

## Repository

- https://github.com/nubank/kageyose

## ISA

- https://backoffice.ist.nubank.world/isa/#/services/kageyose/overview

## Role in card creation / ops

- **mr-shuffle** reissue flows call kageyose; **radio-peao** uses **`GET` customer-cards** bookmark to assemble access-report data.
- Response shape is shared across consumers (see e.g. **urgot** wire comments mirroring `kageyose.wire.out.customer-card`).

## See also

- `services/mr-shuffle.md`
- `services/radio-peao.md`
