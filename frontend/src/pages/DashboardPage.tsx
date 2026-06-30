import { useEffect, useState } from 'react';
import {
  Grid, Paper, Typography, Box,
  Table, TableBody, TableCell, TableHead, TableRow,
  Button,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import PeopleAltIcon from '@mui/icons-material/PeopleAlt';
import StoreIcon from '@mui/icons-material/Store';
import Inventory2Icon from '@mui/icons-material/Inventory2';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import ReceiptIcon from '@mui/icons-material/Receipt';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { getDashboardCounts, listCheckouts } from '../api/commerceApi';
import type { DashboardCounts, Checkout } from '../api/types';
import PageHeader from '../components/common/PageHeader';
import LoadingState from '../components/common/LoadingState';
import ErrorAlert from '../components/common/ErrorAlert';
import StatusChip from '../components/common/StatusChip';
import MoneyDisplay from '../components/common/MoneyDisplay';
import toast from 'react-hot-toast';

function StatCard({
  label, value, sub, icon, color,
}: {
  label: string;
  value: number;
  sub?: string;
  icon: React.ReactNode;
  color: string;
}) {
  return (
    <Paper
      sx={{
        p: 2.5,
        position: 'relative',
        overflow: 'hidden',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '3px',
          background: color,
        },
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box>
          <Typography
            variant="caption"
            sx={{
              color: 'text.secondary',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              fontSize: '0.68rem',
            }}
          >
            {label}
          </Typography>
          <Typography
            sx={{
              mt: 0.5,
              fontWeight: 700,
              fontSize: '2rem',
              lineHeight: 1,
              color: 'text.primary',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {value.toLocaleString()}
          </Typography>
          {sub && (
            <Typography variant="caption" sx={{ color, mt: 0.5, display: 'block' }}>
              {sub}
            </Typography>
          )}
        </Box>
        <Box
          sx={{
            p: 1,
            borderRadius: 1.5,
            backgroundColor: color + '22',
            color,
            display: 'flex',
          }}
        >
          {icon}
        </Box>
      </Box>
    </Paper>
  );
}

export default function DashboardPage() {
  const [counts, setCounts] = useState<DashboardCounts | null>(null);
  const [checkouts, setCheckouts] = useState<Checkout[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [countsRes, checkoutsRes] = await Promise.all([
        getDashboardCounts(),
        listCheckouts(0, 10),
      ]);
      setCounts(countsRes.data.data);
      setCheckouts(checkoutsRes.data.data.items);
    } catch {
      const msg = 'Failed to load dashboard data. Make sure both services are running.';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <LoadingState />;
  if (error) return <ErrorAlert error={error} onRetry={load} />;

  return (
    <Box>
      <PageHeader title="Dashboard" subtitle="System overview" />

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 6, sm: 4, md: 2.4 }}>
          <StatCard
            label="Users"
            value={counts?.total_users ?? 0}
            icon={<PeopleAltIcon fontSize="small" />}
            color="#6e8efb"
          />
        </Grid>
        <Grid size={{ xs: 6, sm: 4, md: 2.4 }}>
          <StatCard
            label="Sellers"
            value={counts?.total_sellers ?? 0}
            sub={`${counts?.total_active_sellers ?? 0} active`}
            icon={<StoreIcon fontSize="small" />}
            color="#4ecdc4"
          />
        </Grid>
        <Grid size={{ xs: 6, sm: 4, md: 2.4 }}>
          <StatCard
            label="Products"
            value={counts?.total_products ?? 0}
            sub={`${counts?.total_active_products ?? 0} active`}
            icon={<Inventory2Icon fontSize="small" />}
            color="#f7b731"
          />
        </Grid>
        <Grid size={{ xs: 6, sm: 4, md: 2.4 }}>
          <StatCard
            label="Checkouts"
            value={counts?.total_checkouts ?? 0}
            icon={<ShoppingCartIcon fontSize="small" />}
            color="#a29bfe"
          />
        </Grid>
        <Grid size={{ xs: 6, sm: 4, md: 2.4 }}>
          <StatCard
            label="Orders"
            value={counts?.total_orders ?? 0}
            icon={<ReceiptIcon fontSize="small" />}
            color="#00b894"
          />
        </Grid>
      </Grid>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Recent Checkouts
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            Recent Activity
          </Typography>
        </Box>
        <Button
          size="small"
          endIcon={<ArrowForwardIcon fontSize="small" />}
          onClick={() => navigate('/checkouts')}
        >
          View All
        </Button>
      </Box>

      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Checkout ID</TableCell>
              <TableCell>User ID</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Amount</TableCell>
              <TableCell>Payment Session</TableCell>
              <TableCell>Order ID</TableCell>
              <TableCell>Seller ID</TableCell>
              <TableCell>Product ID</TableCell>
              <TableCell>Qty</TableCell>
              <TableCell>Created</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {checkouts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={10} align="center" sx={{ color: 'text.secondary', py: 3 }}>
                  No checkouts yet
                </TableCell>
              </TableRow>
            ) : (
              checkouts.map((c) => (
                <TableRow
                  key={c.checkout_id}
                  sx={{ cursor: 'pointer', '&:hover': { backgroundColor: 'action.hover' } }}
                  onClick={() => navigate(`/checkouts/${c.checkout_id}`)}
                >
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {c.checkout_id.slice(0, 8)}…
                  </TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {c.user_id.slice(0, 8)}…
                  </TableCell>
                  <TableCell>
                    <StatusChip status={c.checkout_status} />
                  </TableCell>
                  <TableCell>
                    <MoneyDisplay amount={c.total_amount} currency="INR" />
                  </TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {c.payment_session_id ? `${c.payment_session_id.slice(0, 8)}…` : '—'}
                  </TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {(c as any).order_id ? `${(c as any).order_id.slice(0, 8)}…` : '—'}
                  </TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {(c as any).seller_id ? `${(c as any).seller_id.slice(0, 8)}…` : '—'}
                  </TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {(c as any).product_id ? `${(c as any).product_id.slice(0, 8)}…` : '—'}
                  </TableCell>
                  <TableCell sx={{ fontSize: '0.75rem' }}>
                    {(c as any).quantity ?? '—'}
                  </TableCell>
                  <TableCell sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                    {c.created_at ? new Date(c.created_at).toLocaleString() : '—'}
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
