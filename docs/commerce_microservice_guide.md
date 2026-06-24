# Commerce Service — Engineering Knowledge Guide

> **Audience:** AI coding agents, new contributors, and the author returning after time away.
> **Scope:** Commerce microservice only. For system-wide architecture see `docs/project_structure.md`.
> **Status:** Active development — v1 service layer, routes, schemas, and middleware are implemented.

---

## Service Overview

The commerce service is the business-facing entry point for the LedgerFlow platform. It owns everything related to *what* is being transacted: the catalog of products, the sellers who list them, the buyers who purchase them, the inventory counts that gate purchases, and the lifecycle of a checkout session through to a confirmed order.

Its boundary ends at money movement. The commerce service creates an order and knows its status, but it does not process payments, move funds, or update wallet balances. When a checkout is ready to be paid, commerce logs a placeholder for the future payment event and defers to the payment service. When payment confirms or fails, commerce receives an event and updates its own state accordingly. This boundary keeps business logic (what is being bought, at what price, with what stock) strictly separate from financial mechanics (how money flows).

Within the larger LedgerFlow system, commerce is the origin of the transactional record. An order created here is the root entity that propagates into the payment, ledger, and notification services through events.

---

## Current Scope

The following capabilities are implemented:

- **Entity persistence** — full CRUD repository layer for users, sellers, products, inventory, checkouts, and orders backed by PostgreSQL.
- **Schema management** — Alembic migration chain (`0001_initial_schema` through three subsequent column-removal migrations) reflecting the current lean `Checkout` schema. Migrations run automatically on service startup.
- **Database seeding** — idempotent seeders that pre-populate 3 users, 2 sellers, 5 products, and corresponding inventory rows on every startup. Seeds are safe to re-run.
- **Inventory reservation model** — available/reserved quantity split with explicit `reserve`, `release`, and `commit_reservation` operations designed to support atomic checkout flows.
- **Consistent error handling** — a custom exception hierarchy (`AppException` and subclasses) mapped to HTTP status codes, with a global FastAPI exception handler that always returns a structured `ErrorResponse`.
- **Consistent response envelopes** — all success responses use `SuccessResponse`; all error responses use `ErrorResponse`. Both are Pydantic models.
- **Startup lifecycle** — FastAPI lifespan hook runs migrations then seeders before the server accepts traffic.
- **Health endpoint** — `GET /health` returns service name and environment without touching the database.
- **User validation middleware** — `UserValidationMiddleware` intercepts `POST /api/v1/checkouts/initiate`, reads the request body, queries the user repository, and short-circuits with a structured 404 before the route handler executes if the user is not found.
- **Checkout initiation API** — `POST /api/v1/checkouts/initiate` orchestrates the full synchronous checkout flow: checkout creation → inventory reservation → order creation → payment placeholder → status transitions.
- **Checkout retrieval API** — `GET /api/v1/checkouts/{checkout_id}` returns checkout state with all associated orders.
- **Order retrieval API** — `GET /api/v1/orders/{order_id}` returns order details enriched with product information.

---

## Architectural Overview

The service follows a layered architecture with strict unidirectional dependency flow:

```
HTTP layer (routes)  →  Service layer  →  Repository layer  →  Database
        ↑                     ↑
  Middleware             Domain models
  Schemas                Enums / Exceptions
                         Response envelopes
```

Each layer has a single responsibility and calls only downward. The `routes/` layer owns request validation and response shaping. The `service/` layer owns business logic and orchestration across repositories. The `repository/` layer owns all database interaction — it is the only layer that holds `Session` references and executes queries. Middleware intercepts requests before they reach the route layer.

**Key design principles in effect:**

