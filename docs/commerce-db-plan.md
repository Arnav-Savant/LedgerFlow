# Commerce Service — Database Implementation Plan

> **Status:** Implemented (v1 service layer, APIs, middleware, and schemas complete)
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
│   ├── checkout.py               # Checkout table (lean: id, user_id, total_amount, status)
│   └── order.py                  # Order table (product/seller references live here)
│
├── utils/
│   └── enums.py                  # CheckoutStatus, OrderStatus, Currency enums
│
├── migrations/                   # Alembic home
│   ├── env.py                    # Alembic runtime config — connects to DB, imports models
│   ├── script.py.mako            # Template for generated migration files
│   └── versions/                 # One file per migration, named by revision ID
│       ├── 0001_initial_schema.py
│       ├── 5fd91ec51db1_remove_product_id_from_checkouts.py
│       ├── 57fcfdb642c2_remove_seller_id_from_checkouts.py
│       └── 59d17e6243b9_remove_discounted_pricing_from_checkouts.py
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
├── service/
│   ├── __init__.py
│   ├── user_service.py
│   ├── product_service.py
│   ├── inventory_service.py
│   ├── checkout_service.py       # Full checkout orchestration (saga pattern)
│   └── order_service.py
│
├── schema/
│   ├── __init__.py
│   ├── checkout_schema.py        # Request/response models for checkout APIs
│   └── order_schema.py           # Response models for order API
│
├── routes/
│   ├── __init__.py
│   ├── checkout_routes.py        # POST /checkouts/initiate, GET /checkouts/{id}
│   └── order_routes.py           # GET /orders/{id}
│
├── middleware/
│   ├── __init__.py
│   └── user_validation.py        # UserValidationMiddleware
│
├── alembic.ini                   # Alembic configuration file
└── main.py                       # Runs migrations + seeders, wires routers and middleware
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
| `currency` | ENUM | `Currency` — see section 5 |
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

`available_quantity + reserved_quantity = total physical stock`. When a checkout is created, stock moves from `available` to `reserved`. On payment success it is committed (reserved decrements permanently). On payment failure it is released back to available.

---

### 3.5 Checkouts

Represents a customer's checkout session, which groups one or more orders. Product and seller information is not stored directly on the checkout — it lives on each order.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → users.id |
| `total_amount` | INTEGER | Sum of all order amounts in smallest denomination |
| `status` | ENUM | `CheckoutStatus` — see section 5 |
| `created_at` | TIMESTAMPTZ | Set by mixin |
| `updated_at` | TIMESTAMPTZ | Set by mixin |

> **Schema evolution note:** The initial schema included `product_id`, `seller_id`, `coupon_id`, and `final_amount` on checkouts. These were removed via successive Alembic migrations (see section 7) to reflect the correct design where a checkout aggregates multiple orders and product references belong on orders.

---

### 3.6 Orders

One order is created per product in a checkout. Created from a checkout during the initiation flow.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `checkout_id` | UUID | FK → checkouts.id |
| `user_id` | UUID | FK → users.id |
| `product_id` | UUID | FK → products.id |
| `seller_id` | UUID | FK → sellers.id |
| `amount` | INTEGER | `product.price × quantity` in smallest denomination |
| `currency` | ENUM | `Currency` — derived from product |
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

- They reveal business volume.
- They create ordering coupling.
- They complicate horizontal scaling. UUIDs are statistically unique without coordination.

**Implementation:** Every model sets `id` as a `VARCHAR(36)` column with a default generated in Python (`str(uuid.uuid4())`), not in the database. Generating it in the application means the ID is known before the `INSERT` completes, which simplifies repository code and logging.

```
Column definition pattern:
id: Mapped[str] = mapped_column(
    String(36),
    primary_key=True,
    default=lambda: str(uuid.uuid4()),
)
```

---

## 5. Enums

All status fields use Python `Enum` subclasses stored as native PostgreSQL enum types.

