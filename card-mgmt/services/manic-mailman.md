# manic-mailman

**Card lifecycle notifications** — single place for **email + push** (and related **feed**) logic for cards. It **consumes** domain events on Kafka, loads extra data over HTTP when needed, applies rules (locale, experiments, “ignore old messages”), then **produces** to the central **[notification](https://github.com/nubank/notification)** service.

Official README: *“Having a single and centralized place to have all the card life cycle's related communication logics.”*

## Repository

- [https://github.com/nubank/manic-mailman](https://github.com/nubank/manic-mailman)

## ISA

- [https://backoffice.ist.nubank.world/isa/#/services/manic-mailman/overview](https://backoffice.ist.nubank.world/isa/#/services/manic-mailman/overview)

## Miro (journeys & templates)

- [https://miro.com/app/board/uXjVOBaXGxQ=/](https://miro.com/app/board/uXjVOBaXGxQ=/) — physical/virtual flows; **add new notifications here** when extending journeys.

---

## Downstream contract (notification service)

From the repo README — messages use **logical** topic keys; templates live in Template Studio.


| Produced topic key           | Purpose                                                                               |
| ---------------------------- | ------------------------------------------------------------------------------------- |
| `:deliver-push-notification` | Push — `flow-id`, `target-app`, `template-name`, `contact-id` (customer), `variables` |
| `:deliver-email`             | Email — `flow-id`, `template-name`, `contact-id`, `variables`                         |


Both are `**edn+secure`** in producer settings.

---

## HTTP API

`manic-mailman` is **not** a customer-facing BFF: HTTP is **ops/discovery only**.


| Method | Path                   | Notes                                         |
| ------ | ---------------------- | --------------------------------------------- |
| `GET`  | `/api/version`         | Service version                               |
| `GET`  | `/api/discovery`       | Hypermedia (empty endpoint map in code today) |
| `GET`  | `/api/admin/discovery` | `auth/admin` or `auth/trusted` — same pattern |


All behavior is **Kafka-driven**.

---

## Kafka — consumed topics

Logical keys from `manic_mailman.diplomat.consumer/settings`. `**cards/feature-changed`** uses a wrapper that **drops very old messages** (config: hours threshold).


| Topic key                                                | What triggers comms (summary)                                                         |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `:card-tracking/notification-new-event`                  | Card tracking events                                                                  |
| `:card-tracking-status-changed`                          | Tracking status → factory-in-transit, delivered, etc.                                 |
| `:additional-cards/card-tracking-status-changed`         | Additional card tracking                                                              |
| `:card-delivery-problem-reminder`                        | Reminder for delivery problem flow                                                    |
| `:carrier-in-update-status`                              | Carrier inbound file — `:delivery-problem`, `:card-in-return`, `:destroyed-object`, … |
| `:cards/feature-changed`                                 | Debit path — `:activated`, `:block-reason-added`, `:canceled`                         |
| `:cards/credit-feature-changed`                          | Credit activated → activation + VC upgrade reminder scheduling                        |
| `:additional-cards/credit-feature-changed`               | Additional card credit activation                                                     |
| `:additional-cards/feature-changed`                      | Additional card block notifications                                                   |
| `:virtual-card/available`                                | VC available + schedule creation reminder                                             |
| `:virtual-card/cancelled`                                | VC cancelled comms                                                                    |
| `:virtual-card/first-created`                            | First VC onboarding                                                                   |
| `:cards/virtual-card-expiring-reminder`                  | Expiring VC reminder                                                                  |
| `:abu/chain-opted-out`                                   | ABU opt-out email                                                                     |
| `:notify-reissue-expiring-card`                          | Expiring plastic → reissue nudges                                                     |
| `:card-reports/created`                                  | Card report PDF ready (S3 paths + password)                                           |
| `:card-product/category-update-requested`                | Product/category change comms                                                         |
| `:card-product/force-cancellation-warning`               | Force-cancel warning                                                                  |
| `:card-product/force-cancellation-succeeded`             | Force-cancel succeeded                                                                |
| `:delivery-platform/new-event`                           | Delivery platform lifecycle                                                           |
| `:tokenization/authentication-request`                   | Wallet auth (MDES-style path)                                                         |
| `:tokenization/authentication-code-request`              | Email auth code for tokenization                                                      |
| `:tokenization/authentication-code-mobile-request`       | Mobile auth code                                                                      |
| `:tokenization/request`                                  | Tokenization request                                                                  |
| `:tokenization/completed`                                | Tokenization completed                                                                |
| `:tokenization/pending-notification`                     | Pending tokenization nudge                                                            |
| `:tokenization/unused-notification`                      | Unused token nudge                                                                    |
| `:manic-mailman-internal/card-activation-reminder`       | Scheduled activation reminder                                                         |
| `:manic-mailman-internal/virtual-card-reminder`          | Scheduled VC reminder                                                                 |
| `:manic-mailman-internal/virtual-card-upgrade-reminder`  | VC upgrade reminder                                                                   |
| `:manic-mailman-internal/virtual-card-creation-reminder` | VC creation reminder                                                                  |
| `:manic-mailman-internal/card-tracking-delivery-problem` | Delayed delivery-problem comms                                                        |


Also: `:experiment-updated`, `:token-revoked`, `:all-tokens-revoked` (auth/experiment plumbing).

---

## Kafka — produced topics

From `manic_mailman.diplomat.producer`:


| Topic key                    | Role                                                                                                                       |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `:deliver-email`             | Hand off to **notification** (email)                                                                                       |
| `:deliver-push-notification` | Hand off to **notification** (push)                                                                                        |
| `:facade/feed-updated`       | In-app **feed** updates (`:subtopic :notification`, async) after some card events                                          |
| `:manic-mailman-internal/*`  | **Delayed** messages (`:deliver-at`) — activation reminder, VC reminders, VC creation reminder, delivery-problem follow-up |


Internal producer schemas include `CardActivationReminderMessage`, `VirtualCardReminder`, `VirtualCardUpgradeReminder`, `VirtualCardCreationReminder`, `CardTrackingDeliveryProblem`.

---

## How to read the codebase


| Area                       | Where                                                  |
| -------------------------- | ------------------------------------------------------ |
| Event → handler map        | `src/manic_mailman/diplomat/consumer.clj` (`settings`) |
| Email/push + scheduling    | `src/manic_mailman/diplomat/producer.clj`              |
| Business rules per event   | `src/manic_mailman/controllers/`**                     |
| Wire schemas               | `src/manic_mailman/wire/**`                            |
| Template / journey catalog | Repo **README.md** (large, country-specific tables)    |


---

## Neighbors

- **notification** — actually sends email/push to customers.
- **faramir** — produces several `tokenization/`* topics that **manic-mailman** consumes for wallet comms.
- **Card tracking / delivery / crebito** — upstream of `card-tracking`* and feature-changed events.

## See also

- `services/faramir.md` (tokenization topics)
- `delivery.md`, `embossing.md` (physical card logistics context)

