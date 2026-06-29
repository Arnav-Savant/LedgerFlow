# Payment Service — Engineering Knowledge Guide

> **Audience:** AI coding agents, new contributors, and the author returning after time away.
> **Scope:** Payment microservice only. For system-wide architecture see `docs/project_structure.md`.
> **Status:** Active development — Payment Session lifecycle and Payment Attempt lifecycle fully implemented with dummy PSP simulation. Kafka, refunds, and outbox are out of scope for this iteration.

---

## Service Overview

The payment service is the financial execution layer of the LedgerFlow platform. It owns everything related to *how* money moves: creating payment sessions for buyers, managing payment attempts against a dummy PSP, tracking state transitions, and (in future) publishing outcome events to commerce and ledger services.

Its boundary starts where commerce ends. Commerce creates a checkout, calls the payment service to create a `PaymentSession`, stores the returned `session_id`, and redirects the frontend to the session URL. The payment service then owns the entire payment execution flow: session retrieval, attempt creation, PSP simulation, and terminal state management.

The payment service is the sole owner of `PaymentSession` and `PaymentAttempt` records.

---

## Current Scope

**Implemented:**

- **Config layer** — `ServerConfig` carries `payment_session_expiry_seconds` (default 900s), `payment_session_max_attempts` (default 3), `psp_simulate_success` (optional bool; unset = random), `payment_frontend_base_url` (default `http://localhost:5173/payments/session`). All overridable via `.env`.
- **Models** — `User` (read-side mirror), `PaymentSession` (with `attempt_count`, `max_attempts`), `PaymentAttempt`.
- **Repositories** — `UserRepo`, `PaymentSessionRepo`, `PaymentAttemptRepo`.
- **Services** — `UserService`, `PaymentSessionService`, `PaymentAttemptService`.
- **Middleware** — `RequestLoggerMiddleware` (all routes), `UserValidationMiddleware` (session initiation only).
- **APIs** — `GET /` (list all sessions), `POST /initiate` (session creation), `GET /{session_id}` (session detail + ui\_state), `POST /{session_id}/attempt` (attempt creation with idempotency).
- **Business rules** — session expiry enforcement, max attempts cap, idempotency, PSP simulation, terminal state immutability.
- **Alembic** — separate `payment_alembic_version` table; `include_object` auto-derived from `Base.metadata`.

**Not yet implemented:**
- Kafka event publishing (`PaymentCaptured`, `PaymentFailed`)
- Transactional outbox
- Refunds
- Commerce callbacks on payment outcome
- Real PSP integration (Razorpay / Stripe)
- Background workers (session expiry sweep)

---

## Architectural Overview

```
HTTP layer (routes)  →  Service layer  →  Repository layer  →  Database
        ↑                     ↑
  Middleware             Domain models
  Schemas                Enums / Exceptions
                         Response envelopes
```

All design principles from the commerce service apply without exception. Key rules:

- **No business logic in repositories.** Repos are purely data access.
- **Every layer has try/except.** Repo → `DatabaseException`. Service → re-raise `AppException`, wrap bare `Exception` as `ServiceException`. Route → `ErrorResponse` with correct status, never propagates to global handler.
- **Repos flush, services commit.** Single `db.commit()` per top-level service operation. All repos call `db.flush()`.
- **Services own cross-domain access via services only.** `PaymentAttemptService` accesses `PaymentSession` data through `PaymentSessionService`, never directly through `PaymentSessionRepo`. `PaymentSessionService` accesses user data through `UserService`. No service may touch another service's repository directly.
- **Routes create service instances per-handler.** No module-level service singletons.
- **Money as integers.** All amounts in smallest denomination.
- **IDs as UUID strings.** `VARCHAR(36)`, application-generated.
- **PGEnum with `create_type=False` in all migrations.** Enum types created via `op.execute("CREATE TYPE ...")`.

---

## Project Structure

### `config/`

