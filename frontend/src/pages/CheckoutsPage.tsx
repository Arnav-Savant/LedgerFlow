import { useEffect, useState } from 'react';
import {
  Box, Paper, Table, TableBody, TableCell, TableHead, TableRow,
  Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Snackbar, Alert, MenuItem, Select, FormControl, InputLabel,
  IconButton, Typography, Divider,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { useNavigate } from 'react-router-dom';
import { listCheckouts, initiateCheckout, listUsers, listProducts } from '../api/commerceApi';
import type { Checkout, User, Product, CheckoutInitiateResponse } from '../api/types';
import PageHeader from '../components/common/PageHeader';
import LoadingState from '../components/common/LoadingState';
import ErrorAlert from '../components/common/ErrorAlert';
import StatusChip from '../components/common/StatusChip';
import MoneyDisplay from '../components/common/MoneyDisplay';

interface ProductLine { product_id: string; quantity: string; }

export default function CheckoutsPage() {
  const [checkouts, setCheckouts] = useState<Checkout[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [userId, setUserId] = useState('');
  const [lines, setLines] = useState<ProductLine[]>([{ product_id: '', quantity: '1' }]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CheckoutInitiateResponse | null>(null);
  const [snack, setSnack] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [cRes, uRes, pRes] = await Promise.all([listCheckouts(), listUsers(), listProducts()]);
      setCheckouts(cRes.data.data as Checkout[]);
      setUsers(uRes.data.data as User[]);
      setProducts((pRes.data.data as Product[]).filter((p) => p.is_active));
    } catch {
      setError('Failed to load checkouts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setUserId('');
    setLines([{ product_id: '', quantity: '1' }]);
    setResult(null);
    setDialogOpen(true);
  };

  const addLine = () => setLines([...lines, { product_id: '', quantity: '1' }]);

  const removeLine = (i: number) => setLines(lines.filter((_, idx) => idx !== i));

  const updateLine = (i: number, field: keyof ProductLine, value: string) => {
    const updated = [...lines];
    updated[i] = { ...updated[i], [field]: value };
    setLines(updated);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const res = await initiateCheckout({
        user_id: userId,
        products: lines.map((l) => ({ product_id: l.product_id, quantity: parseInt(l.quantity, 10) })),
      });
      setResult(res.data.data as CheckoutInitiateResponse);
      load();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message ?? 'Checkout failed';
      setSnack(`Error: ${msg}`);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingState />;
  if (error) return <ErrorAlert error={error} onRetry={load} />;

  return (
    <Box>
      <PageHeader
        title="Checkouts"
        subtitle={`${checkouts.length} total`}
        action={{ label: 'New Checkout', icon: <AddIcon />, onClick: openCreate }}
      />

      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Checkout ID</TableCell>
              <TableCell>User</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Total</TableCell>
              <TableCell>Session ID</TableCell>
              <TableCell>Created</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {checkouts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ color: 'text.secondary', py: 3 }}>
                  No checkouts
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
                    {c.checkout_id.slice(0, 12)}…
                  </TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'text.secondary' }}>
                    {c.user_id.slice(0, 8)}…
                  </TableCell>
                  <TableCell><StatusChip status={c.checkout_status} /></TableCell>
                  <TableCell><MoneyDisplay amount={c.total_amount} currency="INR" /></TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'text.secondary' }}>
                    {c.payment_session_id ? `${c.payment_session_id.slice(0, 12)}…` : '—'}
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

      {/* Create Checkout Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Initiate Checkout</DialogTitle>
        <DialogContent sx={{ pt: '16px !important' }}>
          {result ? (
            <Box>
              <Alert severity="success" sx={{ mb: 2 }}>Checkout initiated successfully</Alert>
              <Box sx={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 0.5, fontSize: '0.82rem', mb: 2 }}>
                <Typography variant="caption" color="text.secondary">Checkout ID</Typography>
                <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>{result.checkout_id}</Typography>
                <Typography variant="caption" color="text.secondary">Status</Typography>
                <Typography variant="caption"><StatusChip status={result.checkout_status} /></Typography>
                <Typography variant="caption" color="text.secondary">Total</Typography>
                <Typography variant="caption"><MoneyDisplay amount={result.total_amount} currency="INR" /></Typography>
                <Typography variant="caption" color="text.secondary">Session ID</Typography>
                <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>{result.payment_session_id}</Typography>
              </Box>
              <Button
                variant="contained"
                startIcon={<OpenInNewIcon />}
                onClick={() => {
                  setDialogOpen(false);
                  navigate(`/payments/session/${result.payment_session_id}`);
                }}
              >
                Go to Payment
              </Button>
            </Box>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <FormControl size="small" required>
                <InputLabel>User</InputLabel>
                <Select
                  value={userId}
                  label="User"
                  onChange={(e: SelectChangeEvent) => setUserId(e.target.value)}
                >
                  {users.map((u) => (
                    <MenuItem key={u.user_id} value={u.user_id}>{u.name} ({u.email})</MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Divider sx={{ borderColor: '#30363d' }} />
              <Typography variant="caption" color="text.secondary">Products</Typography>

              {lines.map((line, i) => (
                <Box key={i} sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                  <FormControl size="small" sx={{ flex: 1 }}>
                    <InputLabel>Product</InputLabel>
                    <Select
                      value={line.product_id}
                      label="Product"
                      onChange={(e: SelectChangeEvent) => updateLine(i, 'product_id', e.target.value)}
                    >
                      {products.map((p) => (
                        <MenuItem key={p.product_id} value={p.product_id}>
                          {p.name} (<MoneyDisplay amount={p.price} currency={p.currency} />)
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <TextField
                    label="Qty"
                    type="number"
                    value={line.quantity}
                    onChange={(e) => updateLine(i, 'quantity', e.target.value)}
                    sx={{ width: 72 }}
                    slotProps={{ htmlInput: { min: 1 } }}
                  />
                  {lines.length > 1 && (
                    <IconButton size="small" onClick={() => removeLine(i)} sx={{ mt: 0.5 }}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  )}
                </Box>
              ))}

              <Button size="small" onClick={addLine} sx={{ alignSelf: 'flex-start' }}>
                + Add Product
              </Button>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>
            {result ? 'Close' : 'Cancel'}
          </Button>
          {!result && (
            <Button variant="contained" onClick={handleSubmit} disabled={submitting || !userId}>
              {submitting ? 'Processing…' : 'Initiate Checkout'}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!snack}
        autoHideDuration={4000}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity={snack?.startsWith('Error') ? 'error' : 'success'} onClose={() => setSnack(null)}>
          {snack}
        </Alert>
      </Snackbar>
    </Box>
  );
}
