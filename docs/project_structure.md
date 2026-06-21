# LedgerFlow — Architecture & Project Structure Guide

> **Audience:** Engineers working on this codebase.
> **Scope:** Monorepo layout, service boundaries, domain responsibilities, and folder organization.

---

## Table of Contents

1. [Domain Boundaries](#1-domain-boundaries)
2. [Repository Layout](#2-repository-layout)
3. [Shared Package](#3-shared-package)
4. [Service Structure](#4-service-structure)
5. [Folder Responsibilities](#5-folder-responsibilities)
6. [Database Ownership](#6-database-ownership)
7. [Event Communication](#7-event-communication)
8. [Naming Recommendations](#8-naming-recommendations)

---

## 1. Domain Boundaries

### Commerce

Commerce owns the business side of a transaction — products, pricing, inventory, coupons, checkouts, and orders. It understands *what* is being purchased. It has no knowledge of how money moves; it publishes the fact that a checkout requires payment and waits for a confirmation event.

### Payment

Payment owns the mechanics of moving money — payment sessions, PSP abstraction, attempt state machines, idempotency, retries, and refunds. It knows nothing about products or orders. When it captures a payment or processes a refund, it publishes an event and its responsibility ends.

### Ledger

Ledger maintains an immutable accounting record. It applies double-entry bookkeeping to every money movement it receives via events. It also manages wallet balances and runs reconciliation to detect drift against simulated PSP data. Ledger entries are never modified — corrections are new entries.

### Notification

Notification is a pure consumer. It listens to events from all other services and dispatches emails or SMS messages. It contains no business logic and initiates no state changes in other services.

### Shared

The `shared/` package holds cross-cutting concerns: Kafka event schemas (the contracts between services), a common database base, and shared utilities. It contains no service-specific business logic.

---

## 2. Repository Layout

```
LedgerFlow/
├── docs/                        # Documentation
├── infra/                       # Infrastructure config (Docker Compose, Kafka, Postgres)
│   ├── kafka/
│   └── postgres/
├── services/                    # Independently runnable service applications
│   ├── commerce/
│   ├── payment/
│   ├── ledger/
│   └── notification/
└── shared/                      # Cross-service shared packages
    ├── events/
    ├── models/
    └── utils/
```

Each directory under `services/` is an independently runnable application with its own `Dockerfile` and dependency manifest. The `shared/` package is installed as a local dependency in each service. Infrastructure definitions live entirely in `infra/` — no Python code lives there.

---

## 3. Shared Package

```
shared/
├── events/                      # Kafka event schemas, organized by producing service
│   ├── commerce/
│   ├── payment/
│   └── ledger/
├── models/                      # Common database base class
└── utils/                       # Logging, configuration, exceptions
```

Event schemas live in `shared/` because they are the contracts between services. A producing service and every consuming service must agree on the same schema. Placing them here makes that agreement explicit and keeps drift detectable at a single location.

`shared/` must never import from any service. It contains no FastAPI applications, no migrations, and no service-specific domain logic.

---

## 4. Service Structure

All four services share the same internal folder organization. The layers are identical across services; only the domain concepts within each layer differ. This makes navigating any service immediately familiar.

### Standard layout (Commerce, Payment, Ledger)

```
services/{name}/
├── alembic/                     # Database migrations owned by this service
│   └── versions/
└── app/
    ├── api/                     # HTTP boundary
    │   └── v1/
    ├── domain/                  # Domain models, enums, exceptions, value objects
    │   └── models/
    ├── repositories/            # Data access
    ├── services/                # Business logic
    ├── schemas/                 # Request and response DTOs
    │   ├── requests/
    │   └── responses/
    ├── events/                  # Kafka boundary
    │   ├── producers/
    │   └── consumers/
    ├── workers/                 # Background processes
    ├── infrastructure/          # External adapters (database, Kafka, PSP)
    └── logging/
```

### Notification layout

Notification has no HTTP API and no database, so it omits `api/`, `schemas/`, `repositories/`, and `alembic/`. Its `events/` folder contains only consumers.

```
services/notification/
└── app/
    ├── domain/
    ├── services/
    ├── events/
    │   └── consumers/
    ├── workers/
    ├── infrastructure/
    └── logging/
```

---

## 5. Folder Responsibilities

| Folder | Responsibility |
|---|---|
| `api/` | HTTP boundary. Receives requests, delegates to services, returns responses. |
| `api/v1/` | Version-namespaced routers. Future API versions add a `v2/` without disturbing `v1/`. |
| `domain/` | Core concepts: ORM models, enums, exceptions, value objects. No I/O. |
| `domain/models/` | ORM model definitions for tables owned by this service. |
| `repositories/` | All database queries. One repository per aggregate. |
| `services/` | Business logic and use case orchestration. |
| `schemas/` | Data transfer objects scoped to the HTTP layer. |
| `schemas/requests/` | Inbound payload shapes. |
| `schemas/responses/` | Outbound payload shapes. |
| `events/producers/` | Constructs event payloads and writes them to the outbox. Never publishes to Kafka directly. |
| `events/consumers/` | Deserializes incoming Kafka messages and calls service methods. |
| `workers/` | Background processes: outbox relay, consumer runner, retry scheduler, etc. |
| `infrastructure/` | Adapters to external systems: database session factory, Kafka client, PSP client. |
| `infrastructure/psp/` | PSP abstraction (Payment service only). Abstract interface plus mock implementation. |
| `logging/` | Logging setup for this service. |
| `alembic/versions/` | Migration scripts. Scoped exclusively to this service's own tables. |
| `tests/unit/` | Isolated tests with all infrastructure mocked. |
| `tests/integration/` | Tests against real infrastructure (database, HTTP). |
| `tests/e2e/` | Full within-service workflow tests. |

---

## 6. Database Ownership

The physical database is shared across services, but ownership is logical. Each service owns a distinct set of tables and is the only service permitted to write to them. Cross-service data needs are satisfied through REST calls or Kafka events — never through shared table access or cross-service joins.

Tables are name-prefixed by service to prevent collisions and make ownership unambiguous. Each service manages its own migrations in its own `alembic/` directory, scoped only to its own tables.

---

## 7. Event Communication

Events flow from producing services to consuming services through Kafka. Event schemas are defined in `shared/events/`, organized by producing service. This single source of truth prevents schema drift between producers and consumers.

Producers never publish to Kafka directly from within a service call. Instead, they write events to a local outbox table as part of the same database transaction as the business mutation. A background worker in `workers/` relays outbox rows to Kafka asynchronously. This is the transactional outbox pattern — it ensures no event is lost due to a crash between a database commit and a Kafka publish.

Consumers are responsible for deserializing messages and calling the appropriate service method. Because Kafka delivers at least once, consumers must be written to handle duplicate delivery gracefully.

---

## 8. Naming Recommendations

- **Service directories:** match the domain name (`commerce`, `payment`, `ledger`, `notification`).
- **Folder names:** lowercase, singular where natural (`domain/`, `services/`, `repositories/`).
- **Domain model classes:** singular PascalCase noun (`PaymentSession`, `LedgerEntry`).
- **Service classes:** domain noun + `Service` suffix (`CheckoutService`, `LedgerService`).
- **Repository classes:** domain noun + `Repo` suffix (`PaymentSessionRepo`, `WalletRepo`).
- **Event classes:** aggregate noun + past-tense verb (`PaymentCaptured`, `CheckoutCompleted`).
- **Table names:** service-prefixed snake_case (`payment_sessions`, `ledger_entries`, `commerce_checkouts`).
- **Primary keys:** UUIDs, generated by the application.
- **Monetary values:** integers in the smallest denomination (cents, paise). Never floats.
- **Timestamps:** UTC with timezone.
