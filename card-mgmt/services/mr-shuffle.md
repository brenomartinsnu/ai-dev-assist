# mr-shuffle

**Shuffle widget provider for the Cards team** — BFF for **agent-facing card operations** in Nubank’s **Shuffle** (support platform): Cards widget, card quotas, tokenization widget, ABU widget, delivery/logistics widgets, MCP tools for agents/AI flows.

## Repository

- https://github.com/nubank/mr-shuffle

## ISA

- https://backoffice.ist.nubank.world/isa/#/services/mr-shuffle/overview

## What it does

- Orchestrates HTTP to **crebito**, **kageyose**, and other card/logistics services; **sharded**, Clojure + **ui-server** (SSR) for widgets.
- **Cards widget:** reissue, cancel-all, card data export (PCI-gated), etc. Reissue path historically: **mr-shuffle → kageyose** (see internal RFCs on Reaper/cancellation edge cases).
- **Experiments:** widgets gated via Cockpit/Abrams (e.g. `shuffle-cards-widget`, `shuffle-tokenization-widget`, `shuffle-abu-widget`, `shuffle-widget-card-quota`).
- **MCP:** exposes tools (e.g. logistics) under `POST /mcp` for agent workflows.

## Ownership note

- Primary engineering often **Cards / ICORE** alignment for the Cards widget; platform patterns shared with other widget providers.
