# kuchiyose

**Main orchestrator for card creation and reissue flows** — coordinates **card requests** in Datomic, drives **PAN prep → create → embossing/packaging** via Kafka, and exposes **admin/ops HTTP** plus one **arnaldo** entry route.

## Repository

- [https://github.com/nubank/kuchiyose](https://github.com/nubank/kuchiyose)

## ISA

- [https://backoffice.ist.nubank.world/isa/#/services/kuchiyose/overview](https://backoffice.ist.nubank.world/isa/#/services/kuchiyose/overview)

> Topic names below are **logical keys** from `kuchiyose.diplomat.{consumer,producer}` (e.g. `:card-creation/card-to-request`). Deployed Kafka names follow Nubank’s mapping from these keys—confirm in ISA or env-specific config if you need the literal string.

---

## HTTP API

From `kuchiyose.service/routes`.

### Public / discovery


| Method | Path                   | Notes                                                               |
| ------ | ---------------------- | ------------------------------------------------------------------- |
| `GET`  | `/api/version`         | Version                                                             |
| `GET`  | `/api/discovery`       | Hypermedia entrypoint (currently empty map in code)                 |
| `GET`  | `/api/admin/discovery` | Admin discovery (`auth/admin` or `auth/trusted`) — lists URIs below |


### Card flow (integration)


| Method | Path                     | Auth      | Notes                                                                  |
| ------ | ------------------------ | --------- | ---------------------------------------------------------------------- |
| `POST` | `/api/cards/pre-request` | `arnaldo` | **Pre card request** — starts pre-request flow (`PreCardRequest` body) |


### Admin / operations


| Method   | Path                                             | Auth (scopes)                           | Notes                                                  |
| -------- | ------------------------------------------------ | --------------------------------------- | ------------------------------------------------------ |
| `GET`    | `/api/admin/customers/:id/card-requests`         | `cards-admin`, `cards-general`          | All card requests for customer                         |
| `POST`   | `/api/admin/customers/:id/manual-card-request`   | `cards-admin`, `cards-general`          | Manual **physical** card request                       |
| `POST`   | `/api/admin/cards/:id/republish-card-to-prepare` | `cards-admin`, `cards-general`          | Republish **card-to-prepare** when status is requested |
| `POST`   | `/api/admin/cards/:id/card-request-to-created`   | `cards-admin`                           | Force transition to **created** + `finished-at`        |
| `DELETE` | `/api/admin/cards/:id/cancel`                    | `cards-admin`                           | Cancel request not yet created / not already canceled  |
| `PUT`    | `/api/admin/cards/:id/update-status/:status`     | `cards-admin`                           | Manual status update                                   |
| `POST`   | `/api/admin/fix-stuck-card-requests`             | `cards-admin`, `cards-general`, `tempo` | Fix stuck “requested” without `finished-at`            |


---

## Kafka — consumed topics

Handlers in `kuchiyose.diplomat.consumer/settings`:


| Topic key                                            | Purpose (handler)                                                     |
| ---------------------------------------------------- | --------------------------------------------------------------------- |
| `:card-creation/card-to-request`                     | **request-card!** — main path from upstream “card to request” message |
| `:card-creation/card-prepared`                       | PAN/dataprep ready — **card-prepared-with-applications!**             |
| `:card-creation/card-created`                        | Card exists in SoT — **card-created!**                                |
| `:card-creation/pre-created-card-to-request`         | Pre-requested flow — **continue-pre-card-requested-creation!**        |
| `:kuchiyose-internal/ensure-card-prepared`           | Scheduled/delayed **ensure card prepared**                            |
| `:kuchiyose-internal/fix-card-request-stuck`         | Fix one stuck **card-requested**                                      |
| `:card-creation-internal/pre-created-card-to-create` | **pre-created-card-to-create!**                                       |


Also wired (auth/experiment): `:token-revoked`, `:all-tokens-revoked`, `:experiment-updated` (see consumer ns).

---

## Kafka — produced topics

Producer schema keys in `kuchiyose.diplomat.producer/settings` + `produce!` usages:


| Topic key                                    | Typical use                                                                      |
| -------------------------------------------- | -------------------------------------------------------------------------------- |
| `:card-creation/card-to-prepare`             | After request validated — send work to dataprep/PAN (**partition**: customer-id) |
| `:card-creation/card-to-create`              | Issue card in **crebito** path (**edn+secure**)                                  |
| `:card-creation/card-to-request`             | Emit **CardToRequest** (e.g. manual card) (**edn+secure**)                       |
| `:card-creation/card-creation-completed`     | Completion notification (**edn+secure**)                                         |
| `:card-packaging/prepare-package`            | Welcome kit / packaging (**edn+secure**)                                         |
| `:card/update-parameters`                    | Product type / personalization updates (**hitaiate**-side parameters)            |
| `:kuchiyose-internal/ensure-card-prepared`   | Delayed prepare (optional **deliver-at**, no jitter)                             |
| `:kuchiyose-internal/fix-card-request-stuck` | Internal fix message `{ :card-id }`                                              |


---

## Role in the platform

- **Creation:** ties eligibility, **pandora** (PAN), **hitaiate** (parameters), **crebito**, embossing handoff, packaging.
- **Reissue:** coordinates with **arnaldo** and downstream services.
- **Pre-request:** `POST /api/cards/pre-request` is the **arnaldo** integration surface.

## See also

- `card-creation.md`

