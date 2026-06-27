# Payment Service — Engineering Knowledge Guide

> **Audience:** AI coding agents, new contributors, and the author returning after time away.
> **Scope:** Payment microservice only. For system-wide architecture see `docs/project_structure.md`.
> **Status:** Active development — config, models, repositories, payment session service, API, and middleware implemented.

---

## Service Overview

The payment service is the financial execution layer of the LedgerFlow platform. It owns everything related to *how* money moves: creating payment sessions for buyers, coordinating with external providers, tracking payment state transitions, and publishing the outcome events that allow commerce, ledger, and notification services to react.

Its boundary starts where commerce ends. When commerce creates a checkout and its orders are ready for payment, commerce publishes a `CheckoutPaymentRequested` event. The payment service consumes this event, creates a `PaymentSession`, and returns a redirect URL to the buyer for payment completion. It does not know about products, sellers, inventory, or order line items — that domain belongs entirely to commerce.

The payment service is the sole owner of `PaymentSession` records. No other service writes to these tables.

---

## Current Scope

The following is implemented:

- **Config layer** — `ServerConfig`, `PostgresConfig`, `AppLogger`, `database.py` with `get_db()` dependency. `ServerConfig` carries `payment_session_expiry_seconds` (default 900s / 15 min), overridable via `APP_PAYMENT_SESSION_EXPIRY_SECONDS` in `.env`.
- **Shared contracts** — `AppException` hierarchy (including `PaymentException`), `SuccessResponse`, `ErrorResponse` in `utils/common/`.
- **Enum definitions** — `PaymentStatus`, `PaymentMethod`, `Currency`, `RefundStatus` in `utils/enums.py`.
- **ORM base** — `Base` (declarative base) and `TimestampMixin` in `models/base.py`.
- **Models** — `User` (read-side mirror, no DB FK to commerce), `PaymentSession`.
- **Repositories** — `UserRepo` (full CRUD), `PaymentSessionRepo` (create, get\_by\_id, get\_by\_checkout\_id, get\_all\_by\_user\_id, update\_status, delete).
- **Alembic wiring** — `alembic.ini`, `migrations/env.py` with `include_object` filter (derives owned tables from `Base.metadata` automatically), separate `payment_alembic_version` table. First migration (`87f32a03d60c`) creates `payment_status`, `payment_method` enum types and `payment_sessions` table.
- **`RequestLoggerMiddleware`** — logs method, path, client IP, status code, and elapsed time for every request.
- **Payment session service** — `PaymentSessionService.initiate_session()` validates user, computes `expires_at` from `server_config.payment_session_expiry_seconds`, creates the session, commits the transaction.
- **Payment session API** — `POST /api/v1/payment-sessions/initiate`.
- **FastAPI app** — `main.py` with lifespan hook (migrations on startup), `RequestLoggerMiddleware`, global exception handlers, `GET /health`.

**Not yet implemented:**
- Refund model, repository, service, routes
- Payment capture / failure flows
- Event consumption (`CheckoutPaymentRequested`)
- Event publishing (`PaymentCaptured`, `PaymentFailed`)
- Real payment provider integration (Razorpay / Stripe)

---

## Architectural Overview

The service follows the same layered architecture as the commerce service, with strict unidirectional dependency flow:

```
HTTP layer (routes)  →  Service layer  →  Repository layer  →  Database
        ↑                     ↑
  Middleware             Domain models
  Schemas                Enums / Exceptions
                         Response envelopes
```

All design principles from the commerce service apply here without exception.

**Key design principles in effect:**