- `server_config.py` — `ServerConfig` reads `APP_*` vars:
  - `name` — `payment-service`
  - `port` — `8002`
  - `payment_session_expiry_seconds: int` — default `900`. Env: `APP_PAYMENT_SESSION_EXPIRY_SECONDS`.
  - `payment_session_max_attempts: int` — default `3`. Env: `APP_PAYMENT_SESSION_MAX_ATTEMPTS`.
  - `psp_simulate_success: Optional[bool]` — default `None` (random). Set `"true"` or `"false"` via `APP_PSP_SIMULATE_SUCCESS`.
  - `payment_frontend_base_url: str` — default `http://localhost:5173/payments/session`. Env: `APP_PAYMENT_FRONTEND_BASE_URL`. Used as the base for `redirect_url` — the full URL becomes `{payment_frontend_base_url}/{session_id}`.
- `postgres_config.py` — `PostgresConfig` reads `POSTGRES_*` vars.
- `database.py` — `get_db()` FastAPI dependency.
- `logger.py` — `AppLogger` singleton.

### `models/`

- `base.py` — `Base` + `TimestampMixin` (`created_at`, `updated_at`).
- `user.py` — Read-side mirror of commerce's `User`. Not imported in `__init__.py` (keeps it out of `Base.metadata`, preventing spurious migrations).
- `payment_session.py` — `PaymentSession`:
  - `id: VARCHAR(36)` PK
  - `checkout_id: VARCHAR(36)` — cross-service ref, no FK constraint
  - `user_id: VARCHAR(36)` — cross-service ref, no FK constraint
  - `amount: Integer` — smallest denomination
  - `currency: PGEnum(currency)` — shared with commerce
  - `status: PGEnum(payment_status)` — session lifecycle status
  - `payment_method: PGEnum(payment_method)` — nullable, set when known
  - `redirect_url: VARCHAR(2048)` — built using `session_id`
  - `expires_at: DateTime(timezone=True)` — session TTL
  - `attempt_count: Integer` — default 0, incremented with each attempt
  - `max_attempts: Integer` — set at creation from config, immutable thereafter
  - `created_at`, `updated_at` — from `TimestampMixin`
- `payment_attempt.py` — `PaymentAttempt`:
  - `id: VARCHAR(36)` PK
  - `session_id: VARCHAR(36)` FK → `payment_sessions.id`
  - `idempotency_key: VARCHAR(255)` — composite unique with `session_id`
  - `payment_method: PGEnum(payment_method)`
  - `status: PGEnum(attempt_status)` — `PENDING`, `SUCCESS`, `FAILED`
  - `psp_reference: VARCHAR(255)` — nullable, dummy PSP transaction ID
  - `failure_reason: VARCHAR(1024)` — nullable
  - `created_at`, `updated_at`
- `__init__.py` — imports `PaymentSession`, `PaymentAttempt`. **Do not import `User` here.**

### `repository/`

- `user_repo.py` — `UserRepo`: read-only in practice for payment service.
- `payment_session_repo.py` — `PaymentSessionRepo`:
  - `create(db, checkout_id, user_id, amount, currency, redirect_url, expires_at, max_attempts)` → `PaymentSession`
  - `get_by_id(db, session_id)` → `PaymentSession` (raises `NotFoundException`)
  - `get_by_checkout_id(db, checkout_id)` → `Optional[PaymentSession]`
  - `get_all_by_user_id(db, user_id, skip, limit)` → `list[PaymentSession]`
  - `get_all(db, skip, limit)` → `list[PaymentSession]` — returns all sessions ordered by `created_at` descending. Used by the list endpoint.
  - `update_status(db, session_id, status)` → `PaymentSession`
  - `increment_attempt_count(db, session_id)` → `PaymentSession`
  - `delete(db, session_id)` → `None`
