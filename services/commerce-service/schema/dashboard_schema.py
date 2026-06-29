from pydantic import BaseModel


class DashboardCountsResponse(BaseModel):
    total_users: int
    total_sellers: int
    total_active_sellers: int
    total_products: int
    total_active_products: int
    total_checkouts: int
    total_orders: int