- **No business logic in repositories.** Repos are purely data access. State transitions, stock checks, and multi-step operations belong in the service layer.
- **Every layer has try/except.** All repository methods catch `SQLAlchemyError` and re-raise as `DatabaseException`. All service methods catch `AppException` subclasses and re-raise them unchanged, and catch bare `Exception` to wrap as `ServiceException`. All route handlers catch `AppException` to return a structured `ErrorResponse` with the correct HTTP status code, and catch bare `Exception` to return a 500 `ErrorResponse`. This three-layer pattern means every failure is categorised at the layer where it is first understood.
- **Repos flush, services commit.** Repository methods call `db.flush()` — they write changes to the current transaction without committing. The service layer calls `db.commit()` on success and `db.rollback()` on failure. This means the entire checkout initiation flow (checkout creation, inventory reservation, order creation, status updates) is a single atomic transaction committed once at the end. On any failure, one `db.rollback()` undoes everything. No compensating transactions are needed.
- **Services own object instantiation via `__init__`.** Each service creates its own repository instances in `__init__`. There are no module-level singleton repos. Routes create service instances inside each handler function (one per request). Middleware creates services inline. This ensures no shared mutable state between requests.
- **Service layer owns cross-domain coordination through services only.** `checkout_service` creates and uses `order_service`, `product_service`, and `inventory_service` via `self.*`. It never accesses `OrderRepo`, `ProductRepo`, or `InventoryRepo` directly. Cross-domain data access always goes through the owning service.
- **Routes catch, not propagate.** Route handlers do not let exceptions bubble to the global exception handler for normal request processing. They catch and return `ErrorResponse` directly via `JSONResponse`. The global handlers in `main.py` exist only as a safety net for exceptions raised outside route handlers (middleware, lifespan, startup code).
- **Middleware short-circuits before service execution.** `UserValidationMiddleware` intercepts `POST /api/v1/checkouts/initiate` before the route handler runs. If validation fails, the middleware returns an `ErrorResponse` immediately and the route handler never executes. Route handlers document this with a comment explaining they rely on the middleware for user validation.
- **Singleton configuration objects.** `server_config` and `postgres_config` are module-level instances of Pydantic `BaseSettings` classes. They read from `.env` using prefix-scoped field mapping. `extra="ignore"` prevents cross-config contamination when both configs read the same file.
- **Singleton logger.** `AppLogger` uses `__new__` to enforce a single instance across the process.
- **IDs as UUID strings.** All primary keys and foreign keys are `VARCHAR(36)` storing standard UUID strings. IDs are generated by the application using `str(uuid.uuid4())`, not by the database.
- **Money as integers.** All monetary amounts are stored in the smallest denomination (paise for INR). Floats are never used for money anywhere in the codebase.
- **PostgreSQL enum types owned by Alembic.** All `ENUM` types are created via `op.execute("CREATE TYPE ...")` in the migration. SQLAlchemy models use `create_type=False` to prevent the ORM from attempting to create them.
- **Service layer owns cross-domain coordination.** A service may call other services (e.g. `checkout_service` calls `product_service` and `inventory_service`) but must never directly access a repository owned by another domain. Repository ownership is strict: checkout repo belongs to checkout service, inventory repo to inventory service, etc.

---

## Project Structure

### `config/`

Holds all application configuration and infrastructure setup. This folder is the boundary between environment and code — nothing outside `config/` should read environment variables directly.

- `server_config.py` — `ServerConfig` reads `APP_*` prefixed variables: service name, host, port, log level, API prefix, environment.
- `postgres_config.py` — `PostgresConfig` reads `POSTGRES_*` prefixed variables and exposes `sync_url` and `async_url` properties. Currently only `sync_url` is used.
- `database.py` — creates the SQLAlchemy `engine` and `SessionLocal` factory. Exposes `get_db()` as a FastAPI dependency that yields a session and closes it after the request.
- `logger.py` — `AppLogger` singleton wrapping Python's `logging` module. Uses `APP_LOG_LEVEL` for configuration. Supports structured key/value logging via `**kwargs` formatted as `key=value` pairs appended to the message.

`config/` has no knowledge of domain models or business logic. It is safe to import from anywhere.

### `models/`

Defines the SQLAlchemy ORM schema — the authoritative description of the database tables owned by this service. Models are pure schema declarations; they contain no query logic and no business rules.

All models inherit from `Base` (declarative base) and `TimestampMixin`. The mixin provides `created_at` and `updated_at` columns using `server_default=func.now()` and `onupdate=func.now()`. Note: `onupdate` is ORM-layer only — raw SQL `UPDATE` statements must manually include `updated_at = now()`.

`models/__init__.py` imports all six model classes. This file exists specifically to be imported as a side effect (`import models`) in `migrations/env.py`, which causes all models to register with `Base.metadata` so Alembic can see them.