**Location:** `utils/enums.py`

### CheckoutStatus

| Value | Meaning |
|---|---|
| `PENDING` | Checkout created, payment not yet initiated |
| `PAYMENT_INITIATED` | Payment session created |
| `PAYMENT_FAILED` | Payment attempt failed |
| `PAYMENT_COMPLETED` | Payment captured, order created |
| `EXPIRED` | Checkout timed out before payment |
| `CANCELLED` | Explicitly cancelled by the user |

### OrderStatus

| Value | Meaning |
|---|---|
| `CREATED` | Order record exists, inventory reserved |
| `PAYMENT_PENDING` | Payment initiation has been handed off |
| `CONFIRMED` | Ledger and wallet updated, order fully committed |
| `CANCELLED` | Order cancelled before fulfilment |
| `REFUND_INITIATED` | Refund requested |
| `REFUNDED` | Refund completed |

### Currency

| Value | Notes |
|---|---|
| `INR` | Indian Rupee |
| `USD` | US Dollar |
| `GBP` | British Pound |
| `EUR` | Euro |
| `JPY` | Japanese Yen |

---

## 6. SQLAlchemy Base and Shared Mixins

**Location:** `models/base.py`

All models inherit from a single `DeclarativeBase`. A `TimestampMixin` is defined once and mixed into every model. It adds `created_at` and `updated_at` columns using `server_default=func.now()` and `onupdate=func.now()` respectively.

```
Inheritance pattern:
class Checkout(TimestampMixin, Base):
    __tablename__ = "checkouts"
    ...
```

All table names are prefixed with `commerce_` in the initial design. Actual table names are `users`, `sellers`, `products`, `inventory`, `checkouts`, `orders` as defined in the models.

---

## 7. Alembic — Migration Tracking

### What Alembic does

Alembic tracks the history of your schema as a versioned chain of migration files. The `alembic_version` table in PostgreSQL records which revision was last applied.

### Current migration chain

1. `0001_initial_schema.py` — creates all tables and the three PostgreSQL enum types (`checkout_status`, `order_status`, `currency`).
2. `5fd91ec51db1_remove_product_id_from_checkouts.py` — removes `product_id` FK from checkouts.
3. `57fcfdb642c2_remove_seller_id_from_checkouts.py` — removes `seller_id` from checkouts.
4. `59d17e6243b9_remove_discounted_pricing_from_checkouts.py` — removes `coupon_id` and `final_amount` from checkouts.

### `alembic.ini`

`sqlalchemy.url` is left blank and overridden at runtime by `env.py`.

### `migrations/env.py`

Imports `PostgresConfig` for the database URL and imports `models` as a side effect to populate `Base.metadata`.

### Generating a migration

When a model is added or changed:
```
alembic revision --autogenerate -m "describe what changed"
```

Always review the generated file before committing.

### Applying migrations

```
alembic upgrade head        # Apply all unapplied migrations
alembic downgrade -1        # Roll back one migration
alembic current             # Show current revision
alembic history             # Show full migration chain
```

---

## 8. Auto-Apply Migrations on Startup

`main.py` runs migrations programmatically as part of the lifespan startup hook:

```python
from alembic.config import Config
from alembic import command

def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
```

If the database is already at the latest revision, this is a no-op.

---

## 9. Seeder Strategy

### Location

```
seeders/
├── seed_data.py     # Static definitions: lists of dicts describing each row
└── runner.py        # Reads seed_data.py and inserts rows idempotently
```

### Idempotency

Before inserting any seed row, the runner queries by a natural identifier. If the row exists, it is skipped. If it does not exist, it is inserted.

### Seed data

- **Users:** Three realistic user records.
- **Sellers:** Two seller records.
- **Products:** Five products spread across sellers, with prices in paise.
- **Inventory:** One inventory row per product. `available_quantity` starts at a realistic value; `reserved_quantity` starts at `0`.

