> **Note:** This is v1 of the README. It will be updated as the project evolves.

---

# LedgerFlow

LedgerFlow is a distributed payment processing platform built to simulate how money moves through a modern commerce system — from a customer initiating checkout to funds being recorded in an immutable ledger, with retries, refunds, and reconciliation in between.

It is not a payment gateway, a Stripe clone, or a banking system. It is a working model of the internal machinery that such systems are built on.

---

## Why This Project Exists

Most engineers working in payments interact with one slice of the system — a checkout flow, a webhook handler, a ledger query. The goal of this project is to model the full flow end to end, with the problems that make payment systems hard:

- What happens when a payment attempt fails halfway through?
- How do you guarantee that a Kafka event is published if the service crashes after a database commit?
- How do you record money movement such that the accounting is always correct and auditable?
- How do you reconcile what your system believes happened with what the PSP reports?
- How do you make an API idempotent so that retrying a request never double-charges a customer?

These are not hypothetical problems. They are the class of problems that payment engineers solve daily. LedgerFlow is built to demonstrate working answers to all of them.

---

## Business Workflow

The full lifecycle of a transaction through LedgerFlow:

```
1.  Customer initiates checkout
      └─ Commerce creates a Checkout with items and calculates total price
      └─ Inventory is reserved (not committed yet)

2.  Checkout is confirmed
      └─ Commerce creates an Order
      └─ A CheckoutCompleted event is published to Kafka

3.  Payment session is created
      └─ Payment Service consumes CheckoutCompleted
      └─ A PaymentSession is created, linked to the checkout amount

4.  Payment is attempted
      └─ Payment Service submits the attempt to a simulated PSP
      └─ On success: PaymentCaptured event is published
      └─ On failure: attempt is recorded, retry is scheduled if eligible

5.  Payment captured
      └─ Commerce consumes PaymentCaptured → inventory reservation is committed
      └─ Ledger consumes PaymentCaptured → debit/credit entries are recorded
      └─ Notification consumes PaymentCaptured → confirmation sent to customer

6.  Payment retry (if initial attempt failed)
      └─ Retry worker picks up scheduled retry after backoff delay
      └─ New PaymentAttempt is created and submitted
      └─ Continues until success or max attempts exhausted

7.  Refund (if initiated)
      └─ Refund is submitted to simulated PSP
      └─ RefundCaptured event is published
      └─ Ledger records reversal entries
      └─ Notification informs the customer

8.  Reconciliation
      └─ Ledger service compares internal entries against simulated PSP settlement report
      └─ Gaps and discrepancies are flagged as reconciliation records
```

---

## Core Concepts

**Checkout**
A transient record representing a customer's intent to purchase. It holds items, quantities, applied coupons, and a calculated total. It is not an order — it only becomes one when payment succeeds. Inventory is reserved at checkout time to prevent overselling, but not committed until payment is confirmed.

**Order**
A committed record of a completed purchase. An order is created when a checkout completes. It is the business confirmation that the transaction happened and inventory has been consumed.

**Payment Session**
A container for all payment activity related to a single checkout. One checkout maps to one payment session. The session tracks the overall payment status (pending, captured, failed, refunded) and holds the collection of attempts made against it.

**Payment Attempt**
A single request to a PSP to charge a customer. One payment session may have multiple attempts — for example, if the first attempt times out, a second attempt is made after a backoff delay. Each attempt is a separate, immutable record.

**Ledger**
An append-only accounting log. Every money movement — capture, refund, reversal — is recorded as a pair of entries: one debit and one credit. Entries are never modified. If a correction is needed, a new correcting entry is appended. This models the fundamental principle of double-entry bookkeeping.

**Wallet**
An account within the ledger that tracks the running balance for a participant (customer, merchant, platform). A wallet's balance is derived from its ledger entries — it is not stored independently unless cached for performance.

**Refund**
A reversal of a captured payment, either partial or full. A refund is a first-class entity: it has its own state machine, its own PSP interaction, and produces its own ledger entries that reverse the original capture entries.

**Reconciliation**
The process of comparing what the internal ledger believes happened against what the PSP reports. Discrepancies — missing captures, unexpected refunds, amount mismatches — are recorded as reconciliation records for investigation. This models the settlement process that real payment systems run periodically.

---

## Architecture

LedgerFlow is a monorepo containing four independently runnable services. Services communicate through REST (synchronous, request-response) and Kafka (asynchronous, event-driven). Each service owns its own data — no cross-service database queries.

### Commerce Service

Owns the business side of a transaction. Responsible for checkout creation and lifecycle, price calculation, coupon application, inventory reservation and release, and order creation. It is the entry point for a customer interaction and the initiator of the payment flow. Commerce knows nothing about how money moves — it only knows that a checkout requires payment and reacts to the result.

Owned entities: `Checkout`, `CheckoutItem`, `Order`, `OrderItem`, `Inventory`, `InventoryReservation`

### Payment Service