The six entities are: `User`, `Seller`, `Product`, `Inventory`, `Checkout`, `Order`.

**Current `Checkout` schema** (after migrations): `id`, `user_id`, `total_amount`, `status`, `created_at`, `updated_at`. The columns `product_id`, `seller_id`, `coupon_id`, and `final_amount` have been removed via three successive migrations. Product and seller associations now live exclusively on the `Order` model.

### `repository/`

One repository class per entity. Each repository is a stateless class that accepts a `Session` as the first argument to every method. **Repos are not instantiated at module level** — each service creates its own repo instance in `__init__`.

Repositories are the **only** place in the codebase that interact with the database. Every method wraps its body in `try/except SQLAlchemyError` and re-raises as `DatabaseException`.

**All mutation methods use `db.flush()` not `db.commit()`.** `flush()` sends the SQL to the database within the current transaction but does not commit. The service layer controls when the transaction is committed. Repos keep `db.rollback()` in their except blocks because a failed flush leaves the session in an invalid state — the rollback resets the session to a clean state so the service's own `db.rollback()` and exception handling can proceed correctly.

Key repository methods beyond standard CRUD:

- `InventoryRepo.reserve(product_id, quantity)` — moves stock from available → reserved.
- `InventoryRepo.release(product_id, quantity)` — moves stock from reserved → available (used in checkout rollback).
- `InventoryRepo.commit_reservation(product_id, quantity)` — consumes reserved stock on payment success.
- `CheckoutRepo.update(checkout_id, total_amount, status)` — partial update for total_amount and/or status.
- `CheckoutRepo.get_with_user(checkout_id)` — raw SQL join returning checkout + user fields as a dict.
- `OrderRepo.get_all_by_checkout_id(checkout_id)` — returns all orders for a given checkout (list).

### `migrations/`

Contains Alembic configuration and versioned migration scripts. This folder owns the database schema lifecycle.

`env.py` is the Alembic runtime environment. It imports `postgres_config` to override the database URL at runtime, and imports `models` as a side effect to populate `Base.metadata`.

`alembic.ini` sets `script_location = migrations` and leaves `sqlalchemy.url` blank. The URL is injected by `env.py`.

Migration chain:
1. `0001_initial_schema.py` — creates all tables and PostgreSQL enum types from scratch.
2. `5fd91ec51db1_remove_product_id_from_checkouts.py` — removes `product_id` FK from checkouts.
3. `57fcfdb642c2_remove_seller_id_from_checkouts.py` — removes `seller_id` from checkouts.
4. `59d17e6243b9_remove_discounted_pricing_from_checkouts.py` — removes `coupon_id` and `final_amount` from checkouts.

### `seeders/`

`seed_data.py` contains static data fixtures — fixed UUID strings used as stable primary keys for 3 users, 2 sellers, 5 products, and 5 inventory rows.

`runner.py` orchestrates the seeding. Each `_seed_*` function checks for the existence of a record before inserting, making the operation fully idempotent.

### `utils/`

Cross-cutting utilities with no domain-specific knowledge.

`utils/enums.py` defines the Python enum classes (`CheckoutStatus`, `OrderStatus`, `Currency`) that mirror the PostgreSQL enum types.

`utils/common/` contains the three shared contract types:
- `custom_exception.py` — `AppException` base class and **six** subclasses. `NotFoundException` supports both `(resource, identifier)` and legacy `(message=...)` calling conventions. `InsufficientStockException` supports both `(product_id, requested, available)` and legacy `(details={...})` calling conventions. `ServiceException` (500) is raised by the service layer when an unexpected non-`AppException` error occurs. Every subclass maps to a specific HTTP status code and machine-readable error code string.
- `success_response.py` — `SuccessResponse` Pydantic model with `ok()` (200) and `created()` (201) factory classmethods. Used by route handlers and the `/health` endpoint.
- `error_response.py` — `ErrorResponse` Pydantic model with `from_exception()` and `internal_error()` factory classmethods. Used by route handlers (inside try/except), middleware, and the global exception handlers in `main.py`.

### `service/`

Business logic layer. Five service files are implemented. Every class follows this instantiation pattern:

