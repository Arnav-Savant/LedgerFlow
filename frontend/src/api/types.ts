export interface ApiResponse<T> {
  success: boolean;
  status_code: number;
  message: string;
  data: T;
}

export interface User {
  user_id: string;
  name: string;
  email: string;
  phone?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Seller {
  seller_id: string;
  name: string;
  email: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Product {
  product_id: string;
  seller_id: string;
  name: string;
  price: number;
  currency: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Inventory {
  inventory_id: string;
  product_id: string;
  available_quantity: number;
  reserved_quantity: number;
  updated_at?: string;
}

export interface OrderSummary {
  order_id: string;
  product_id: string;
  seller_id: string;
  amount: number;
  currency: string;
  order_status: string;
}

export interface Checkout {
  checkout_id: string;
  user_id: string;
  checkout_status: string;
  total_amount: number;
  payment_session_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CheckoutDetail extends Checkout {
  orders: OrderSummary[];
}

export interface Order {
  order_id: string;
  checkout_id: string;
  user_id: string;
  product_id: string;
  product_name: string;
  seller_id: string;
  seller_name: string;
  quantity: number;
  amount: number;
  currency: string;
  order_status: string;
  created_at?: string;
}

export interface AttemptSummary {
  attempt_id: string;
  status: string;
  failure_reason?: string;
  created_at: string;
}

export interface PaymentSession {
  session_id: string;
  checkout_id: string;
  user_id: string;
  status: string;
  amount: number;
  currency: string;
  payment_method?: string;
  attempt_count: number;
  max_attempts: number;
  expires_at: string;
  ui_state: string;
  can_retry: boolean;
  redirect_url?: string;
  attempts?: AttemptSummary[];
  created_at?: string;
}

export interface DashboardCounts {
  total_users: number;
  total_sellers: number;
  total_active_sellers: number;
  total_products: number;
  total_active_products: number;
  total_checkouts: number;
  total_orders: number;
}

export interface CheckoutInitiateRequest {
  user_id: string;
  products: { product_id: string; quantity: number }[];
}

export interface CheckoutInitiateResponse {
  checkout_id: string;
  user_id: string;
  checkout_status: string;
  total_amount: number;
  payment_session_id: string;
  redirect_url: string;
  order_ids: string[];
  orders: OrderSummary[];
}