- **No business logic in repositories.** Repos are purely data access. State transitions and multi-step operations belong in the service layer.
- **Every layer has try/except.** Repository methods catch `SQLAlchemyError` → re-raise as `DatabaseException`. Service methods catch `AppException` subclasses and re-raise unchanged; catch bare `Exception` → wrap as `ServiceException`. Route handlers catch `AppException` → return `ErrorResponse` with correct status code; catch bare `Exception` → return 500 `ErrorResponse`.
- **Repos flush, services commit.** `db.flush()` in repositories. `db.commit()` / `db.rollback()` owned exclusively by the service layer.
- **Services own object instantiation via `__init__`.** Each service creates its own repository instances in `__init__`. No module-level singleton repos. Routes create service instances inside each handler function.
- **Service layer owns cross-domain coordination through services only.** A service may call other services but must never directly access a repository owned by another domain.
- **Routes catch, not propagate.** Route handlers do not let exceptions bubble to the global exception handler. The global handlers in `main.py` are a safety net only.
- **Singleton configuration objects.** `server_config` and `postgres_config` are module-level instances. `extra="ignore"` prevents cross-config contamination.
- **Singleton logger.** `AppLogger` uses `__new__` to enforce a single instance.
- **IDs as UUID strings.** All PKs and FKs are `VARCHAR(36)` storing standard UUID strings generated by the application via `str(uuid.uuid4())`.
- **Money as integers.** All monetary amounts stored in smallest denomination (paise for INR). No floats for money anywhere.
- **PostgreSQL enum types owned by Alembic.** All `ENUM` types created via `op.execute("CREATE TYPE ...")` in the migration. SQLAlchemy models use `create_type=False`.

---

## Project Structure

### `config/`

Nothing outside `config/` reads environment variables directly.

- `server_config.py` — `ServerConfig` reads `APP_*` prefixed variables. Key fields:
  - `name` — `payment-service`
  - `port` — `8002`
  - `payment_session_expiry_seconds` — default `900` (15 min). Set via `APP_PAYMENT_SESSION_EXPIRY_SECONDS` in `.env` to change session TTL without a code deploy.
- `postgres_config.py` — `PostgresConfig` reads `POSTGRES_*` prefixed variables. Exposes `sync_url` and `async_url`. Only `sync_url` is used currently.
- `database.py` — Creates the SQLAlchemy `engine` and `SessionLocal` factory. Exposes `get_db()` as a FastAPI dependency.
- `logger.py` — `AppLogger` singleton. Log lines follow the format `timestamp | LEVEL | payment-service | message | key=value ...`.

### `models/`