Owns the mechanics of moving money. Responsible for payment session management, PSP integration (abstracted behind an interface), payment attempt orchestration, idempotency enforcement, retry scheduling, and refund workflows. When a payment succeeds or fails, it publishes an event and considers its job done.

Owned entities: `PaymentSession`, `PaymentAttempt`, `Refund`

### Ledger Service

Owns the financial record. Responsible for recording double-entry ledger entries for every money movement, maintaining wallet balances, and running reconciliation against simulated PSP settlement data. Ledger entries are immutable — no update or delete queries are ever issued against the `ledger_entries` table.

Owned entities: `LedgerEntry`, `Wallet`, `WalletTransaction`, `ReconciliationRecord`

### Notification Service

A pure event consumer with no HTTP API and no database of its own. Listens to events published by Commerce, Payment, and Ledger, and dispatches email or SMS notifications. Contains no business logic and makes no state-changing calls to other services.

---

## Distributed Systems Concepts Demonstrated

**Event-driven architecture**
Services communicate through Kafka topics. A service publishes an event describing what happened; downstream services react to it independently. No service knows which other services consume its events.

**Outbox pattern**
Producers never publish to Kafka directly from within a service call. Instead, an event is written to an outbox table as part of the same database transaction as the business mutation. A background worker reads from the outbox and publishes to Kafka. This eliminates the dual-write problem — if the service crashes after committing to the database but before publishing to Kafka, the outbox row survives and the event is eventually delivered.

**Idempotency**
Every mutating API endpoint accepts an idempotency key. The first request with a given key executes and stores the result. Subsequent requests with the same key return the stored result without re-executing the operation. This makes retrying safe — a network timeout that causes a client to retry will not result in a double charge.

**Retry handling**
Failed payment attempts are not retried immediately in-process. Instead, a retry schedule is created with a calculated backoff delay. A background worker periodically checks for due retries and re-triggers the attempt flow. This separates the concern of deciding to retry from the concern of executing the retry.

**Dead letter queues**
Messages that fail processing repeatedly — due to malformed payloads, unexpected state, or persistent downstream errors — are routed to a dead letter topic rather than blocking the main consumer. This prevents one bad message from halting all event processing on a topic.

**Event replay**
Because events are the source of communication between services, replaying events from a topic offset allows a service to rebuild its state or reprocess a historical window. This is demonstrated in the context of ledger re-derivation and reconciliation.

**Eventual consistency**
Ledger entries are not written synchronously when a payment is captured. Commerce does not commit inventory synchronously when it confirms an order. These updates happen asynchronously via events. The system is designed to accept that different services will briefly have inconsistent views of the world, and that consistency is achieved eventually through event processing.

**Saga-style workflows**
The checkout-to-ledger flow spans multiple services and multiple steps. There is no distributed transaction coordinator. Instead, each step publishes an event that triggers the next step, and failures at any step are handled by compensating actions (e.g., releasing inventory if payment fails). This is the choreography-based saga pattern.

---

## Payment Concepts Demonstrated

**Payment processing**
The system models the lifecycle of a payment from session creation through PSP submission, with distinct states for each phase. The PSP integration is abstracted behind an interface — the mock implementation applies deterministic rules to simulate successes and failures without any real network calls.

**Multiple payment attempts**
A payment session can accumulate multiple attempts. Each attempt is an independent record with its own outcome. The session's overall status is derived from the state of its attempts, not stored independently. This models how real payment systems handle retried charges without losing the history of what was tried.

**Payment retries**
Retries are scheduled, not immediate. The backoff interval is configurable. The system tracks how many attempts have been made and enforces a maximum, after which the session is marked as exhausted rather than retried indefinitely.

**Refund workflows**
Refunds are first-class entities, not simply negative payments. They have their own state machine, their own PSP call, and their own ledger entries. Partial refunds are supported — a refund does not have to cover the full captured amount.

**Ledger accounting**
Every money movement is recorded using double-entry bookkeeping. A capture debits the customer's wallet and credits the merchant's wallet. A refund reverses those entries. The ledger is append-only; this preserves a complete, auditable history of every financial event.

**Financial correctness**
Monetary values are stored as integers in the smallest denomination (paise, cents) to eliminate floating-point rounding errors. This is a hard constraint — no float arithmetic is applied to money anywhere in the system.

**Reconciliation**
The Ledger service periodically compares its internal records against a simulated PSP settlement report. Discrepancies are recorded as reconciliation records. This models the settlement and exception handling that payment operations teams run after every settlement cycle.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python |
| Web framework | FastAPI |
| Database | PostgreSQL (single instance, logical ownership per service) |
| Message broker | Kafka |
| Containerization | Docker Compose |
| Migrations | Alembic (per service) |
| Data validation | Pydantic |

---

## Current Scope

### In scope