```python
class SomeService:
    def __init__(self):
        self.some_repo = SomeRepo()      # own repo, created here
        self.other_service = OtherService()  # cross-domain via service, not repo
```

Every service method follows this exception pattern:

```python
try:
    # business logic
except AppException:
    raise                         # domain exceptions propagate unchanged
except Exception as exc:
    raise ServiceException(...)   # unknown errors are wrapped with context
```

Transaction ownership — only `checkout_service.initiate_checkout()` calls `db.commit()` and `db.rollback()`. All sub-service methods (`order_service.create_order`, `inventory_service.reserve`, etc.) flush only — they participate in the caller's transaction.

- `user_service.py` — wraps `UserRepo`; used by middleware and checkout orchestration. Read-only currently.
- `product_service.py` — wraps `ProductRepo`; product lookup for checkout and order enrichment. Read-only.
- `inventory_service.py` — wraps `InventoryRepo`; exposes `reserve`, `release`, `commit_reservation`. Flush-only (no commit) — called within checkout transaction.
- `order_service.py` — wraps `OrderRepo` and uses `ProductService`. Has two categories of methods:
  - **Internal mutation methods** (`create_order`, `update_order_status`, `get_orders_by_checkout_id`) — called from `checkout_service`, flush-only, no commit.
  - **Public read methods** (`get_by_id`) — called from order routes, returns order enriched with product details.
- `checkout_service.py` — owns the full checkout initiation transaction. Holds `self.checkout_repo`, `self.order_service`, `self.product_service`, `self.inventory_service`. Calls `db.commit()` on success and `db.rollback()` on any failure. Never accesses `OrderRepo`, `ProductRepo`, or `InventoryRepo` directly.

Note: stub files with hyphenated names (`checkout-service.py`, etc.) exist from initial scaffolding and are not importable. The implemented files use underscores.

### `schema/`

Pydantic request/response models:

- `checkout_schema.py` — `CheckoutInitiateRequest`, `ProductItem`, `CheckoutInitiateResponse`, `CheckoutDetailResponse`, `OrderSummary`.
- `order_schema.py` — `OrderDetailResponse`, `ProductDetail`.

### `routes/`

FastAPI route handlers. Every handler owns its own try/except and returns structured responses for both success and failure:

```python
@router.post("/initiate")
def initiate_checkout(request, db):
    try:
        result = checkout_service.initiate_checkout(...)
        return SuccessResponse.created(data=..., message="...")
    except AppException as exc:
        return JSONResponse(status_code=exc.status_code,
                            content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        return JSONResponse(status_code=500,
                            content=ErrorResponse.internal_error().model_dump())
```

- `checkout_routes.py` — `POST /checkouts/initiate`, `GET /checkouts/{checkout_id}`. Registered under `/api/v1` prefix. Contains a comment block explaining that user validation for `POST /initiate` is handled entirely by `UserValidationMiddleware` before this handler executes.
- `order_routes.py` — `GET /orders/{order_id}`. Registered under `/api/v1` prefix.

The global exception handlers in `main.py` are a fallback only — under normal request processing all exceptions are caught by the route handlers.

### `middleware/`

- `user_validation.py` — `UserValidationMiddleware` (`BaseHTTPMiddleware` subclass). Intercepts `POST /api/v1/checkouts/initiate`, parses the request body JSON, extracts `user_id`, queries `user_repo`, and returns a 404 `ErrorResponse` if the user does not exist. FastAPI caches the request body so the route handler can still read it after the middleware has consumed it.

### `main.py`

The application entry point and FastAPI app definition. Registers `UserValidationMiddleware` and includes both routers under the `/api/v1` prefix. Two global exception handlers are registered as a safety net for exceptions raised outside route handlers (middleware errors, lifespan failures). Both handlers return `ErrorResponse` serialized as `JSONResponse`. The `/health` endpoint returns `SuccessResponse.ok()` with service name, environment, and status. The lifespan hook runs migrations then seeders before the server begins accepting requests.

---

## Request and Data Flow

### `POST /api/v1/checkouts/initiate`