- `base.py` — `Base` (declarative base) and `TimestampMixin` (`created_at`, `updated_at`). `onupdate` is ORM-layer only — raw SQL `UPDATE` statements must manually include `updated_at = now()`.
- `user.py` — Read-side mirror of commerce's `User`. Exists so `UserRepo` can query the shared `users` table. No DB-level FK constraint to commerce. **Do not create a migration for this table** — commerce owns and creates it.
- `payment_session.py` — `PaymentSession` with all 11 columns (see Core Domain Concepts).
- `__init__.py` — Imports all model classes. Imported as a side effect in `migrations/env.py` to register models with `Base.metadata`. The `include_object` filter in `env.py` uses `Base.metadata.tables` to determine which tables belong to the payment service — `users` is therefore excluded because it is not in `PAYMENT_SERVICE_TABLES` (the filter is now derived dynamically, but `users` is intentionally omitted from `models/__init__.py`'s effect on autogenerate by the fact that commerce already owns it in the DB).

> **Important:** `User` is imported in `models/__init__.py` for SQLAlchemy ORM query support, but the `include_object` filter in `migrations/env.py` must explicitly exclude the `users` table to prevent the payment service from generating migrations for it. The filter uses `target_metadata.tables`, so if `User` is registered with `Base.metadata`, `users` will appear there. Keep `User` out of `Base.metadata` by **not** importing it in `models/__init__.py` — use a separate import only in `repository/user_repo.py` directly.

### `repository/`

One repository class per entity. Each accepts `Session` as the first argument to every method. All mutation methods use `db.flush()`. Every method wraps its body in `try/except SQLAlchemyError` → re-raises as `DatabaseException`.

- `user_repo.py` — `UserRepo`: `create`, `get_by_id`, `get_by_email`, `get_all`, `update`, `delete`. Read-only in practice for the payment service (user records are written by commerce).
- `payment_session_repo.py` — `PaymentSessionRepo`:
  - `create(db, checkout_id, user_id, amount, currency, redirect_url, expires_at, payment_method=None)` → `PaymentSession`
  - `get_by_id(db, session_id)` → `PaymentSession` (raises `NotFoundException` if missing)
  - `get_by_checkout_id(db, checkout_id)` → most recent `PaymentSession` or `None`
  - `get_all_by_user_id(db, user_id, skip, limit)` → `list[PaymentSession]`
  - `update_status(db, session_id, status, payment_method=None)` → `PaymentSession`
  - `delete(db, session_id)` → `None`

### `migrations/`

- `env.py` — Alembic runtime. Imports `postgres_config` for URL injection and `import models` as side effect. Uses a separate version table (`payment_alembic_version`) so commerce and payment track their migration chains independently on the same database. `include_object` derives owned tables from `Base.metadata` — no manual table list to maintain.
- `alembic.ini` — `script_location = migrations`. URL left blank, injected by `env.py`.
- `versions/87f32a03d60c_added_payment_session_model.py` — Creates `payment_status` and `payment_method` PostgreSQL enum types (skips `currency` — already created by commerce) and the `payment_sessions` table with indexes on `checkout_id` and `user_id`.

### `seeders/`

No seed data for the payment service. All `PaymentSession` records originate from live request flows. Folder exists for structural consistency.

### `utils/`

#### `utils/enums.py`

- `PaymentStatus` — `INITIATED`, `PENDING`, `CAPTURED`, `FAILED`, `REFUND_INITIATED`, `REFUNDED`, `CANCELLED`
- `PaymentMethod` — `UPI`, `CARD`, `NET_BANKING`, `WALLET`
- `Currency` — `INR`, `USD`, `GBP`, `EUR`, `JPY`
- `RefundStatus` — `INITIATED`, `PROCESSED`, `FAILED`

#### `utils/common/`

- `custom_exception.py` — `AppException` base class and subclasses: `NotFoundException`, `ConflictException`, `ValidationException`, `DatabaseException`, `ServiceException`, `PaymentException` (HTTP 402, error code `PAYMENT_FAILED`).
- `success_response.py` — `SuccessResponse` with `ok()` and `created()` classmethods.
- `error_response.py` — `ErrorResponse` with `from_exception()` and `internal_error()` classmethods.

### `services/`

Note: directory is named `services/` (plural), unlike commerce's `service/`. Do not rename.

- `payment_session_service.py` — `PaymentSessionService`:
  - `__init__` creates `PaymentSessionRepo` and `UserRepo`.
  - `initiate_session(db, checkout_id, user_id, amount, currency)`:
    1. Calls `user_repo.get_by_id()` — raises `NotFoundException` if user does not exist.
    2. Computes `expires_at = now(UTC) + timedelta(seconds=server_config.payment_session_expiry_seconds)`.
    3. Builds a dummy `redirect_url`.
    4. Calls `payment_session_repo.create()`.
    5. Calls `db.commit()`.
    6. Returns the created `PaymentSession`.
    7. On `AppException`: calls `db.rollback()` and re-raises.
    8. On bare `Exception`: calls `db.rollback()` and raises `ServiceException`.

### `schema/`

- `payment_session_schema.py`:
  - `PaymentSessionInitiateRequest` — `checkout_id: str`, `user_id: str`, `amount: int`, `currency: Currency`.
  - `PaymentSessionInitiateResponse` — `session_id: str`, `checkout_id: str`, `redirect_url: str`, `status: str`, `expires_at: datetime`.

### `routes/`

- `payment_session_routes.py` — `APIRouter(prefix="/payment-sessions")`:
  - `POST /initiate` — validates `PaymentSessionInitiateRequest`, calls `PaymentSessionService.initiate_session()`, returns `SuccessResponse.created(PaymentSessionInitiateResponse)`. Catches `AppException` → `ErrorResponse` with correct status code. Catches bare `Exception` → 500 `ErrorResponse`.

### `middleware/`

- `request_logger.py` — `RequestLoggerMiddleware` (`BaseHTTPMiddleware`). Intercepts every request. Logs method, path, and client IP on ingress. Logs method, path, status code, and elapsed milliseconds on egress. Registered in `main.py` and applied to all routes including `/health`.

### `main.py`

FastAPI app entry point. Lifespan hook runs migrations before the server accepts traffic. `RequestLoggerMiddleware` registered and active for all routes. Global exception handlers as safety nets. `GET /health` returns service name, environment, and status. Runs on port `8002`.

---

## Request and Data Flow

### `POST /api/v1/payment-sessions/initiate`

```
1. RequestLoggerMiddleware — logs incoming request

2. Route handler validates PaymentSessionInitiateRequest schema

3. PaymentSessionService.initiate_session(checkout_id, user_id, amount, currency)
   a. user_repo.get_by_id()                → 404 NotFoundException if user missing
   b. expires_at = now(UTC) + timedelta(seconds=server_config.payment_session_expiry_seconds)
   c. redirect_url = "https://pay.ledgerflow.dev/session/{checkout_id}"  [dummy]
   d. payment_session_repo.create()        → flush PaymentSession (status=INITIATED)
   e. db.commit()

4. Route returns SuccessResponse.created(PaymentSessionInitiateResponse)
   {session_id, checkout_id, redirect_url, status, expires_at}

5. RequestLoggerMiddleware — logs status code + elapsed ms
```

### `GET /health`

```
1. RequestLoggerMiddleware — logs incoming request
2. Returns SuccessResponse.ok({service, environment, status})
3. RequestLoggerMiddleware — logs 200 + elapsed ms
```

---

## Core Domain Concepts

**User** — Read-side reference to a commerce buyer. The `users` table is owned and written by the commerce service. The payment service queries it read-only to validate that a `user_id` in an initiation request actually exists.

**PaymentSession** — A session representing a buyer's intent to complete payment for a checkout. One checkout maps to one active session in the happy path. Carries `amount`, `currency`, `status`, an optional `payment_method` (set when the buyer selects one), a `redirect_url` for the payment UI, and `expires_at` for TTL enforcement. Status starts at `INITIATED`.

**PaymentStatus transitions:**
`INITIATED → PENDING → CAPTURED` (success path)
`INITIATED → PENDING → FAILED` (provider rejection)
`CAPTURED → REFUND_INITIATED → REFUNDED` (refund path)
`INITIATED / PENDING → CANCELLED` (timeout / checkout expiry)

**RefundStatus transitions:**
`INITIATED → PROCESSED` (success)
`INITIATED → FAILED` (provider rejection)

**Session expiry** — `expires_at` is `now(UTC) + payment_session_expiry_seconds`. Default is 900 seconds (15 minutes). Change via `APP_PAYMENT_SESSION_EXPIRY_SECONDS` in `.env` without a code deploy.

---

## Integration Points

**Commerce service (event-driven, planned)**
Commerce publishes `CheckoutPaymentRequested` when a checkout is ready. Payment consumes this event to call `PaymentSessionService.initiate_session()`. Payment publishes `PaymentCaptured` (triggers commerce to commit reservation and confirm orders) and `PaymentFailed` (triggers commerce to release inventory and cancel orders). Currently driven by direct HTTP calls.

**External payment providers (planned)**
Razorpay or Stripe integration will live inside the service layer. The dummy `redirect_url` marks the integration point. Replace with a real provider URL once the provider SDK is integrated.

**PostgreSQL (primary store)**
Same `ledgerflow` database as the commerce service. Payment owns `payment_sessions`. The `users` table is shared read-only. Cross-service references (`checkout_id`, `user_id`) are plain `VARCHAR(36)` with no DB-level FK constraints.

---

## Important Architectural Decisions

**Session expiry via config, not hardcoded**
`payment_session_expiry_seconds` lives in `ServerConfig` and is read from `APP_PAYMENT_SESSION_EXPIRY_SECONDS` in `.env`. The service layer reads `server_config.payment_session_expiry_seconds` at call time — never hardcodes `900` or `timedelta(minutes=15)` in business logic. This allows expiry to be changed per environment without a code change.

**`expires_at` computed in the service layer**
`expires_at` is calculated in `PaymentSessionService.initiate_session()`, not in the repository and not in the route handler. The service layer owns business rules; the repo only persists what it receives.

**Cross-service foreign keys as plain strings**
`payment_sessions.checkout_id` and `payment_sessions.user_id` reference rows owned by the commerce service. No DB-level FK constraints. Referential integrity is enforced at the application layer — the service validates user existence via `user_repo.get_by_id()` before creating the session.

**`RequestLoggerMiddleware` on all routes**
Every request — including `/health` — passes through `RequestLoggerMiddleware`. This is intentional: health checks from load balancers are useful signal for latency monitoring. The middleware logs ingress and egress separately so elapsed time is always captured even when the route handler raises an exception.

**Separate Alembic version table**
`payment_alembic_version` keeps the payment service's migration history independent from commerce's `alembic_version` on the same database. Each service runs `alembic upgrade head` against its own chain without interfering with the other.

**`include_object` derived from `Base.metadata`**
`migrations/env.py` uses `target_metadata.tables` (populated by `import models`) to determine which tables belong to this service. Adding a new model to `models/__init__.py` automatically includes it in future autogenerate runs. Removing a model automatically excludes it. No manual table list to maintain.

**Synchronous SQLAlchemy**
Sync SQLAlchemy with `psycopg2-binary`. Deliberate simplicity tradeoff at this development stage.

---

## Operational Considerations

**Configuration**
All configuration via `.env` in the service root. Key env vars:
- `APP_PAYMENT_SESSION_EXPIRY_SECONDS` — session TTL in seconds (default 900)
- `POSTGRES_PORT` — 5433 (Docker Compose Postgres)

**Running the service**
```
cd services/payment-service
python main.py
# or
uvicorn main:app --reload
```
Working directory must be `services/payment-service/`.

**Port** — `8002` (commerce is `8001`).

**Database bootstrap** — Same `ledgerflow` PostgreSQL instance. Migrations run automatically on startup.

**Startup sequence** — Service will fail to start if PostgreSQL is not reachable. No retry logic.

---

## Known Constraints

- **Dummy redirect URL.** `redirect_url` is a static string. Replace with a real provider URL once Razorpay / Stripe is integrated.
- **No session expiry enforcement.** `expires_at` is stored but not enforced — expired sessions are not rejected or cleaned up automatically. A background job or query-time check is needed.
- **`User` model must not generate a migration.** `user_repo.py` imports `User` directly from `models/user.py`. Do not import `User` in `models/__init__.py` or it will appear in `Base.metadata` and the `include_object` filter may incorrectly include the `users` table in autogenerate output.
- **No event consumption.** Payment initiation is triggered by direct HTTP POST, not by a `CheckoutPaymentRequested` event.
- **`onupdate` is ORM-only.** Raw SQL `UPDATE` must manually set `updated_at = now()`.
- **Enum drift risk.** PostgreSQL enum types, `PGEnum` instances in migrations, and Python enum classes in `utils/enums.py` must all be updated together.
- **`services/` vs `service/`.** This service uses `services/` (plural).

---

## Development Notes

**Adding a new model**
1. Create `models/<name>.py` inheriting from `Base` and `TimestampMixin`.
2. Import it in `models/__init__.py`.
3. Run `alembic revision --autogenerate -m "description"` — the new table appears automatically via `include_object`.
4. Review the generated file — fix enum columns to use `PGEnum(..., create_type=False)` and add `op.execute("CREATE TYPE ...")` manually.

**Changing session expiry**
Edit `APP_PAYMENT_SESSION_EXPIRY_SECONDS` in `.env` and restart. No code change needed.

**Adding a new enum value**
Do not edit existing migration files. Create a new migration: `alembic revision -m "add_value_to_payment_status"`. Add the value to `utils/enums.py`.

**Error handling convention**
1. **Repository** — catches `SQLAlchemyError` → `DatabaseException`. Domain failures raise `AppException` subclasses directly.
2. **Service** — catches `AppException` → re-raises. Catches bare `Exception` → `ServiceException`. Calls `db.rollback()` in both failure paths before re-raising.
3. **Routes** — catches `AppException` → `JSONResponse(exc.status_code, ErrorResponse.from_exception(exc))`. Catches bare `Exception` → `JSONResponse(500, ErrorResponse.internal_error())`.
4. **Global handlers** — safety net only.

**Response convention**
All route handlers return `SuccessResponse.ok(data=...)` for reads and `SuccessResponse.created(data=...)` for creates.

**Session management**
Never hold a `Session` outside a repository method or middleware dispatch block. Services and repos must not store the session on `self`.

---

## AI Agent Context

**What this service does:** Creates and manages payment sessions for commerce checkouts. It is the entry point for financial transactions in the LedgerFlow platform.

**Folder ownership:**
- `config/` — infrastructure wiring only; no business logic
- `models/` — schema declarations only; no query methods or business logic
- `repository/` — all database I/O; one class per entity; every method must have try/except
- `services/` — business orchestration; services may call other services but never another service's repository
- `middleware/` — request interception; `RequestLoggerMiddleware` active on all routes
- `schema/` — Pydantic request/response contracts; no business logic
- `routes/` — thin HTTP handlers; call service methods and shape responses only
- `migrations/` — owned by Alembic; only modify via `alembic revision` commands
- `seeders/` — empty; no pre-seeded data
- `utils/common/` — shared contracts (`AppException`, `SuccessResponse`, `ErrorResponse`)
- `utils/enums.py` — Python mirror of PostgreSQL enum types; must stay in sync with migration definitions

**Implemented APIs:**
- `GET /health` — service liveness check
- `POST /api/v1/payment-sessions/initiate` — create a payment session for a checkout

**Major workflows not yet implemented:**
- `GET /api/v1/payment-sessions/{session_id}` — fetch session details
- `POST /api/v1/refunds/initiate` — initiate a refund
- Payment capture / failure status updates
- Session expiry enforcement
- Event consumption: `CheckoutPaymentRequested`
- Event publishing: `PaymentCaptured`, `PaymentFailed`
- Real provider integration

**Rules an AI agent must not break without understanding the wider impact:**
1. **Never remove `create_type=False`** from any `SAEnum` or `PGEnum` column definition.
2. **Never modify an existing migration file** to change already-applied schema. Create a new migration instead.
3. **Never store a `Session` on a repository instance** — sessions are per-request, not per-singleton.
4. **Always use `PGEnum(..., create_type=False)`** (not `sa.Enum`) in migration `op.create_table` calls for enum columns.
5. **Always raise `AppException` subclasses** from service and repository layers — never return `None` to signal failure.
6. **Never access a repository from a service that doesn't own it.**
7. **Never add a database-level FK constraint** from `payment_sessions.checkout_id` or `payment_sessions.user_id` to the commerce schema.
8. **Never rename `services/` to `service/`.**
9. **Never import `User` in `models/__init__.py`** — it must not appear in `Base.metadata` or it will be included in autogenerate output and generate spurious migrations for the `users` table.
10. **Never hardcode the session expiry duration** — always read from `server_config.payment_session_expiry_seconds`.