- `payment_attempt_repo.py` — `PaymentAttemptRepo`:
  - `create(db, session_id, idempotency_key, payment_method)` → `PaymentAttempt` (status=PENDING)
  - `get_by_id(db, attempt_id)` → `PaymentAttempt` (raises `NotFoundException`)
  - `get_by_idempotency_key(db, session_id, idempotency_key)` → `Optional[PaymentAttempt]`
  - `get_all_by_session_id(db, session_id)` → `list[PaymentAttempt]`
  - `update_status(db, attempt_id, status, psp_reference=None, failure_reason=None)` → `PaymentAttempt`

### `migrations/`

- `env.py` — `include_object` derives owned tables from `Base.metadata`. Separate `payment_alembic_version` table.
- `versions/87f32a03d60c` — initial: creates `payment_status`, `payment_method` enums and `payment_sessions` table.
- `versions/<new>` — adds `SUCCESS`, `EXPIRED` to `payment_status`; adds `attempt_count`, `max_attempts` to `payment_sessions`; creates `attempt_status` enum; creates `payment_attempts` table.

### `utils/`

#### `utils/enums.py`

- `PaymentStatus` — **Session lifecycle**: `INITIATED`, `SUCCESS`, `FAILED`, `EXPIRED`, `CANCELLED`. Legacy values `PENDING`, `CAPTURED`, `REFUND_INITIATED`, `REFUNDED` remain in DB enum for backward compat but are not used for sessions.
- `AttemptStatus` — **Attempt lifecycle**: `PENDING`, `SUCCESS`, `FAILED`.
- `PaymentMethod` — `UPI`, `CARD`, `NET_BANKING`, `WALLET`.
- `Currency` — `INR`, `USD`, `GBP`, `EUR`, `JPY`.
- `RefundStatus` — `INITIATED`, `PROCESSED`, `FAILED` (future use).

#### `utils/common/`

- `custom_exception.py` — `AppException` hierarchy: `NotFoundException`, `ConflictException`, `ValidationException`, `DatabaseException`, `ServiceException`, `PaymentException`.
- `success_response.py`, `error_response.py` — unchanged.

### `services/`

Note: directory is named `services/` (plural). Do not rename.

- `user_service.py` — `UserService.get_by_id()`.
- `payment_session_service.py` — `PaymentSessionService`:
  - `__init__` — creates `PaymentSessionRepo`, `UserService`.
  - `initiate_session(db, checkout_id, user_id, amount, currency)`:
    1. Validates user via `UserService`.
    2. Computes `expires_at = now(UTC) + timedelta(seconds=server_config.payment_session_expiry_seconds)`.
    3. Builds `redirect_url = f"{server_config.payment_frontend_base_url}/{session.id}"` — uses **session id**, not checkout id. Defaults to `http://localhost:5173/payments/session/{session_id}`.
    4. Creates session with `max_attempts = server_config.payment_session_max_attempts`.
    5. Commits. Returns `{"session_id", "redirect_url"}`.
  - `list_all(db, skip, limit)`:
    1. Logs `logger.info("Fetching all payment sessions", ...)`.
    2. Calls `payment_session_repo.get_all(db, skip, limit)`.
    3. For each session: computes `ui_state`, `can_retry`, and serializes enum fields with `.value` (so `status` and `currency` are strings, not enum objects).
    4. Returns `list[dict]` with fields: `session_id, checkout_id, user_id, status, amount, currency, attempt_count, max_attempts, expires_at, ui_state, can_retry, redirect_url, created_at`.
    5. Route validates each dict through `PaymentSessionListItemResponse` before returning.
  - `get_session(db, session_id)`:
    1. Fetches session.
    2. Checks expiry: if `now(UTC) > expires_at` and status not already terminal → updates status to `EXPIRED`, commits.
    3. Fetches all attempts for the session.
    4. Computes `ui_state` and `can_retry`.
    5. Returns structured dict for the GET response.
