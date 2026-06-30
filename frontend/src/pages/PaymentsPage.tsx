import { useEffect, useState } from 'react';
import {
  Box, Paper, Table, TableBody, TableCell, TableHead, TableRow, Chip, TablePagination,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { listPaymentSessions } from '../api/paymentApi';
import type { PaymentSession } from '../api/types';
import PageHeader from '../components/common/PageHeader';
import LoadingState from '../components/common/LoadingState';
import ErrorAlert from '../components/common/ErrorAlert';
import StatusChip from '../components/common/StatusChip';
import MoneyDisplay from '../components/common/MoneyDisplay';

const UI_STATE_COLOR: Record<string, 'default' | 'warning' | 'success' | 'error' | 'info'> = {
  PAYMENT_PAGE: 'info',
  RETRY: 'warning',
  SUCCESS: 'success',
  FAILED: 'error',
  EXPIRED: 'default',
};

export default function PaymentsPage() {
  const [sessions, setSessions] = useState<PaymentSession[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listPaymentSessions(page * rowsPerPage, rowsPerPage);
      const paginatedData = res.data.data as { items: PaymentSession[]; total: number; skip: number; limit: number };
      setSessions(paginatedData.items);
      setTotal(paginatedData.total);
    } catch {
      setError('Failed to load payment sessions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [page, rowsPerPage]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorAlert error={error} onRetry={load} />;

  return (
    <Box>
      <PageHeader title="Payment Sessions" subtitle={`${total} total`} />

      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Session ID</TableCell>
              <TableCell>Checkout ID</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>UI State</TableCell>
              <TableCell>Amount</TableCell>
              <TableCell>Attempts</TableCell>
              <TableCell>Expires</TableCell>
              <TableCell>Created</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sessions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ color: 'text.secondary', py: 3 }}>
                  No payment sessions
                </TableCell>
              </TableRow>
            ) : (
              sessions.map((s) => (
                <TableRow
                  key={s.session_id}
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/payments/session/${s.session_id}`)}
                >
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {s.session_id.slice(0, 12)}…
                  </TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'text.secondary' }}>
                    {s.checkout_id.slice(0, 12)}…
                  </TableCell>
                  <TableCell><StatusChip status={s.status} /></TableCell>
                  <TableCell>
                    <Chip
                      label={s.ui_state}
                      color={UI_STATE_COLOR[s.ui_state] ?? 'default'}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <MoneyDisplay amount={s.amount} currency={s.currency} />
                  </TableCell>
                  <TableCell sx={{ color: 'text.secondary' }}>
                    {s.attempt_count} / {s.max_attempts}
                  </TableCell>
                  <TableCell sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                    {new Date(s.expires_at).toLocaleString()}
                  </TableCell>
                  <TableCell sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                    {s.created_at ? new Date(s.created_at).toLocaleString() : '—'}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={total}
          page={page}
          rowsPerPage={rowsPerPage}
          onPageChange={(_, newPage) => setPage(newPage)}
          onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
          rowsPerPageOptions={[10, 20, 50, 100]}
        />
      </Paper>
    </Box>
  );
}
