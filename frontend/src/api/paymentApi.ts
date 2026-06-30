import axios from 'axios';
import type { ApiResponse, PaymentSession, PaginatedData } from './types';

const payment = axios.create({ baseURL: '/payment/api/v1' });

export const listPaymentSessions = (skip = 0, limit = 20) =>
  payment.get<ApiResponse<PaginatedData<PaymentSession>>>('payment-sessions/', { params: { skip, limit } });

export const getPaymentSession = (sessionId: string) =>
  payment.get<ApiResponse<PaymentSession>>(`/payment-sessions/${sessionId}`);

export const createPaymentAttempt = (
  sessionId: string,
  data: { idempotency_key: string; payment_method: string },
) => payment.post<ApiResponse<{ attempt_id: string; status: string; failure_reason?: string; session_status: string }>>(
  `/payment-sessions/${sessionId}/attempt`,
  data,
);
