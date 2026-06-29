import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Typography, Paper, Button, FormControl, InputLabel, Select,
  MenuItem, CircularProgress, Alert, Chip, Divider,
  Table, TableHead, TableRow, TableCell, TableBody,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { getPaymentSession, createPaymentAttempt } from '../api/paymentApi';
import type { PaymentSession } from '../api/types';
import MoneyDisplay from '../components/common/MoneyDisplay';
import StatusChip from '../components/common/StatusChip';
import LoadingState from '../components/common/LoadingState';

const PAYMENT_METHODS = ['CARD', 'UPI', 'NET_BANKING', 'WALLET'];

function generateIdempotencyKey(): string {
  return crypto.randomUUID();
}

// ── Sub-screens ────────────────────────────────────────────────────────────────

function SuccessScreen({ session }: { session: PaymentSession }) {
  const navigate = useNavigate();
  return (
    <Box sx={{ textAlign: 'center', py: 6 }}>
      <CheckCircleIcon sx={{ fontSize: 56, color: '#3fb950', mb: 2 }} />
      <Typography variant="h6" sx={{ mb: 1 }}>Payment Successful</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        <MoneyDisplay amount={session.amount} currency={session.currency} /> has been processed.
      </Typography>
      <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 3, fontFamily: 'monospace' }}>
        Session: {session.session_id}
      </Typography>
      <Button onClick={() => navigate(`/checkouts`)} variant="outlined">
        View Checkouts
      </Button>
    </Box>
  );
}

function FailedScreen({ onRetry }: { session?: PaymentSession; onRetry?: () => void }) {
  const navigate = useNavigate();
  return (
    <Box sx={{ textAlign: 'center', py: 6 }}>
      <ErrorIcon sx={{ fontSize: 56, color: '#f85149', mb: 2 }} />
      <Typography variant="h6" sx={{ mb: 1 }}>Payment Failed</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        All attempts have been exhausted or the session has been cancelled.
      </Typography>
      <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
        {onRetry && (
          <Button variant="contained" onClick={onRetry}>
            Retry
          </Button>
        )}
        <Button onClick={() => navigate('/checkouts')} variant="outlined">
          View Checkouts
        </Button>
      </Box>
    </Box>
  );
}

