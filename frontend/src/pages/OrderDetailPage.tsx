import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Box, Paper, Typography, Grid, Button } from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { getOrder } from '../api/commerceApi';
import type { OrderDetail } from '../api/types';
import PageHeader from '../components/common/PageHeader';
import LoadingState from '../components/common/LoadingState';
import ErrorAlert from '../components/common/ErrorAlert';
import StatusChip from '../components/common/StatusChip';
import MoneyDisplay from '../components/common/MoneyDisplay';

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Box sx={{ display: 'flex', gap: 2, py: 0.75, borderBottom: '1px solid #21262d' }}>
      <Typography variant="caption" sx={{ color: 'text.secondary', width: 160, flexShrink: 0 }}>
        {label}
      </Typography>
      <Typography variant="caption" sx={{ color: 'text.primary' }}>
        {value}
      </Typography>
    </Box>
  );
}

export default function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = async () => {
    if (!orderId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getOrder(orderId);
      setOrder(res.data.data as OrderDetail);
    } catch {
      setError('Failed to load order');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [orderId]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorAlert error={error} onRetry={load} />;
  if (!order) return null;

  return (
    <Box>
      <PageHeader
        title={`Order ${orderId!.slice(0, 12)}…`}
        subtitle="Order detail"
      />

      <Button
        startIcon={<ArrowBackIcon />}
        size="small"
        onClick={() => navigate('/orders')}
        sx={{ mb: 2 }}
      >
        Back to Orders
      </Button>

      <Grid container spacing={2}>
        {/* Left column: order info */}
        <Grid size={{ xs: 12, md: 8 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1.5, color: 'text.secondary' }}>
              Order Info
            </Typography>

            <InfoRow
              label="Order ID"
              value={
                <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                  {order.order_id}
                </Typography>
              }
            />
            <InfoRow
              label="Checkout ID"
              value={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                    {order.checkout_id}
                  </Typography>
                  <Button
                    size="small"
                    variant="outlined"
                    sx={{ py: 0, px: 1, minWidth: 0, fontSize: '0.7rem', lineHeight: 1.6 }}
                    onClick={() => navigate(`/checkouts/${order.checkout_id}`)}
                  >
                    View Checkout
                  </Button>
                </Box>
              }
            />
            <InfoRow
              label="User ID"
              value={
                <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                  {order.user_id}
                </Typography>
              }
            />
            <InfoRow
              label="Order Status"
              value={<StatusChip status={order.order_status} />}
            />
            <InfoRow
              label="Checkout Status"
              value={<StatusChip status={order.checkout_status} />}
            />
            <InfoRow
              label="Amount"
              value={<MoneyDisplay amount={order.amount} currency={order.currency} />}
            />
            <InfoRow
              label="Quantity"
              value={order.quantity}
            />
            <InfoRow
              label="Ledger Updated"
              value={
                <Typography
                  variant="caption"
                  sx={{ color: order.ledger_updated ? 'success.main' : 'text.secondary' }}
                >
                  {order.ledger_updated ? 'Yes' : 'No'}
                </Typography>
              }
            />
            <InfoRow
              label="Wallet Updated"
              value={
                <Typography
                  variant="caption"
                  sx={{ color: order.wallet_updated ? 'success.main' : 'text.secondary' }}
                >
                  {order.wallet_updated ? 'Yes' : 'No'}
                </Typography>
              }
            />
          </Paper>
        </Grid>

        {/* Right column: product + seller */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1.5, color: 'text.secondary' }}>
              Product
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
              {order.product.name}
            </Typography>
            <Typography
              variant="caption"
              sx={{ fontFamily: 'monospace', color: 'text.secondary', display: 'block', mb: 1 }}
            >
              {order.product.product_id}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Typography variant="caption" sx={{ color: 'text.secondary' }}>Price:</Typography>
              <MoneyDisplay amount={order.product.price} currency={order.product.currency} />
            </Box>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 0.5 }}>
              Currency: {order.product.currency}
            </Typography>
          </Paper>

          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1.5, color: 'text.secondary' }}>
              Seller
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
              {order.seller_name}
            </Typography>
            <Typography
              variant="caption"
              sx={{ fontFamily: 'monospace', color: 'text.secondary', display: 'block' }}
            >
              {order.seller_id}
            </Typography>
          </Paper>

          <Paper sx={{ p: 1.5, bgcolor: 'action.hover' }}>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              Payment is managed through the checkout. View the checkout to access the payment session.
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
