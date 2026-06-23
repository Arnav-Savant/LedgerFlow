from utils.enums import Currency

# Fixed IDs are standard UUID strings (with hyphens).
# The seeder checks for existence before inserting, so these IDs are stable across restarts.

# ── Users ──────────────────────────────────────────────────────────────────────
USERS = [
    {
        "id": "10000000-0000-0000-0000-000000000001",
        "name": "Rahul Sharma",
        "email": "rahul.sharma@example.com",
        "phone": "+91-9876543210",
    },
    {
        "id": "10000000-0000-0000-0000-000000000002",
        "name": "Priya Patel",
        "email": "priya.patel@example.com",
        "phone": "+91-9876543211",
    },
    {
        "id": "10000000-0000-0000-0000-000000000003",
        "name": "Amit Kumar",
        "email": "amit.kumar@example.com",
        "phone": "+91-9876543212",
    },
]

# ── Sellers ────────────────────────────────────────────────────────────────────
SELLERS = [
    {
        "id": "20000000-0000-0000-0000-000000000001",
        "name": "TechMart India",
        "email": "techmart@example.com",
    },
    {
        "id": "20000000-0000-0000-0000-000000000002",
        "name": "FashionHub",
        "email": "fashionhub@example.com",
    },
]

TECHMART_ID = "20000000-0000-0000-0000-000000000001"
FASHIONHUB_ID = "20000000-0000-0000-0000-000000000002"

# ── Products ───────────────────────────────────────────────────────────────────
# Prices are stored in paise (INR smallest denomination).
# ₹2,999 → 299900 paise.
PRODUCTS = [
    {
        "id": "30000000-0000-0000-0000-000000000001",
        "seller_id": TECHMART_ID,
        "name": "Wireless Earbuds Pro",
        "price": 299900,
        "currency": Currency.INR,
    },
    {
        "id": "30000000-0000-0000-0000-000000000002",
        "seller_id": TECHMART_ID,
        "name": "Laptop Stand",
        "price": 149900,
        "currency": Currency.INR,
    },
    {
        "id": "30000000-0000-0000-0000-000000000003",
        "seller_id": TECHMART_ID,
        "name": "USB-C Hub 7-in-1",
        "price": 89900,
        "currency": Currency.INR,
    },
    {
        "id": "30000000-0000-0000-0000-000000000004",
        "seller_id": FASHIONHUB_ID,
        "name": "Cotton T-Shirt (Blue)",
        "price": 59900,
        "currency": Currency.INR,
    },
    {
        "id": "30000000-0000-0000-0000-000000000005",
        "seller_id": FASHIONHUB_ID,
        "name": "Slim Fit Denim Jeans",
        "price": 129900,
        "currency": Currency.INR,
    },
]

# ── Inventory ──────────────────────────────────────────────────────────────────
# One row per product. reserved_quantity starts at 0.
INVENTORY = [
    {
        "id": "40000000-0000-0000-0000-000000000001",
        "product_id": "30000000-0000-0000-0000-000000000001",
        "available_quantity": 100,
        "reserved_quantity": 0,
    },
    {
        "id": "40000000-0000-0000-0000-000000000002",
        "product_id": "30000000-0000-0000-0000-000000000002",
        "available_quantity": 100,
        "reserved_quantity": 0,
    },
    {
        "id": "40000000-0000-0000-0000-000000000003",
        "product_id": "30000000-0000-0000-0000-000000000003",
        "available_quantity": 150,
        "reserved_quantity": 0,
    },
    {
        "id": "40000000-0000-0000-0000-000000000004",
        "product_id": "30000000-0000-0000-0000-000000000004",
        "available_quantity": 200,
        "reserved_quantity": 0,
    },
    {
        "id": "40000000-0000-0000-0000-000000000005",
        "product_id": "30000000-0000-0000-0000-000000000005",
        "available_quantity": 75,
        "reserved_quantity": 0,
    },
]
