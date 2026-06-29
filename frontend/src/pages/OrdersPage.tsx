import { useEffect, useState } from 'react';
import { Box, Paper, Table, TableBody, TableCell, TableHead, TableRow } from '@mui/material';
import { listOrders } from '../api/commerceApi';
import type { Order } from '../api/types';
import PageHeader from '../components/common/PageHeader';
import LoadingState from '../components/common/LoadingState';
import ErrorAlert from '../components/common/ErrorAlert';
import StatusChip from '../components/common/StatusChip';
import MoneyDisplay from '../components/common/MoneyDisplay';

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listOrders();
      setOrders(res.data.data as Order[]);
    } catch {
      setError('Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <LoadingState />;
  if (error) return <ErrorAlert error={error} onRetry={load} />;

  return (
    <Box>
      <PageHeader title="Orders" subtitle={`${orders.length} total`} />

      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Order ID</TableCell>
              <TableCell>Product</TableCell>
              <TableCell>Seller</TableCell>
              <TableCell>Qty</TableCell>
              <TableCell>Amount</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {orders.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ color: 'text.secondary', py: 3 }}>
                  No orders
                </TableCell>
              </TableRow>
            ) : (
              orders.map((o) => (
                <TableRow key={o.order_id}>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {o.order_id.slice(0, 12)}…
                  </TableCell>
                  <TableCell>{o.product_name}</TableCell>
                  <TableCell sx={{ color: 'text.secondary' }}>{o.seller_name}</TableCell>
                  <TableCell>{o.quantity}</TableCell>
                  <TableCell>
                    <MoneyDisplay amount={o.amount} currency={o.currency} />
                  </TableCell>
                  <TableCell><StatusChip status={o.order_status} /></TableCell>
                  <TableCell sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                    {o.created_at ? new Date(o.created_at).toLocaleString() : '—'}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}
