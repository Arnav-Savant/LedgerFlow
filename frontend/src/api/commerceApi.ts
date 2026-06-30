import axios from 'axios';
import type {
  ApiResponse, User, Seller, Product, Inventory,
  Checkout, CheckoutDetail, Order, OrderDetail, DashboardCounts,
  CheckoutInitiateRequest, CheckoutInitiateResponse, PaginatedData,
} from './types';

const commerce = axios.create({ baseURL: '/commerce/api/v1' });

// Users
export const listUsers = (skip = 0, limit = 20) => commerce.get<ApiResponse<PaginatedData<User>>>('users/', { params: { skip, limit } });
export const getUser = (id: string) => commerce.get<ApiResponse<User>>(`/users/${id}`);
export const createUser = (data: { name: string; email: string; phone?: string }) =>
  commerce.post<ApiResponse<User>>('/users/', data);
export const updateUser = (id: string, data: Partial<{ name: string; email: string; phone: string }>) =>
  commerce.put<ApiResponse<User>>(`/users/${id}`, data);
export const deleteUser = (id: string) => commerce.delete<ApiResponse<null>>(`/users/${id}`);

// Sellers
export const listSellers = (skip = 0, limit = 20) => commerce.get<ApiResponse<PaginatedData<Seller>>>('sellers/', { params: { skip, limit } });
export const getSeller = (id: string) => commerce.get<ApiResponse<Seller>>(`/sellers/${id}`);
export const createSeller = (data: { name: string; email: string }) =>
  commerce.post<ApiResponse<Seller>>('/sellers/', data);
export const updateSeller = (id: string, data: Partial<{ name: string; email: string }>) =>
  commerce.put<ApiResponse<Seller>>(`/sellers/${id}`, data);
export const disableSeller = (id: string) => commerce.delete<ApiResponse<Seller>>(`/sellers/${id}`);
export const reactivateSeller = (id: string) => commerce.patch<ApiResponse<Seller>>(`/sellers/${id}/reactivate`);

// Products
export const listProducts = (skip = 0, limit = 20) => commerce.get<ApiResponse<PaginatedData<Product>>>('products/', { params: { skip, limit } });
export const getProduct = (id: string) => commerce.get<ApiResponse<Product>>(`/products/${id}`);
export const createProduct = (data: { seller_id: string; name: string; price: number; currency: string }) =>
  commerce.post<ApiResponse<Product>>('/products/', data);
export const updateProduct = (id: string, data: Partial<{ name: string; price: number }>) =>
  commerce.put<ApiResponse<Product>>(`/products/${id}`, data);
export const deactivateProduct = (id: string) => commerce.delete<ApiResponse<Product>>(`/products/${id}`);
export const reactivateProduct = (id: string) => commerce.patch<ApiResponse<Product>>(`/products/${id}/reactivate`);

// Inventory
export const listInventory = (skip = 0, limit = 20) => commerce.get<ApiResponse<PaginatedData<Inventory>>>('inventory/', { params: { skip, limit } });
export const getInventoryByProduct = (productId: string) =>
  commerce.get<ApiResponse<Inventory>>(`/inventory/product/${productId}`);
export const updateStock = (productId: string, operation: string, quantity: number) =>
  commerce.post<ApiResponse<Inventory>>(`/inventory/product/${productId}/stock`, { operation, quantity });

// Checkouts
export const listCheckouts = (skip = 0, limit = 20) => commerce.get<ApiResponse<PaginatedData<Checkout>>>('checkouts/', { params: { skip, limit } });
export const getCheckout = (id: string) => commerce.get<ApiResponse<CheckoutDetail>>(`/checkouts/${id}`);
export const initiateCheckout = (data: CheckoutInitiateRequest) =>
  commerce.post<ApiResponse<CheckoutInitiateResponse>>('/checkouts/initiate', data);

// Orders
export const listOrders = (skip = 0, limit = 20) => commerce.get<ApiResponse<PaginatedData<Order>>>('orders/', { params: { skip, limit } });
export const getOrder = (id: string) => commerce.get<ApiResponse<OrderDetail>>(`/orders/${id}`);

// Dashboard
export const getDashboardCounts = () => commerce.get<ApiResponse<DashboardCounts>>('/dashboard/counts');