- `payment_attempt_service.py` — `PaymentAttemptService`:
  - `__init__` — creates `PaymentAttemptRepo`, `PaymentSessionService`.
  - `create_attempt(db, session_id, idempotency_key, payment_method)`:

    **Validation (raises before any write):**
    1. Fetch session — `NotFoundException` if missing.
    2. If `now(UTC) > session.expires_at` and not terminal → update session to `EXPIRED`, commit, raise `ValidationException`.
    3. If `session.status` in `{SUCCESS, FAILED, EXPIRED, CANCELLED}` → raise `ValidationException`.
    4. If `session.attempt_count >= session.max_attempts` → raise `ValidationException`.

    **Idempotency check:**
    5. `attempt_repo.get_by_idempotency_key(db, session_id, idempotency_key)` → if found, return immediately (no write).

    **Execution (all flushed, one commit at end):**
    6. `attempt_repo.create()` → PENDING attempt.
    7. `session_service.increment_attempt_count()`.
    8. Simulate PSP via `_simulate_psp()` → `True` (success) or `False` (failure).
    9. If success: `attempt_repo.update_status(PENDING→SUCCESS, psp_reference=<dummy>)`, `session_service.mark_success()`.
    10. If failure: `attempt_repo.update_status(PENDING→FAILED, failure_reason=<reason>)`. If `attempt_count >= max_attempts`: `session_service.mark_failed()`.
    11. `db.commit()`.
    12. Returns `{"attempt_id", "status", "failure_reason", "session_status"}`.

    **`_simulate_psp()`:** reads `server_config.psp_simulate_success`. If `True` → always succeed. If `False` → always fail. If `None` → `random.choice([True, False])`.

### `schema/`

- `payment_session_schema.py`:
  - `PaymentSessionInitiateRequest` — `checkout_id`, `user_id`, `amount`, `currency`.
  - `PaymentSessionInitiateResponse` — `session_id`, `redirect_url`.
  - `AttemptSummary` — `attempt_id`, `status`, `failure_reason`, `created_at`.
  - `PaymentSessionDetailResponse` — `session_id`, `status`, `amount`, `currency`, `payment_method`, `attempt_count`, `max_attempts`, `expires_at`, `ui_state`, `can_retry`, `attempts: list[AttemptSummary]`.
  - `PaymentSessionListItemResponse` — `session_id`, `checkout_id`, `user_id`, `status`, `amount`, `currency`, `attempt_count`, `max_attempts`, `expires_at`, `ui_state`, `can_retry`, `redirect_url`, `created_at`. Used by the `GET /` list endpoint for schema-validated responses.
- `payment_attempt_schema.py`:
  - `PaymentAttemptRequest` — `idempotency_key: str`, `payment_method: PaymentMethod`.
  - `PaymentAttemptResponse` — `attempt_id`, `status`, `failure_reason`, `session_status`.

### `routes/`

- `payment_session_routes.py`:
  - `GET /payment-sessions/` — list all sessions (`skip`/`limit` query params). Returns summary dicts ordered by `created_at` desc.
  - `POST /payment-sessions/initiate` — create session. Guarded by `UserValidationMiddleware`.
  - `GET /payment-sessions/{session_id}` — fetch session detail with `ui_state`.
- `payment_attempt_routes.py`:
  - `POST /payment-sessions/{session_id}/attempt` — create attempt (idempotent on `idempotency_key`).

### `middleware/`

- `request_logger.py` — `RequestLoggerMiddleware` — all routes.
- `user_validation.py` — `UserValidationMiddleware` — `POST /api/v1/payment-sessions/initiate` only.

### `main.py`

Registers `CORSMiddleware` (all origins, all methods) first, then `RequestLoggerMiddleware`, then `UserValidationMiddleware`. `CORSMiddleware` must be registered before the logger and user-validation middleware so preflight OPTIONS requests are handled without going through the full middleware stack. Includes both routers under `/api/v1`.

---

## Request and Data Flow

### `GET /api/v1/payment-sessions/`

```
1. PaymentSessionService.list_all(db, skip, limit)
   └─ payment_session_repo.get_all() — ordered by created_at desc
2. Returns SuccessResponse.ok([{session_id, checkout_id, status, amount, ...}, ...])
```

