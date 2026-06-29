import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Paper, Typography, Grid, Table, TableBody, TableCell,
  TableHead, TableRow, Button,
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { getCheckout } from '../api/commerceApi';
import type { CheckoutDetail } from '../api/types';
import type { TimelineEvent } from '../components/common/Timeline';
import PageHeader from '../components/common/PageHeader';
import LoadingState from '../components/common/LoadingState';
import ErrorAlert from '../components/common/ErrorAlert';
import StatusChip from '../components/common/StatusChip';
import MoneyDisplay from '../components/common/MoneyDisplay';
import Timeline from '../components/common/Timeline';

function buildTimeline(checkout: CheckoutDetail): TimelineEvent[] {
  const events: TimelineEvent[] = [];

  events.push({
    id: 'checkout-created',
    label: 'Checkout Created',
    timestamp: checkout.created_at,
    status: 'completed',
    detail: `ID: ${checkout.checkout_id}`,
  });

  if (checkout.checkout_status !== 'PENDING') {
    events.push({
      id: 'inventory-reserved',
      label: 'Inventory Reserved',
      status: 'completed',
      detail: `${checkout.orders.length} product(s) reserved`,
    });

    events.push({
      id: 'orders-created',
      label: 'Orders Created',
      status: 'completed',
      detail: `${checkout.orders.length} order(s) created`,
    });
  }

  if (checkout.payment_session_id) {
    events.push({
      id: 'payment-session',
      label: 'Payment Session Created',
      status: 'completed',
      detail: `Session: ${checkout.payment_session_id}`,
    });
  }

  if (checkout.checkout_status === 'PAYMENT_COMPLETED') {
    events.push({
      id: 'payment-success',
      label: 'Payment Completed',
      status: 'completed',
    });
  } else if (checkout.checkout_status === 'PAYMENT_FAILED') {
    events.push({
      id: 'payment-failed',
      label: 'Payment Failed',
      status: 'failed',
    });
  } else if (checkout.checkout_status === 'PAYMENT_INITIATED') {
    events.push({
      id: 'awaiting-payment',
      label: 'Awaiting Payment',
      status: 'pending',
    });
  }

  return events;
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Box sx={{ display: 'flex', gap: 2, py: 0.75, borderBottom: '1px solid #30363d' }}>
      <Typography variant="caption" sx={{ color: 'text.secondary', width: 160, flexShrink: 0 }}>
        {label}
      </Typography>
      <Typography variant="caption" sx={{ color: 'text.primary', fontFamily: 'monospace' }}>
        {value}
      </Typography>
    </Box>
  );
}

export default function CheckoutDetailPage() {
  const { checkoutId } = useParams<{ checkoutId: string }>();
  const [checkout, setCheckout] = useState<CheckoutDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = async () => {
    if (!checkoutId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getCheckout(checkoutId);
      setCheckout(res.data.data as CheckoutDetail);
    } catch {
      setError('Failed to load checkout');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [checkoutId]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorAlert error={error} onRetry={load} />;
  if (!checkout) return null;

  const timeline = buildTimeline(checkout);

  return (
    <Box>
      <PageHeader
        title={`Checkout ${checkout.checkout_id.slice(0, 12)}…`}
        subtitle="Checkout detail"
      />

      <Button
        startIcon={<ArrowBackIcon />}
        size="small"
        onClick={() => navigate('/checkouts')}
        sx={{ mb: 2 }}
      >
        Back to Checkouts
      </Button>

      <Grid container spacing={2}>
        {/* Left column: info + orders */}
        <Grid size={{ xs: 12, md: 8 }}>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1.5, color: 'text.secondary' }}>
              Checkout Info
            </Typography>
            <InfoRow label="Checkout ID" value={checkout.checkout_id} />
            <InfoRow label="User ID" value={checkout.user_id} />
            <InfoRow
              label="Status"
              value={<StatusChip status={checkout.checkout_status} />}
            />
            <InfoRow
              label="Total Amount"
              value={<MoneyDisplay amount={checkout.total_amount} currency="INR" />}
            />
            <InfoRow label="Payment Session ID" value={checkout.payment_session_id ?? '—'} />
            <InfoRow
              label="Created"
              value={checkout.created_at ? new Date(checkout.created_at).toLocaleString() : '—'}
            />

            {checkout.payment_session_id && (
              <Button
                variant="outlined"
                size="small"
                startIcon={<OpenInNewIcon />}
                sx={{ mt: 2 }}
                onClick={() => navigate(`/payments/session/${checkout.payment_session_id}`)}
              >
                View Payment Session
              </Button>
            )}
          </Paper>

          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1.5, color: 'text.secondary' }}>
              Orders ({checkout.orders.length})
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Order ID</TableCell>
                  <TableCell>Product</TableCell>
                  <TableCell>Seller</TableCell>
                  <TableCell>Amount</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {checkout.orders.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center" sx={{ color: 'text.secondary' }}>
                      No orders
                    </TableCell>
                  </TableRow>
                ) : (
                  checkout.orders.map((o) => (
                    <TableRow key={o.order_id}>
                      <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                        {o.order_id.slice(0, 12)}…
                      </TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'text.secondary' }}>
                        {o.product_id.slice(0, 8)}…
                      </TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'text.secondary' }}>
                        {o.seller_id.slice(0, 8)}…
                      </TableCell>
                      <TableCell>
                        <MoneyDisplay amount={o.amount} currency={o.currency} />
                      </TableCell>
                      <TableCell><StatusChip status={o.order_status} /></TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Paper>
        </Grid>

        {/* Right column: timeline */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
              Timeline
            </Typography>
            <Timeline events={timeline} />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