function ExpiredScreen({ session }: { session: PaymentSession }) {
  const navigate = useNavigate();
  return (
    <Box sx={{ textAlign: 'center', py: 6 }}>
      <AccessTimeIcon sx={{ fontSize: 56, color: '#8b949e', mb: 2 }} />
      <Typography variant="h6" sx={{ mb: 1 }}>Session Expired</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        This payment session expired at{' '}
        <strong>{new Date(session.expires_at).toLocaleString()}</strong>.
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Please initiate a new checkout.
      </Typography>
      <Button onClick={() => navigate('/checkouts')} variant="outlined">
        New Checkout
      </Button>
    </Box>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function PaymentSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<PaymentSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [paymentMethod, setPaymentMethod] = useState('CARD');
  const [paying, setPaying] = useState(false);
  const [networkError, setNetworkError] = useState(false);
  const [lastFailureReason, setLastFailureReason] = useState<string | null>(null);

  const fetchSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      const res = await getPaymentSession(sessionId);
      setSession(res.data.data as PaymentSession);
      setError(null);
    } catch {
      setError('Failed to load payment session');
    }
  }, [sessionId]);

  useEffect(() => {
    setLoading(true);
    fetchSession().finally(() => setLoading(false));
  }, [fetchSession]);

  const handlePay = async () => {
    if (!session) return;
    const idempotencyKey = generateIdempotencyKey();
    setPaying(true);
    setNetworkError(false);
    setLastFailureReason(null);

    try {
      const res = await createPaymentAttempt(session.session_id, {
        idempotency_key: idempotencyKey,
        payment_method: paymentMethod,
      });
      // Request succeeded — re-fetch for authoritative state
      const attemptData = res.data.data;
      if (attemptData?.failure_reason) {
        setLastFailureReason(attemptData.failure_reason);
      }
      await fetchSession();
    } catch {
      // Network error — unknown state. Re-fetch to discover authoritative state.
      setNetworkError(true);
      await fetchSession();
    } finally {
      setPaying(false);
    }
  };

  if (loading) return (
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', backgroundColor: '#0f1117' }}>
      <LoadingState message="Loading payment session…" />
    </Box>
  );

  if (error || !session) return (
    <Box sx={{ p: 4, backgroundColor: '#0f1117', minHeight: '100vh' }}>
      <Alert severity="error">{error ?? 'Session not found'}</Alert>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/payments')} sx={{ mt: 2 }}>
        Back to Payments
      </Button>
    </Box>
  );

  const remaining = session.max_attempts - session.attempt_count;

  return (
    <Box
      sx={{
        minHeight: '100vh',
        backgroundColor: '#0f1117',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2,
      }}
    >
      <Box sx={{ width: '100%', maxWidth: 520 }}>
        {/* Header */}
        <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
          <Button
            startIcon={<ArrowBackIcon />}
            size="small"
            onClick={() => navigate('/payments')}
            sx={{ color: '#8b949e' }}
          >
            Payments
          </Button>
          <Typography variant="caption" sx={{ color: '#30363d' }}>/</Typography>
          <Typography variant="caption" sx={{ color: '#8b949e', fontFamily: 'monospace' }}>
            {session.session_id.slice(0, 12)}…
          </Typography>
        </Box>

        <Paper sx={{ p: 3 }}>
          {/* Session metadata */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Amount Due
            </Typography>
            <Typography sx={{ fontSize: '2rem', fontWeight: 700, color: 'text.primary', mt: 0.5 }}>
              <MoneyDisplay amount={session.amount} currency={session.currency} />
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              {session.currency}
            </Typography>
          </Box>

          <Divider sx={{ borderColor: '#30363d', mb: 2 }} />

          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 1.5, mb: 3 }}>
            <Box>
              <Typography variant="caption" color="text.secondary">Status</Typography>
              <Box sx={{ mt: 0.5 }}><StatusChip status={session.status} /></Box>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Attempts</Typography>
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                {session.attempt_count} / {session.max_attempts}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Remaining</Typography>
              <Typography
                variant="body2"
                sx={{ mt: 0.5, color: remaining === 0 ? 'error.main' : remaining === 1 ? 'warning.main' : 'success.main' }}
              >
                {remaining}
              </Typography>
            </Box>
          </Box>

          <Box sx={{ mb: 3 }}>
            <Typography variant="caption" color="text.secondary">Expires</Typography>
            <Typography variant="body2" sx={{ mt: 0.25 }}>
              {new Date(session.expires_at).toLocaleString()}
            </Typography>
          </Box>

          {networkError && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              Network error — loading latest session state from backend…
            </Alert>
          )}

          {lastFailureReason && session.ui_state === 'RETRY' && (
            <Alert severity="error" sx={{ mb: 2 }}>
              Payment declined: {lastFailureReason}
            </Alert>
          )}

          {/* Render based on ui_state */}
          {session.ui_state === 'SUCCESS' && <SuccessScreen session={session} />}
          {session.ui_state === 'FAILED' && <FailedScreen session={session} />}
          {session.ui_state === 'EXPIRED' && <ExpiredScreen session={session} />}

          {(session.ui_state === 'PAYMENT_PAGE' || session.ui_state === 'RETRY') && (
            <Box>
              {session.ui_state === 'RETRY' && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  Previous attempt failed. {remaining} attempt{remaining !== 1 ? 's' : ''} remaining.
                </Alert>
              )}

              <FormControl size="small" fullWidth sx={{ mb: 2 }}>
                <InputLabel>Payment Method</InputLabel>
                <Select
                  value={paymentMethod}
                  label="Payment Method"
                  onChange={(e: SelectChangeEvent) => setPaymentMethod(e.target.value)}
                  disabled={paying}
                >
                  {PAYMENT_METHODS.map((m) => (
                    <MenuItem key={m} value={m}>{m.replace('_', ' ')}</MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Button
                variant="contained"
                fullWidth
                size="large"
                disabled={paying || remaining === 0}
                onClick={handlePay}
                sx={{ py: 1.25 }}
              >
                {paying ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CircularProgress size={16} color="inherit" />
                    Processing…
                  </Box>
                ) : session.ui_state === 'RETRY' ? (
                  `Retry Payment (${remaining} left)`
                ) : (
                  'Pay Now'
                )}
              </Button>
            </Box>
          )}
        </Paper>

        {/* Attempts history */}
        {session.attempts && session.attempts.length > 0 && (
          <Paper sx={{ mt: 2, p: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1.5, color: 'text.secondary' }}>
              Attempt History
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Attempt ID</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Reason</TableCell>
                  <TableCell>Time</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {session.attempts.map((a) => (
                  <TableRow key={a.attempt_id}>
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.72rem' }}>
                      {a.attempt_id.slice(0, 12)}…
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={a.status}
                        color={a.status === 'SUCCESS' ? 'success' : a.status === 'FAILED' ? 'error' : 'default'}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                      {a.failure_reason ?? '—'}
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                      {new Date(a.created_at).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        )}
      </Box>
    </Box>
  );
}