### `POST /api/v1/payment-sessions/initiate`

```
1. UserValidationMiddleware — validates user_id exists
2. RequestLoggerMiddleware — logs request
3. Route validates PaymentSessionInitiateRequest
4. PaymentSessionService.initiate_session()
   a. UserService.get_by_id()          → 404 if not found
   b. expires_at = now(UTC) + expiry_seconds
   c. payment_session_repo.create()    → INITIATED, attempt_count=0
   d. redirect_url = "…/session/{session.id}"
   e. db.commit()
5. Returns SuccessResponse.created({session_id, redirect_url})
```

### `GET /api/v1/payment-sessions/{session_id}`

```
1. RequestLoggerMiddleware — logs request
2. PaymentSessionService.get_session()
   a. payment_session_repo.get_by_id() → 404 if not found
   b. If now(UTC) > expires_at and not terminal → update to EXPIRED, commit
   c. payment_attempt_repo.get_all_by_session_id()
   d. Compute ui_state + can_retry
3. Returns SuccessResponse.ok(PaymentSessionDetailResponse)
```

### `POST /api/v1/payment-sessions/{session_id}/attempt`

```
1. RequestLoggerMiddleware — logs request
2. Route validates PaymentAttemptRequest (idempotency_key, payment_method)
3. PaymentAttemptService.create_attempt()
   a. Fetch session → 404 if not found
   b. Expiry check → EXPIRED if past, ValidationException
   c. Status check → ValidationException if terminal
   d. Max attempts check → ValidationException
   e. Idempotency check → return existing attempt if key exists (no write)
   f. attempt_repo.create()                    → PENDING attempt (flush)
   g. session_service.increment_attempt_count() (flush)
   h. _simulate_psp()                           → True or False
   i. attempt_repo.update_status()              → SUCCESS or FAILED (flush)
   j. If SUCCESS: session_service.mark_success() (flush)
      If FAILED + exhausted: session_service.mark_failed() (flush)
   k. db.commit()
4. Returns SuccessResponse.created({attempt_id, status, failure_reason, session_status})
```

---

## `ui_state` Derivation

Computed in `PaymentSessionService.get_session()`, returned in `PaymentSessionDetailResponse`.

| Condition | `ui_state` | `can_retry` |
|-----------|-----------|------------|
| `now > expires_at` or `status == EXPIRED` | `EXPIRED` | `false` |
| `status == SUCCESS` | `SUCCESS` | `false` |
| `status == FAILED` (terminal) | `FAILED` | `false` |
| `status == CANCELLED` | `FAILED` | `false` |
| `status == INITIATED`, `attempt_count == 0` | `PAYMENT_PAGE` | `true` |
| `status == INITIATED`, `attempt_count > 0` | `RETRY` | `true` |

The frontend never infers state from raw fields — it reads `ui_state` directly.

---

## Core Domain Concepts

**PaymentSession** — The root entity for a payment. One checkout maps to one active session. Carries session-level state (`status`, `attempt_count`, `max_attempts`, `expires_at`). Is the parent of all `PaymentAttempt` records. Once `SUCCESS`, it is immutable with respect to payment execution.

**PaymentAttempt** — One execution of the payment process. A session may have multiple attempts (up to `max_attempts`). Each attempt represents a single user action (one click of "Pay"). Idempotency is enforced per `(session_id, idempotency_key)`.

**PaymentStatus (session):** `INITIATED` → `SUCCESS` (terminal) or `FAILED` (terminal). `EXPIRED` and `CANCELLED` are also terminal. A session with failed attempts and retries remaining stays `INITIATED`.

**AttemptStatus:** `PENDING` → `SUCCESS` or `FAILED`.

**Session expiry** — TTL enforced lazily on read (`GET /payment-sessions/{session_id}`) and on write (`POST /{session_id}/attempt`). No background sweep yet.

**Idempotency** — Same `(session_id, idempotency_key)` pair returns the existing attempt without DB write. Frontend generates a new key per retry, creating a new attempt.

