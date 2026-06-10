# abu

**Automatic Billing Updater (ABU)** — Visa/Mastercard programs that push **updated card credentials** to merchants when a card is replaced, tied to **card chains** and token updates.

## Repository

- [https://github.com/nubank/abu](https://github.com/nubank/abu)

## ISA

- [https://backoffice.ist.nubank.world/isa/#/services/abu/overview](https://backoffice.ist.nubank.world/isa/#/services/abu/overview)

## Role in card creation ecosystem

- Not a “creation” service per se, but **downstream of issuance**: when customers get new PANs, ABU keeps **recurring** charges working. **joker** chains exist partly to support ABU + wallet continuity. Shuffle may expose **ABU** widgets via **mr-shuffle** experiments.

## See also

- `embossing.md` (ABU mention)
- `card-hierarchy.md`
- `services/joker.md`

