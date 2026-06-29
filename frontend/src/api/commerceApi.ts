import axios from 'axios';
import type {
  ApiResponse, User, Seller, Product, Inventory,
  Checkout, CheckoutDetail, Order, DashboardCounts,
  CheckoutInitiateRequest, CheckoutInitiateResponse,
} from './types';

const commerce = axios.create({ baseURL: '/commerce/api/v1' });

// Users
export const listUsers = () => commerce.get<ApiResponse<User[]>>('/users/');
export const getUser = (id: string) => commerce.get<ApiResponse<User>>(`/users/${id}`);
export const createUser = (data: { name: string; email: string; phone?: string }) =>
  commerce.post<ApiResponse<User>>('/users/', data);
export const updateUser = (id: string, data: Partial<{ name: string; email: string; phone: string }>) =>
  commerce.put<ApiResponse<User>>(`/users/${id}`, data);
export const deleteUser = (id: string) => commerce.delete<ApiResponse<null>>(`/users/${id}`);

// Sellers
export const listSellers = () => commerce.get<ApiResponse<Seller[]>>('/sellers/');
export const getSeller = (id: string) => commerce.get<ApiResponse<Seller>>(`/sellers/${id}`);
export const createSeller = (data: { name: string; email: string }) =>
  commerce.post<ApiResponse<Seller>>('/sellers/', data);
export const updateSeller = (id: string, data: Partial<{ name: string; email: string }>) =>
  commerce.put<ApiResponse<Seller>>(`/sellers/${id}`, data);
export const disableSeller = (id: string) => commerce.delete<ApiResponse<Seller>>(`/sellers/${id}`);

// Products
export const listProducts = () => commerce.get<ApiResponse<Product[]>>('/products/');
export const getProduct = (id: string) => commerce.get<ApiResponse<Product>>(`/products/${id}`);
export const createProduct = (data: { seller_id: string; name: string; price: number; currency: string }) =>
  commerce.post<ApiResponse<Product>>('/products/', data);
export const updateProduct = (id: string, data: Partial<{ name: string; price: number }>) =>
  commerce.put<ApiResponse<Product>>(`/products/${id}`, data);
export const deactivateProduct = (id: string) => commerce.delete<ApiResponse<Product>>(`/products/${id}`);

// Inventory
export const listInventory = () => commerce.get<ApiResponse<Inventory[]>>('/inventory/');
export const getInventoryByProduct = (productId: string) =>
  commerce.get<ApiResponse<Inventory>>(`/inventory/product/${productId}`);
export const adjustInventory = (productId: string, delta: number) =>
  commerce.post<ApiResponse<Inventory>>(`/inventory/product/${productId}/adjust`, { delta });

// Checkouts
export const listCheckouts = () => commerce.get<ApiResponse<Checkout[]>>('/checkouts/');
export const getCheckout = (id: string) => commerce.get<ApiResponse<CheckoutDetail>>(`/checkouts/${id}`);
export const initiateCheckout = (data: CheckoutInitiateRequest) =>
  commerce.post<ApiResponse<CheckoutInitiateResponse>>('/checkouts/initiate', data);

// Orders
export const listOrders = () => commerce.get<ApiResponse<Order[]>>('/orders/');
export const getOrder = (id: string) => commerce.get<ApiResponse<Order>>(`/orders/${id}`);

// Dashboard
export const getDashboardCounts = () => commerce.get<ApiResponse<DashboardCounts>>('/dashboard/counts');