```
1. UserValidationMiddleware
   └─ Read body → extract user_id
   └─ user_repo.get_by_id() → 404 if not found

2. Route handler validates request schema (CheckoutInitiateRequest)

3. checkout_service.initiate_checkout(user_id, products)
   a. checkout_repo.create()               → PENDING checkout, total_amount=0
   b. For each product:
      ├─ product_service.get_by_id()       → fetch price, seller_id, currency
      └─ inventory_service.reserve()       → available → reserved (raises InsufficientStockException if short)
   c. For each product:
      └─ order_repo.create()               → CREATED order per product
   d. logger.info("Payment initiation placeholder…")
   e. order_repo.update_status()           → all orders CREATED → PAYMENT_PENDING
   f. checkout_repo.update()              → total_amount + PAYMENT_PENDING
   
   On any failure:
   ├─ inventory_service.release() for each reserved product
   ├─ order_repo.delete() for each created order
   └─ checkout_repo.delete() for the checkout

4. Route returns SuccessResponse.created(CheckoutInitiateResponse)
```

### `GET /api/v1/checkouts/{checkout_id}`

```
checkout_service.get_checkout()
  ├─ checkout_repo.get_by_id()
  └─ order_repo.get_all_by_checkout_id()

Route returns SuccessResponse.ok(CheckoutDetailResponse)
```

### `GET /api/v1/orders/{order_id}`

```
order_service.get_by_id()
  ├─ order_repo.get_by_id()
  └─ product_service.get_by_id()

Route returns SuccessResponse.ok(OrderDetailResponse)
```

---

## Core Domain Concepts

**User** — A buyer. Has an email (unique), name, and optional phone.

**Seller** — A merchant listing products. Has an email (unique) and name.

**Product** — A catalog item owned by a seller. Has a price stored in the smallest monetary denomination (paise for INR) and a currency.

**Inventory** — One row per product. Tracks `available_quantity` (sellable stock) and `reserved_quantity` (stock held for in-flight checkouts).

**Checkout** — A session representing a buyer's intent to purchase one or more products. Carries `total_amount` and a `status`. The checkout is the parent entity for all orders created during that session. It does not directly reference products or sellers — that information lives on the orders. Status transitions: `PENDING → PAYMENT_PENDING` (on successful initiation), with future transitions to `PAYMENT_COMPLETED / PAYMENT_FAILED / EXPIRED / CANCELLED` driven by payment service events.

**Order** — One order per product line in a checkout. Created during checkout initiation. Carries `product_id`, `seller_id`, `amount`, `currency`, and status flags for downstream service acknowledgment (`ledger_updated`, `wallet_updated`). Status transitions: `CREATED → PAYMENT_PENDING` (during checkout initiation), with future transitions driven by payment events.

**CheckoutStatus values:** `PENDING`, `PAYMENT_INITIATED`, `PAYMENT_FAILED`, `PAYMENT_COMPLETED`, `EXPIRED`, `CANCELLED`

**OrderStatus values:** `CREATED`, `PAYMENT_PENDING`, `CONFIRMED`, `CANCELLED`, `REFUND_INITIATED`, `REFUNDED`

---

## Integration Points

**PostgreSQL (primary store)**
The service's only current external dependency. A single `ledgerflow` database holds all six tables. The connection is synchronous (`psycopg2-binary`).

**Payment service (planned, event-driven)**
Commerce will publish a `CheckoutPaymentRequested` event when a checkout is ready. The current placeholder log in `checkout_service.initiate_checkout()` marks the integration point. Commerce will consume a `PaymentCaptured` event to trigger `commit_reservation` and status transitions, and a `PaymentFailed` event to `release` inventory and update checkout/order status. These events are not yet implemented.

**Ledger service (planned, event-driven)**
After order creation, commerce will produce an `OrderCreated` event. The ledger service acknowledges via `LedgerUpdated`, which sets `order.ledger_updated = True`.

**Notification service (planned, event-driven)**
Consumes order and checkout events to dispatch user-facing emails or SMS. Commerce has no direct coupling to notification.

---

## Important Architectural Decisions