- Complete checkout-to-order flow
- Inventory reservation, commitment, and release
- Payment session and attempt lifecycle
- Simulated PSP integration (deterministic mock)
- Idempotency enforcement on payment APIs
- Automatic payment retries with configurable backoff
- Refund workflows (full and partial)
- Double-entry ledger recording
- Wallet balance tracking
- Reconciliation against simulated PSP settlement data
- Transactional outbox pattern for Kafka publishing
- Dead letter queue handling for failed consumer messages
- Event-driven communication between services
- Saga-style compensating flows for failure cases
- Email and SMS notifications via event consumers

### Out of scope

- Real PSP integrations (Stripe, Razorpay, Adyen, etc.)
- PCI DSS compliance
- Card network processing (Visa, Mastercard, etc.)
- UPI internals
- Real banking integrations or NEFT/RTGS/SWIFT settlement
- Settlement with actual financial institutions
- Fraud detection
- 3DS authentication
- Multi-currency FX conversion
- Kubernetes, service mesh, or cloud infrastructure
- CI/CD pipelines

---

## Future Enhancements

- **Saga orchestrator:** Replace choreography-based sagas with an explicit orchestrator service to make workflow state and failure handling more observable.
- **Event sourcing on the ledger:** Store the ledger as a pure event log and derive wallet balances on read, rather than maintaining balance as materialized state.
- **DLQ reprocessing tooling:** Build a small admin interface for inspecting and reprocessing dead letter queue messages.
- **Webhook delivery:** Simulate PSP-style webhook callbacks to a merchant endpoint when payment events occur.
- **Multi-tenant wallets:** Extend the wallet model to support platform fees, marketplace splits, and escrow accounts.
- **Simulated settlement cycles:** Run periodic settlement jobs that sweep merchant balances and generate settlement reports.
- **Observability:** Add distributed tracing (OpenTelemetry) with correlation IDs propagated through HTTP headers and Kafka event payloads.

---

## Repository Structure

```
LedgerFlow/
├── docs/           # Architecture and design documentation
├── infra/          # Docker Compose, Kafka configuration, Postgres initialization
├── services/
│   ├── commerce/   # Checkout, inventory, and order management
│   ├── payment/    # Payment sessions, attempts, retries, and refunds
│   ├── ledger/     # Double-entry ledger, wallets, and reconciliation
│   └── notification/ # Event-driven email and SMS dispatch
└── shared/         # Kafka event schemas, database base, common utilities
```

Each service under `services/` is independently runnable with its own `Dockerfile`, dependency manifest, and migration history. The `shared/` package is installed as a local dependency in each service and contains no business logic — only cross-service contracts and infrastructure primitives.

For internal structure of each service, see [`docs/architecture.md`](docs/architecture.md).

---

## Engineering Notes

**Shared database, logical ownership**
All services write to the same PostgreSQL instance. This is a deliberate simplification — in a production system, each service would have its own database. The constraint enforced here is that a service only ever creates, reads, updates, or deletes its own tables. Tables are name-prefixed by service (`payment_sessions`, `commerce_checkouts`) to make ownership visible. This models the discipline required in a microservice architecture without the operational overhead of running four separate databases.

**Outbox over direct Kafka publishing**
An alternative approach would be to publish to Kafka directly inside the service method, before or after the database commit. This creates a window for partial failure: the database commits but the Kafka publish fails (or vice versa). The outbox pattern closes this window by making the event durable within the same database transaction as the business mutation. The tradeoff is added latency — events are delivered asynchronously by a background worker rather than immediately — and the need to operate the outbox worker alongside each service.

**PSP as an abstract interface**
The Payment service depends on a `PSPClient` interface, not a concrete PSP. The mock implementation is deterministic — it applies rules based on the payment amount or other inputs to simulate PSP responses. This keeps the payment logic testable without real network calls and makes it straightforward to add additional PSP adapters without changing service logic.

**Idempotency as a service-level concern**
Idempotency is enforced at the service layer, not the API layer. The service checks whether an operation with a given idempotency key has already been performed and returns the stored result if so. This means the API layer is thin and the business rule — "do not re-execute a duplicate request" — is expressed where the operation actually happens.

**Immutable ledger**
The ledger's append-only constraint is enforced by convention, not by the database. No `UPDATE` or `DELETE` is ever issued against `ledger_entries`. Corrections are recorded as new entries that reverse prior ones. This is a deliberate tradeoff — it requires discipline in the service layer but preserves a complete, unmodifiable audit trail of every financial event. In a production system, this constraint could be reinforced by removing database permissions for `UPDATE` and `DELETE` on this table.

**Eventual consistency as a feature, not a bug**
Commerce does not wait for the Ledger to acknowledge a payment before confirming an order. The Ledger does not need Commerce's confirmation before posting entries. Each service reacts to events asynchronously. The system is designed around the assumption that brief inconsistency between services is acceptable, and that all services will eventually converge on a consistent view once all events are processed. This is the practical tradeoff that makes event-driven microservices feasible at scale — strict synchronous consistency across service boundaries would require distributed transactions, which are operationally expensive and failure-prone.
