import { Chip } from '@mui/material';

type ChipColor = 'success' | 'error' | 'warning' | 'default' | 'info' | 'primary';

const STATUS_COLORS: Record<string, ChipColor> = {
  // Checkout statuses
  PENDING: 'default',
  PAYMENT_INITIATED: 'warning',
  PAYMENT_COMPLETED: 'success',
  PAYMENT_FAILED: 'error',
  EXPIRED: 'error',
  CANCELLED: 'error',
  // Order statuses
  CREATED: 'default',
  PAYMENT_PENDING: 'warning',
  CONFIRMED: 'success',
  REFUND_INITIATED: 'warning',
  REFUNDED: 'info',
  // Payment session statuses
  INITIATED: 'info',
  SUCCESS: 'success',
  FAILED: 'error',
  // Active flags
  active: 'success',
  inactive: 'error',
};

export default function StatusChip({ status }: { status: string }) {
  const color = STATUS_COLORS[status] ?? 'default';
  return <Chip label={status} color={color} size="small" variant="outlined" />;
}
