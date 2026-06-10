# chico-xavier

**Mastercard ALM (Account Lifecycle Management)** integration — talks to Mastercard over **JWE**-encrypted payloads for **product graduation** (e.g. card category upgrade/downgrade such as Gold → Platinum).

## Repository

- https://github.com/nubank/chico-xavier

## ISA

- https://backoffice.ist.nubank.world/isa/#/services/chico-xavier/overview

## What it does

- Uses **Mastercard encryption keys** (public PEM for outbound encrypt, plus key rotation via **nu-keysets**). Keys expire and must be renewed on a schedule (see Card Creation Confluence: *Renew Mastercard Encryption Keys - Chico Xavier (ALM)*).

## Card-creation link

- **Product changes** on an existing card line intersect issuance/eligibility and network reporting — adjacent to pure “new PAN” creation but part of the same cards domain.