---

## Business Rules

1. Completed sessions (`SUCCESS`, `FAILED`, `EXPIRED`, `CANCELLED`) cannot create new attempts.
2. Expired sessions are detected and marked `EXPIRED` on first access after TTL.
3. `attempt_count >= max_attempts` prevents new attempts even if session is `INITIATED`.
4. Duplicate `idempotency_key` for the same session returns the existing attempt (no duplicate record created).
5. A successful attempt transitions the session to `SUCCESS` — no further attempts allowed.
6. A failed attempt with retries remaining leaves the session `INITIATED`.
7. A failed attempt that exhausts retries transitions the session to `FAILED` (terminal).
8. All mutations for a single `create_attempt` call are committed in one transaction.

---

## Integration Points

**Commerce service (synchronous HTTP, implemented)**
Commerce calls `POST /api/v1/payment-sessions/initiate` during checkout. Payment service returns `session_id` and `redirect_url`. Commerce stores `payment_session_id` on the checkout row.

**External payment providers (planned)**
Replace `_simulate_psp()` with a real Razorpay / Stripe SDK call. `psp_reference` stores the provider's transaction ID.

**Event publishing (planned)**
After `create_attempt` commits a terminal status, publish `PaymentSucceeded` or `PaymentFailed` to Kafka via transactional outbox. Commerce and ledger services consume these events to update order status and ledger entries.

**PostgreSQL (primary store)**
Same `ledgerflow` database as commerce. Payment owns `payment_sessions` and `payment_attempts`. `users` table is shared read-only.

---

## Important Architectural Decisions

**`redirect_url` is configurable via `payment_frontend_base_url`**
The `redirect_url` returned on session initiation is built as `{payment_frontend_base_url}/{session_id}`. The base URL defaults to `http://localhost:5173/payments/session` (the local Vite dev server). Override `APP_PAYMENT_FRONTEND_BASE_URL` in `.env` for staging/production environments. The URL uses `session_id` (not `checkout_id`) so the frontend is decoupled from the commerce domain.

**`max_attempts` stored on the session row**
Set at creation from `server_config.payment_session_max_attempts`. Stored in the DB so changing the config does not retroactively affect in-flight sessions.

**Session expiry enforced lazily**
`expires_at` is checked on every read and write. No background sweep. An expired session is marked `EXPIRED` on first access. This is acceptable for this iteration; a sweep worker should be added later to handle sessions that are never re-fetched.

**PSP simulation is synchronous**
No background workers, no queues. The entire attempt lifecycle (create → PSP → update → commit) completes within the HTTP request. `PROCESSING` is therefore not a needed session status.

**Idempotency at service layer, enforced by DB unique constraint**
The service checks for an existing attempt before creating a new one. The DB unique constraint on `(session_id, idempotency_key)` is a safety net against concurrent race conditions.

**`attempt_count` incremented before PSP call**
This ensures that even if the PSP call itself fails with an exception (not a PSP failure response), the attempt count is still recorded and the session is protected from runaway retries.

**Separate Alembic version table**
`payment_alembic_version` is independent from commerce's `alembic_version`.

---

## Operational Considerations

**Configuration — key env vars**
```
APP_PAYMENT_SESSION_EXPIRY_SECONDS=900
APP_PAYMENT_SESSION_MAX_ATTEMPTS=3
APP_PSP_SIMULATE_SUCCESS=                                        # unset = random; "true" = always succeed; "false" = always fail
APP_PAYMENT_FRONTEND_BASE_URL=http://localhost:5173/payments/session  # override for staging/prod
```

**Running the service**
```
cd services/payment-service
python main.py
```
Port `8002`. PostgreSQL must be reachable on startup.

---

## Known Constraints

