import { useEffect, useState } from 'react';
import {
  Grid, Paper, Typography, Box,
  Table, TableBody, TableCell, TableHead, TableRow,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { getDashboardCounts, listCheckouts } from '../api/commerceApi';
import type { DashboardCounts, Checkout } from '../api/types';
import PageHeader from '../components/common/PageHeader';
import LoadingState from '../components/common/LoadingState';
import ErrorAlert from '../components/common/ErrorAlert';
import StatusChip from '../components/common/StatusChip';
import MoneyDisplay from '../components/common/MoneyDisplay';

function StatCard({ label, value, sub }: { label: string; value: number; sub?: string }) {
  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="caption" sx={{ color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </Typography>
      <Typography sx={{ my: 0.5, color: 'text.primary', fontWeight: 700, fontSize: '1.8rem' }}>
        {value}
      </Typography>
      {sub && (
        <Typography variant="caption" color="text.secondary">
          {sub}
        </Typography>
      )}
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
        listCheckouts(),
      ]);
      setCounts(countsRes.data.data);
      const allCheckouts = checkoutsRes.data.data as Checkout[];
      setCheckouts(allCheckouts.slice(0, 10));
    } catch {
      setError('Failed to load dashboard data. Make sure both services are running.');
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
        <Grid size={{ xs: 6, sm: 4, md: 3 }}>
          <StatCard label="Users" value={counts?.total_users ?? 0} />
        </Grid>
        <Grid size={{ xs: 6, sm: 4, md: 3 }}>
          <StatCard
            label="Sellers"
            value={counts?.total_sellers ?? 0}
            sub={`${counts?.total_active_sellers ?? 0} active`}
          />
        </Grid>
        <Grid size={{ xs: 6, sm: 4, md: 3 }}>
          <StatCard
            label="Products"
            value={counts?.total_products ?? 0}
            sub={`${counts?.total_active_products ?? 0} active`}
          />
        </Grid>
        <Grid size={{ xs: 6, sm: 4, md: 3 }}>
          <StatCard label="Checkouts" value={counts?.total_checkouts ?? 0} />
        </Grid>
        <Grid size={{ xs: 6, sm: 4, md: 3 }}>
          <StatCard label="Orders" value={counts?.total_orders ?? 0} />
        </Grid>
      </Grid>

      <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
        Recent Checkouts
      </Typography>
      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Checkout ID</TableCell>
              <TableCell>User</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Amount</TableCell>
              <TableCell>Session</TableCell>
              <TableCell>Created</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {checkouts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ color: 'text.secondary', py: 3 }}>
                  No checkouts yet
                </TableCell>
              </TableRow>
            ) : (
              checkouts.map((c) => (
                <TableRow
                  key={c.checkout_id}
                  sx={{ cursor: 'pointer' }}
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