**Single DB transaction for checkout initiation (flush/commit/rollback pattern)**
Repository mutation methods call `db.flush()` instead of `db.commit()`. The service layer is the sole owner of the transaction boundary. `checkout_service.initiate_checkout()` flushes all steps (checkout creation, inventory reservations, order creation, status updates) within a single open transaction, then calls `db.commit()` once at the end. On any failure, `db.rollback()` undoes every flush atomically — no compensating transactions, no manual cleanup of created records. This is a strict improvement over the saga pattern: simpler code, true atomicity, and guaranteed consistency.

**VARCHAR(36) for IDs instead of PostgreSQL UUID type**
IDs are stored as standard UUID strings in `VARCHAR(36)` columns rather than PostgreSQL's native UUID type. This avoids the `psycopg2`/SQLAlchemy impedance mismatch. The tradeoff is slightly more storage and no database-level UUID validation.

**Synchronous SQLAlchemy over async**
The service uses synchronous SQLAlchemy (`psycopg2-binary`) rather than async (`asyncpg`). This is a deliberate simplicity tradeoff at early development stages.

**PGEnum instead of sa.Enum in migrations**
`sa.Enum` with `create_type=False` does not reliably skip auto-creation of PostgreSQL enum types inside `op.create_table` in all SQLAlchemy versions. The migration uses `sqlalchemy.dialects.postgresql.ENUM` (aliased as `PGEnum`) which unconditionally respects `create_type=False`.

**Auto-run migrations on startup**
`command.upgrade(alembic_cfg, "head")` runs in the FastAPI lifespan before the server accepts traffic.

**Repository pattern with singleton instances**
Each repository class is instantiated once at module level and imported as a singleton. The session is passed per-call, not per-instance, so the singleton pattern is safe.

**Transactional outbox deferred**
Event publishing is planned but not implemented. The architecture documentation notes that commerce should never publish to Kafka directly from within a service method — events should be written to an outbox table in the same transaction as the business mutation, with a background worker relaying to Kafka.

**Backward-compatible exception constructors**
`NotFoundException` and `InsufficientStockException` support both the current `(resource, identifier)` / `(product_id, requested, available)` calling conventions and the legacy `(message=...)` / `(details={...})` conventions used in earlier repository code. This avoids a runtime `TypeError` from existing repos while allowing new code to use the cleaner API.

---

## Operational Considerations

**Configuration**
All configuration is driven by `.env` in the service root. `ServerConfig` reads `APP_*` prefixed keys; `PostgresConfig` reads `POSTGRES_*` prefixed keys.

**Environment**
The service is designed to run locally via `python main.py` or `uvicorn main:app --reload` from the `services/commerce-service/` directory. The working directory must be `services/commerce-service/`.

**Database bootstrap**
PostgreSQL must be running and the `ledgerflow` database must exist before the service starts. Docker Compose at the repo root manages the Postgres container (`ledgerflow-postgres`) on port 5433.

**Observability**
Structured logging via `AppLogger`. Log lines follow the format `timestamp | LEVEL | commerce-service | message | key=value ...`.

**Startup sequence dependency**
The service will fail to start if PostgreSQL is not reachable. There is no retry logic or connection wait in the lifespan hook.

---

## Known Constraints

- **No authentication.** The service has no auth middleware. User identity is passed as a raw ID in request payloads. Auth is explicitly out of scope.
- **No coupon logic.** Coupon support has been removed from the current Checkout model. `final_amount` does not exist on checkouts; order amounts reflect full product price × quantity.
- **Single product per order, multiple orders per checkout.** Each `Order` references one product. Multi-product purchases are supported by creating one order per product within the same checkout.
- **No outbox table.** The transactional outbox pattern is architecturally intended but the `outbox` table and Kafka infrastructure do not exist yet.
- **`onupdate` is ORM-only.** `TimestampMixin.updated_at` uses SQLAlchemy's `onupdate=func.now()`. Raw SQL `UPDATE` via `text()` must manually include `updated_at = now()`.
- **Enum drift risk.** PostgreSQL enum types are defined in three places: the migration SQL, the `PGEnum` instances in the migration, and the Python enum classes in `utils/enums.py`. All three must be updated together when enum values change.
- **Hyphenated stub files are not importable.** `service/checkout-service.py`, `service/order-service.py`, `service/inventory-service.py` remain as legacy stubs. Implemented files use underscores.

---

## Development Notes