- **Dummy PSP.** `_simulate_psp()` uses random or config-driven outcomes. No real provider.
- **Lazy expiry.** Expired sessions are only marked `EXPIRED` when accessed. A session that is never re-fetched after TTL remains `INITIATED` in the DB.
- **No Kafka.** Payment outcome events are not published. Commerce and ledger services are not notified of payment results.
- **Single currency per session.** Mixed-currency checkouts use the first product's currency.
- **`User` model not in `Base.metadata`.** `user_repo.py` imports `User` directly from `models/user.py`. Never import it in `models/__init__.py`.
- **`onupdate` is ORM-only.** Raw SQL `UPDATE` must set `updated_at = now()` manually.
- **`services/` not `service/`.** Do not rename to match commerce.

---

## Development Notes

**Adding a new model**
Create in `models/`, import in `models/__init__.py`, run `alembic revision --autogenerate`. Fix enum columns to use `PGEnum(..., create_type=False)` and add `op.execute("CREATE TYPE ...")` manually.

**Changing session expiry or max attempts**
Edit `.env` and restart. Only affects newly created sessions — existing sessions retain the values stored on their row.

**Error handling convention**
1. Repo — `SQLAlchemyError` → `DatabaseException`. Domain failures raise `AppException` subclasses.
2. Service — re-raises `AppException`; wraps bare `Exception` as `ServiceException`. Calls `db.rollback()` before re-raising.
3. Routes — `AppException` → `JSONResponse(exc.status_code, ErrorResponse.from_exception(exc))`. Bare `Exception` → 500.
4. Global handlers in `main.py` — safety net only.

---

## AI Agent Context

**What this service does:** Creates payment sessions for commerce checkouts, manages payment attempt lifecycle with idempotency, simulates PSP outcomes, enforces session business rules (expiry, max attempts, terminal state immutability).

**Folder ownership:**
- `config/` — infrastructure wiring; no business logic
- `models/` — schema only; no query logic on model classes
- `repository/` — all DB I/O; every method has try/except
- `services/` — orchestration; services call other services, never another service's repo
- `middleware/` — `RequestLoggerMiddleware` (all), `UserValidationMiddleware` (initiate only)
- `schema/` — Pydantic contracts; no business logic
- `routes/` — thin handlers; shape request/response only
- `migrations/` — Alembic only; never edit applied migrations

**Implemented APIs:**
- `GET /api/v1/payment-sessions/` — list all sessions (skip/limit)
- `POST /api/v1/payment-sessions/initiate` — create session (redirect_url uses configurable base URL)
- `GET /api/v1/payment-sessions/{session_id}` — session detail with `ui_state`
- `POST /api/v1/payment-sessions/{session_id}/attempt` — create attempt (idempotent)
- `GET /health`

**Rules an AI agent must not break:**
1. Never remove `create_type=False` from `PGEnum`.
2. Never modify an applied migration. Create a new one.
3. Never store a `Session` on a repo instance.
4. Never use `sa.Enum` in migrations — always `PGEnum(..., create_type=False)`.
5. Never return `None` from service/repo to signal failure — raise `AppException` subclasses.
6. Never access another service's repository directly.
7. Never add DB-level FK constraints from `payment_sessions` to commerce tables.
8. Never rename `services/` to `service/`.
9. Never import `User` in `models/__init__.py`.
10. Never hardcode session expiry, max attempts, PSP behavior, or `redirect_url` base — always read from `server_config`.
11. Never allow a second attempt for a `SUCCESS` session — it is immutable.
12. Never create a duplicate attempt for the same `(session_id, idempotency_key)` — return the existing one.
13. Never call a repository directly from a route handler — all data access flows through the service layer.
14. Every route handler must log at entry with `logger.info`, log on success, and log in all except blocks (`logger.error` for `AppException`, `logger.exception` for bare `Exception`).
15. Every route response must be serialized through a Pydantic schema and returned via `.model_dump()` — never raw dicts.
16. Every service method must call `logger.info` at entry with relevant context. Use `logger.exception` in bare `except Exception` blocks to capture the stack trace. Enum fields in returned dicts must be serialized with `.value` — never raw enum objects.
