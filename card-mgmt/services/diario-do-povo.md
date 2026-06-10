# diario-do-povo

**Canceled-card reporting artifact** — internal design notes reference storing **reports** (e.g. **canceled-card-receipt** type) in **S3**, tied to **customer-id** and triggered from **card widget** actions when a card is **canceled** (support / ops visibility).

## Repository

- https://github.com/nubank/diario-do-povo

## ISA

- https://backoffice.ist.nubank.world/isa/#/services/diario-do-povo/overview

## Role

- Not a card **issuer**, but part of the **card ops** story: evidence and audit around **canceled** cards for CX/investigation.

## See also

- `services/mr-shuffle.md` (Cards widget context)