**Adding a new enum value**
Do not edit `0001_initial_schema.py`. Create a new migration: `alembic revision -m "add_value_to_checkout_status"`. Then add the value to `utils/enums.py`.

**Adding a new model**
Create the model in `models/`, add it to `models/__init__.py`, then run `alembic revision --autogenerate -m "add_table_name"`. Review the generated file before committing.

**Error handling convention**
Three-layer exception handling:
1. **Repository** — catches `SQLAlchemyError`, re-raises as `DatabaseException`. Domain failures (not found, insufficient stock) raise the appropriate `AppException` subclass directly.
2. **Service** — catches `AppException` subclasses and re-raises unchanged. Catches bare `Exception` and wraps as `ServiceException`. Never swallows exceptions silently.
3. **Routes** — catches `AppException` and returns `JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())`. Catches bare `Exception` and returns `JSONResponse(500, ErrorResponse.internal_error().model_dump())`. No exceptions propagate to the global handler under normal conditions.
4. **Global handlers in main.py** — safety net only; handles exceptions from middleware, lifespan, or any code path outside route handlers.

**Response convention**
All route handlers return `SuccessResponse.ok(data=...)` for reads and `SuccessResponse.created(data=...)` for creates. Do not return raw Pydantic models or dicts from route handlers.

**Session management**
Never hold a `Session` outside a repository method or a middleware dispatch block. The session is provided by the `get_db()` FastAPI dependency and closed after each request. Services and repos must not store the session on `self` — it is passed per-call. Middleware creates its own `SessionLocal()` session and closes it in a `finally` block.

**Instantiation**
Repos are instantiated in the `__init__` of the service that owns them. Services are instantiated at the top of each route handler function. Neither repos nor services have module-level singleton instances. This avoids shared mutable state between requests and makes the dependency graph explicit.

---

## AI Agent Context

**What this service does:** Manages the commerce domain — users, sellers, products, inventory, checkouts, and orders. It is the origin of the transaction record in a distributed payment platform.

**Folder ownership:**
- `config/` — infrastructure wiring only; do not add business logic here
- `models/` — schema declarations only; never add query methods or business logic to model classes
- `repository/` — all database I/O; one class per entity; every method must have try/except
- `service/` — business orchestration layer; services may call other services but never another service's repository
- `middleware/` — request interception before route handlers; currently holds user validation
- `schema/` — Pydantic request/response contracts; no business logic
- `routes/` — thin HTTP handlers; call service methods and shape responses only
- `migrations/` — owned by Alembic; only modify via `alembic revision` commands
- `seeders/` — idempotent startup data; fixed UUIDs must not be changed once the DB has been seeded
- `utils/common/` — shared contracts (`AppException`, `SuccessResponse`, `ErrorResponse`)
- `utils/enums.py` — Python mirror of PostgreSQL enum types; must stay in sync with migration definitions

**Implemented APIs:**
- `POST /api/v1/checkouts/initiate` — checkout initiation with inventory reservation and order creation
- `GET /api/v1/checkouts/{checkout_id}` — checkout state with associated orders
- `GET /api/v1/orders/{order_id}` — order details with product information

**Major workflows not yet implemented:**
- Payment service event consumption (PaymentCaptured → commit_reservation + order confirmation)
- Payment failure handling (PaymentFailed → release inventory + update statuses)
- Outbox table + Kafka relay for event publishing
- Checkout expiration / cancellation flows

**Rules an AI agent must not break without understanding the wider impact:**
1. **Never remove `create_type=False`** from any `SAEnum` or `PGEnum` column definition.
2. **Never change the fixed seed UUIDs** in `seeders/seed_data.py` if the database has already been seeded.
3. **Never add `import models` to any file other than `migrations/env.py`** for the purpose of metadata registration.
4. **Never modify an existing migration file** to change already-applied schema. Create a new migration instead.
5. **Never store a `Session` on a repository instance** — sessions are per-request, not per-singleton.
6. **Always use `PGEnum(..., create_type=False)`** (not `sa.Enum`) in migration `op.create_table` calls for enum columns.
7. **Always raise `AppException` subclasses** from service and repository layers — never return `None` to signal failure.
8. **Never access a repository from a service that doesn't own it.** Cross-domain data access must go through the owning service layer.