### Execution order

1. Users (no foreign keys)
2. Sellers (no foreign keys)
3. Products (depends on sellers)
4. Inventory (depends on products)

---

## 10. Repository Layer

### Purpose

The repository layer is the only place in the service that issues database queries. Service classes call repository methods; they never construct queries themselves.

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

### Standard CRUD operations per repository

Every repository implements at minimum:

| Method | Description |
|---|---|
| `create(session, ...)` | Insert a new row, return the created model instance |
| `get_by_id(session, id)` | Fetch one row by UUID primary key; raises `NotFoundException` if not found |
| `get_all(session)` | Fetch all rows with optional limit/offset |
| `update_status(session, id, status)` | Update status field |
| `delete(session, id)` | Delete a row by primary key |

### Domain-specific operations

- `CheckoutRepo.update(checkout_id, total_amount, status)` — partial update for amount and/or status.
- `CheckoutRepo.get_with_user(checkout_id)` — raw SQL join returning checkout + user fields.
- `OrderRepo.get_all_by_checkout_id(checkout_id)` — returns all orders for a checkout (list, not first).
- `InventoryRepo.reserve / release / commit_reservation` — inventory lifecycle operations.

### Session handling

Repositories accept a `session` argument rather than creating one themselves. The transaction boundary is controlled at the service layer. Multiple repository calls within the same service method each commit independently (see compensating transactions in section 10 of the guide).

---

## 11. Startup Sequence End to End

When `python main.py` is executed:

```
1. ServerConfig and PostgresConfig are loaded from .env

2. AppLogger is initialized

3. FastAPI app is created

4. UserValidationMiddleware is registered

5. Routers are included under /api/v1 prefix

6. Lifespan context begins:

   a. run_migrations()
      └─ Alembic applies any unapplied migrations

   b. run_seeders()
      └─ Idempotent seed for Users → Sellers → Products → Inventory

7. Uvicorn begins serving requests on APP_HOST:APP_PORT

8. Available endpoints:
   GET  /health
   POST /api/v1/checkouts/initiate
   GET  /api/v1/checkouts/{checkout_id}
   GET  /api/v1/orders/{order_id}
```

---

## 12. Operational Commands Reference

### First-time setup

```bash
pip install -r requirements.txt
docker compose up -d postgres
python main.py
```

### Schema changes

```bash
# 1. Edit or add a model in models/
# 2. Generate the migration
alembic revision --autogenerate -m "describe the change"
# 3. Review the generated file in migrations/versions/
# 4. Apply it (or restart the service)
alembic upgrade head
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
docker compose down -v
docker compose up -d postgres
python main.py
```

---

## Key Decisions Summary

| Decision | Choice | Reason |
|---|---|---|
| Primary key type | UUID string in VARCHAR(36) | No volume leakage; ID known before insert; avoids psycopg2/SQLAlchemy impedance mismatch |
| Money storage | Integer (paise/cents) | Eliminates float rounding errors entirely |
| Status fields | Python Enum → PostgreSQL native enum | Invalid values rejected at DB level |
| Migration tool | Alembic | Industry standard for SQLAlchemy projects; supports autogenerate and downgrade |
| Migration timing | Auto-run at service startup | No manual step required; safe for single-instance development setup |
| Seeder approach | Idempotent check-before-insert | Safe to run on every restart; no duplicate data |
| Session ownership | Per repository method call | Each repo method commits; service layer compensates on failure |
| Checkout schema | Lean (user_id, total_amount, status only) | Product/seller data belongs on orders; supports multi-product checkouts |
| Multi-product checkout | One order per product | Order model references one product; multi-product support via multiple orders under one checkout |
| Cross-domain data access | Via owning service, not direct repo access | Enforces domain boundaries; keeps service layer as the coordination point |
| Transactional integrity | Compensating transactions (saga pattern) | Avoids long-held locks across multiple inventory operations while preserving consistency |
