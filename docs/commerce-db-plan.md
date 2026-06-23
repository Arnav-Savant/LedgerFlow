# Commerce Service — Database Implementation Plan

> **Status:** Plan (pre-implementation)
> **Scope:** Models, migrations, seeders, and repository layer for the Commerce service.
> **Audience:** Anyone implementing or reviewing this service's data layer. Written to be reusable as a reference for similar database setups.

---

## Table of Contents

1. [What This Plan Covers](#1-what-this-plan-covers)
2. [Folder Structure After Implementation](#2-folder-structure-after-implementation)
3. [Database Design](#3-database-design)
4. [UUID as Primary Key — Why and How](#4-uuid-as-primary-key--why-and-how)
5. [Enums](#5-enums)
6. [SQLAlchemy Base and Shared Mixins](#6-sqlalchemy-base-and-shared-mixins)
7. [Alembic — Migration Tracking](#7-alembic--migration-tracking)
8. [Auto-Apply Migrations on Startup](#8-auto-apply-migrations-on-startup)
9. [Seeder Strategy](#9-seeder-strategy)
10. [Repository Layer](#10-repository-layer)
11. [Startup Sequence End to End](#11-startup-sequence-end-to-end)
12. [Operational Commands Reference](#12-operational-commands-reference)

---

## 1. What This Plan Covers

This plan describes how the Commerce service manages its database:

- **Models** — SQLAlchemy ORM definitions for each table the service owns.
- **Migrations** — How schema changes are tracked over time using Alembic, so that anyone pulling the repository always ends up with the correct database state.
- **Auto-apply** — How the service applies pending migrations automatically when it starts, so no manual database setup is required before running the service.
- **Seeders** — How realistic baseline data (users, sellers, products, inventory) is inserted once on first boot and never duplicated.
- **Repository layer** — A clean data access pattern where each model has its own CRUD file, keeping raw SQL and query logic out of service classes.

---

## 2. Folder Structure After Implementation

```
services/commerce-service/
│
├── models/
│   ├── __init__.py               # Imports all models so Alembic can discover them
│   ├── base.py                   # DeclarativeBase + TimestampMixin
│   ├── user.py                   # User table
│   ├── seller.py                 # Seller table
│   ├── product.py                # Product table
│   ├── inventory.py              # Inventory table
│   ├── checkout.py               # Checkout table
│   └── order.py                  # Order table
│
├── utils/
│   └── enums.py                  # CheckoutStatus, OrderStatus, Currency enums
│
├── migrations/                   # Alembic home
│   ├── env.py                    # Alembic runtime config — connects to DB, imports models
│   ├── script.py.mako            # Template for generated migration files
│   └── versions/                 # One file per migration, named by revision ID
│       └── 0001_initial_schema.py
│
├── seeders/
│   ├── __init__.py
│   ├── seed_data.py              # Static seed definitions (users, sellers, products)
│   └── runner.py                 # Idempotent seeder — checks before inserting
│
├── repository/
│   ├── __init__.py
│   ├── user_repo.py
│   ├── seller_repo.py
│   ├── product_repo.py
│   ├── inventory_repo.py
│   ├── checkout_repo.py
│   └── order_repo.py
│
├── alembic.ini                   # Alembic configuration file
└── main.py                       # Runs migrations + seeders before starting FastAPI
```

---

## 3. Database Design

### 3.1 Users

Represents a customer who can initiate checkouts.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key, application-generated |
| `name` | VARCHAR | Full name |
| `email` | VARCHAR | Unique |
| `phone` | VARCHAR | Optional |
| `created_at` | TIMESTAMPTZ | Set by mixin |
| `updated_at` | TIMESTAMPTZ | Set by mixin |

---

### 3.2 Sellers

Represents a merchant whose products can be purchased.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Business name |
| `email` | VARCHAR | Unique |
| `created_at` | TIMESTAMPTZ | Set by mixin |
| `updated_at` | TIMESTAMPTZ | Set by mixin |

---

### 3.3 Products

Represents a purchasable item listed by a seller.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `seller_id` | UUID | FK → sellers.id |
| `name` | VARCHAR | Product name |
| `price` | INTEGER | Stored in paise/cents — no floats |
| `currency` | VARCHAR | e.g. `INR`, `USD` |
| `created_at` | TIMESTAMPTZ | Set by mixin |
| `updated_at` | TIMESTAMPTZ | Set by mixin |

> **Money rule:** All monetary values are integers representing the smallest denomination (paise for INR, cents for USD). Never store money as a float. `499.00` is stored as `49900`.

---

### 3.4 Inventory

Tracks stock for each product. One row per product.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `product_id` | UUID | FK → products.id, unique |
| `available_quantity` | INTEGER | Stock available for new reservations |
| `reserved_quantity` | INTEGER | Stock reserved but not yet committed (defaults to 0) |
| `created_at` | TIMESTAMPTZ | Set by mixin |
| `updated_at` | TIMESTAMPTZ | Set by mixin |

`available_quantity + reserved_quantity = total physical stock`. When a checkout is created, stock moves from `available` to `reserved`. On payment success it is consumed (reserved decrements). On payment failure it is released back to available.

---

### 3.5 Checkouts

Represents a customer's intent to purchase, before payment is confirmed.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → users.id |
| `product_id` | UUID | FK → products.id |
| `seller_id` | UUID | FK → sellers.id |
| `coupon_id` | UUID | Nullable — applied coupon, if any |
| `total_amount` | INTEGER | Pre-discount total in smallest denomination |
| `final_amount` | INTEGER | Post-discount amount actually charged |
| `status` | ENUM | `CheckoutStatus` — see section 5 |
| `created_at` | TIMESTAMPTZ | Set by mixin |
| `updated_at` | TIMESTAMPTZ | Set by mixin |

---

### 3.6 Orders

Created from a checkout once payment is confirmed.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `checkout_id` | UUID | FK → checkouts.id |
| `user_id` | UUID | FK → users.id |
| `product_id` | UUID | FK → products.id |
| `seller_id` | UUID | FK → sellers.id |
| `amount` | INTEGER | Final charged amount |
| `currency` | VARCHAR | e.g. `INR` |
| `order_status` | ENUM | `OrderStatus` — see section 5 |
| `checkout_status` | ENUM | Snapshot of checkout status at order creation |
| `ledger_updated` | BOOLEAN | `False` until Ledger confirms entry posted |
| `wallet_updated` | BOOLEAN | `False` until Wallet confirms balance updated |
| `created_at` | TIMESTAMPTZ | Set by mixin |
| `updated_at` | TIMESTAMPTZ | Set by mixin |

`ledger_updated` and `wallet_updated` are flags updated by the event consumers in this service when they receive confirmation events from the Ledger service. They are not set synchronously during order creation.

---

## 4. UUID as Primary Key — Why and How

Sequential integer IDs (1, 2, 3…) are the default in most databases, but they carry problems for distributed and financial systems:

- They reveal business volume. An outsider can infer how many orders exist by watching IDs increment.
- They create ordering coupling. Systems sometimes (incorrectly) depend on `id` order implying time order, which breaks under concurrent inserts.
- They complicate horizontal scaling. Two services generating sequential IDs will collide. UUIDs are statistically unique without coordination.

**Implementation:** Every model sets `id` as a UUID column with a default generated in Python (`uuid.uuid4()`), not in the database. Generating it in the application means the ID is known before the `INSERT` completes, which simplifies repository code and logging.

```
Column definition pattern:
id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
)
```

The `default=uuid.uuid4` (without parentheses) tells SQLAlchemy to call `uuid4()` each time a new row is created.

---

## 5. Enums

All status fields use Python `Enum` subclasses stored as native PostgreSQL enum types. Raw strings scattered through the codebase are not acceptable — the enum class is the single source of truth for valid states.

**Location:** `utils/enums.py`

### CheckoutStatus

| Value | Meaning |
|---|---|
| `PENDING` | Checkout created, payment not yet initiated |
| `PAYMENT_INITIATED` | Payment session created |
| `COMPLETED` | Payment captured, order created |
| `EXPIRED` | Checkout timed out before payment |
| `CANCELLED` | Explicitly cancelled by the user |

### OrderStatus

| Value | Meaning |
|---|---|
| `CREATED` | Order record exists, payment just captured |
| `CONFIRMED` | Ledger and wallet updated, order fully committed |
| `CANCELLED` | Order cancelled before fulfilment |
| `REFUND_INITIATED` | Refund requested |
| `REFUNDED` | Refund completed |

### Currency

| Value | Notes |
|---|---|
| `INR` | Indian Rupee |
| `USD` | US Dollar |

SQLAlchemy maps Python enums to PostgreSQL native enum types. This means invalid status values are rejected at the database level, not just the application level.

---

## 6. SQLAlchemy Base and Shared Mixins

**Location:** `models/base.py`

All models inherit from a single `DeclarativeBase`. This is required for Alembic to discover and track all models automatically.

A `TimestampMixin` is defined once and mixed into every model. It adds `created_at` and `updated_at` columns using `server_default=func.now()` and `onupdate=func.now()` respectively. This means the database sets these values — they are never set manually in application code.

```
Inheritance pattern:
class Checkout(TimestampMixin, Base):
    __tablename__ = "commerce_checkouts"
    ...
```

All table names are prefixed with `commerce_` to reflect service ownership when sharing a single database with other services.

---

## 7. Alembic — Migration Tracking

### What Alembic does

Alembic is a database migration tool that tracks the history of your schema as a versioned chain of migration files. Each file represents a delta — what to add, modify, or remove — and Alembic maintains a table called `alembic_version` in your database that records which revision was last applied.

When you run `alembic upgrade head`, Alembic:
1. Reads the `alembic_version` table to find the current revision.
2. Finds all unapplied migration files in `migrations/versions/`.
3. Applies them in order until the latest (`head`) is reached.

This means the database always converges to the correct schema regardless of its current state.

### Initial setup

Alembic is initialized once with:
```
alembic init migrations
```

This creates the `migrations/` folder and `alembic.ini`. After initialization, two things must be configured manually:

**`alembic.ini`** — The `sqlalchemy.url` key is set to a placeholder. We override this in `env.py` by reading from `PostgresConfig` instead, so credentials never live in `alembic.ini`.

**`migrations/env.py`** — This file is edited to:
1. Import the `PostgresConfig` and construct the database URL dynamically.
2. Import `Base` (the `DeclarativeBase`) from `models/base.py`.
3. Set `target_metadata = Base.metadata` so Alembic can compare the current database schema against the declared models and generate accurate diffs.

### Generating a migration

When a model is added or changed:
```
alembic revision --autogenerate -m "describe what changed"
```

Alembic compares `Base.metadata` (what the models declare) against the live database schema and generates a migration file in `migrations/versions/`. The generated file contains `upgrade()` and `downgrade()` functions. Always review the generated file before committing — autogenerate can miss some changes (like index renames or constraints on existing columns).

### Applying migrations

```
alembic upgrade head        # Apply all unapplied migrations
alembic downgrade -1        # Roll back one migration
alembic current             # Show current revision
alembic history             # Show full migration chain
```

### Migration file naming

Alembic generates a random hex revision ID for each file. It is useful to also use the `-m` message to make files human-readable:
```
migrations/versions/3a8f21cc1d04_initial_schema.py
migrations/versions/7e91b30a4421_add_coupon_table.py
```

The `alembic_version` table in PostgreSQL stores only the revision ID (the hex prefix), so the human-readable suffix is purely for developer navigation.

---

## 8. Auto-Apply Migrations on Startup

Rather than requiring engineers to run `alembic upgrade head` manually before starting the service, `main.py` runs migrations programmatically as part of the lifespan startup hook.

### How it works

Alembic exposes a Python API that can be called from application code:

```
from alembic.config import Config
from alembic import command

def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "revision")
```

This is called once at server startup before any request is handled. If the database is already at the latest revision, `alembic upgrade head` is a no-op — it detects that `alembic_version` matches `head` and exits immediately. There is no risk of re-running migrations.

### Why this is appropriate here

In a production system with multiple replicas, auto-running migrations at service startup is dangerous — several instances might attempt to run migrations simultaneously. PostgreSQL's advisory locks or a dedicated migration job would be used instead.

For this project, there is one instance per service, so startup migration is safe and removes a manual step. This is a deliberate tradeoff for simplicity in a development/portfolio context.

---

## 9. Seeder Strategy

### What seeders are for

Seeders populate the database with realistic baseline data: a set of users, sellers, products, and corresponding inventory records. This data is needed to exercise the full checkout-to-order flow without manually inserting rows first.

### Location

```
seeders/
├── seed_data.py     # Static definitions: lists of dicts describing each row
└── runner.py        # Reads seed_data.py and inserts rows idempotently
```

### Idempotency — the core requirement

The seeder must be safe to call on every startup. If the data already exists, it must not insert duplicate rows. The pattern is:

1. Before inserting any seed row, query the table by a natural identifier (e.g., email for users, product name + seller ID for products).
2. If the row exists, skip it.
3. If it does not exist, insert it.

This check-before-insert approach means the seeder is safe to run on cold start (empty database), warm restart (database has some data), and repeated restarts (all data exists). It never inserts duplicate rows and never raises a conflict error.

### Seed data design

**Users:** Three realistic user records with names, emails, and phone numbers.

**Sellers:** Two seller records — representing distinct merchants.

**Products:** Four to six products spread across sellers, with realistic names and prices in paise (e.g., a product priced at ₹499 is stored as `49900`).

**Inventory:** One inventory row per product. `available_quantity` starts at a realistic value (e.g., 100). `reserved_quantity` starts at `0` for all products. The `product_id` foreign key links back to the product inserted in the same seeding run.

### Execution order matters

Seeders must run in dependency order:
1. Users (no foreign keys)
2. Sellers (no foreign keys)
3. Products (depends on sellers)
4. Inventory (depends on products)

The runner enforces this order explicitly.

### When the seeder runs

The seeder runs after migrations complete, inside the same lifespan startup hook in `main.py`:

```
startup sequence:
  1. run_migrations()    → ensures schema is current
  2. run_seeders()       → ensures baseline data exists
  3. app starts          → begins handling requests
```

---

## 10. Repository Layer

### Purpose

The repository layer is the only place in the service that issues database queries. Service classes call repository methods; they never construct queries themselves. This separation means business logic and database access can be changed independently, and repositories are straightforward to mock in unit tests.

### One file per model

```
repository/
├── user_repo.py
├── seller_repo.py
├── product_repo.py
├── inventory_repo.py
├── checkout_repo.py
└── order_repo.py
```

Each file contains one repository class named after its model (e.g., `CheckoutRepo`, `InventoryRepo`).

### Standard CRUD operations per repository

Every repository implements at minimum:

| Method | Description |
|---|---|
| `create(session, data)` | Insert a new row, return the created model instance |
| `get_by_id(session, id)` | Fetch one row by UUID primary key, return `None` if not found |
| `get_all(session)` | Fetch all rows (with optional limit/offset for pagination) |
| `update(session, id, data)` | Apply partial updates to an existing row, return updated instance |
| `delete(session, id)` | Delete a row by primary key |

Domain-specific queries are added as additional methods on the same class. For example, `CheckoutRepo` would have `get_by_user_id(session, user_id)` and `InventoryRepo` would have `get_by_product_id(session, product_id)`.

### Session handling

Repositories accept a `session` argument rather than creating one themselves. The session is created by the FastAPI dependency injector (`dependencies.py`) and passed through the call chain: router → service → repository. This means the transaction boundary is controlled at the service layer, and multiple repository calls within the same service method participate in the same transaction.

### Why no async yet at this stage

The repository pattern described here uses synchronous SQLAlchemy sessions for simplicity during initial implementation. The service can be migrated to async sessions (`AsyncSession` with `asyncpg`) later without changing the repository interface — only the session factory and the `await` keywords inside repository methods need to change.

---

## 11. Startup Sequence End to End

When `python main.py` is executed, the following happens in order:

```
1. ServerConfig and PostgresConfig are loaded from .env
   └─ If a required variable is missing or invalid, startup fails immediately with a clear error

2. AppLogger is initialized
   └─ Log level is set from APP_LOG_LEVEL

3. FastAPI app is created

4. Lifespan context begins:

   a. run_migrations()
      └─ Alembic connects to PostgreSQL using POSTGRES_* config
      └─ Reads alembic_version table
      └─ Applies any unapplied migration files from migrations/versions/
      └─ If already at head: no-op, proceeds immediately
      └─ Logs: "Migrations applied" or "Already at head"

   b. run_seeders()
      └─ Opens a database session
      └─ Runs seed check for Users → inserts if missing
      └─ Runs seed check for Sellers → inserts if missing
      └─ Runs seed check for Products → inserts if missing
      └─ Runs seed check for Inventory → inserts if missing
      └─ Logs: "Seeded N rows" or "Seed data already present, skipping"
      └─ Session committed, closed

5. Uvicorn begins serving requests on APP_HOST:APP_PORT

6. GET /health returns 200 immediately — no warm-up needed
```

On shutdown (SIGTERM), the lifespan context exits cleanly. No database teardown is needed since the connection pool is managed by SQLAlchemy and released automatically.

---

## 12. Operational Commands Reference

### First-time setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL
docker compose up -d postgres

# Run the service (migrations + seeders + server, all in one)
python main.py
```

### Schema changes (adding a table or column)

```bash
# 1. Edit or add a model in models/
# 2. Generate the migration
alembic revision --autogenerate -m "describe the change"

# 3. Review the generated file in migrations/versions/
# 4. Apply it
alembic upgrade head

# Or simply restart the service — startup will apply it automatically
python main.py
```

### Inspecting migration state

```bash
alembic current      # What revision is the database at?
alembic history      # Full chain of migrations
alembic heads        # Latest revision (what "head" points to)
```

### Rolling back

```bash
alembic downgrade -1          # Roll back one step
alembic downgrade base        # Roll back everything (destructive)
```

### Resetting the database (development only)

```bash
docker compose down -v        # Destroys the postgres_data volume
docker compose up -d postgres # Fresh PostgreSQL instance
python main.py                # Migrations + seeders run from scratch
```

---

## Key Decisions Summary

| Decision | Choice | Reason |
|---|---|---|
| Primary key type | UUID (application-generated) | No volume leakage, no coordination needed, ID known before insert |
| Money storage | Integer (paise/cents) | Eliminates float rounding errors entirely |
| Status fields | Python Enum → PostgreSQL native enum | Invalid values rejected at DB level, not just application level |
| Migration tool | Alembic | Industry standard for SQLAlchemy projects; supports autogenerate and downgrade |
| Migration timing | Auto-run at service startup | No manual step required; safe for single-instance development setup |
| Seeder approach | Idempotent check-before-insert | Safe to run on every restart; no duplicate data, no conflict errors |
| Session ownership | Service layer | Service controls transaction boundary; repositories are stateless |
| Table name prefix | `commerce_` | Ownership visible at a glance when sharing a database with other services |
