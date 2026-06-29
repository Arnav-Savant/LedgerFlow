import { useEffect, useState } from 'react';
import {
  Box, Paper, Table, TableBody, TableCell, TableHead, TableRow,
  IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Button, Tooltip, Snackbar, Alert,
} from '@mui/material';
import TuneIcon from '@mui/icons-material/Tune';
import { listInventory, adjustInventory, listProducts } from '../api/commerceApi';
import type { Inventory, Product } from '../api/types';
import PageHeader from '../components/common/PageHeader';
import LoadingState from '../components/common/LoadingState';
import ErrorAlert from '../components/common/ErrorAlert';

export default function InventoryPage() {
  const [inventory, setInventory] = useState<Inventory[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adjustTarget, setAdjustTarget] = useState<Inventory | null>(null);
  const [delta, setDelta] = useState('');
  const [saving, setSaving] = useState(false);
  const [snack, setSnack] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [invRes, prodRes] = await Promise.all([listInventory(), listProducts()]);
      setInventory(invRes.data.data as Inventory[]);
      setProducts(prodRes.data.data as Product[]);
    } catch {
      setError('Failed to load inventory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const productName = (id: string) => products.find((p) => p.product_id === id)?.name ?? id.slice(0, 8);

  const handleAdjust = async () => {
    if (!adjustTarget || !delta) return;
    setSaving(true);
    try {
      await adjustInventory(adjustTarget.product_id, parseInt(delta, 10));
      setSnack(`Inventory adjusted by ${delta}`);
      setAdjustTarget(null);
      setDelta('');
      load();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message ?? 'Adjust failed';
      setSnack(`Error: ${msg}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingState />;
  if (error) return <ErrorAlert error={error} onRetry={load} />;

  return (
    <Box>
      <PageHeader title="Inventory" subtitle={`${inventory.length} products tracked`} />

      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Product</TableCell>
              <TableCell>Product ID</TableCell>
              <TableCell>Available</TableCell>
              <TableCell>Reserved</TableCell>
              <TableCell>Last Updated</TableCell>
              <TableCell align="right">Adjust</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {inventory.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ color: 'text.secondary', py: 3 }}>
                  No inventory records
                </TableCell>
              </TableRow>
            ) : (
              inventory.map((inv) => (
                <TableRow key={inv.inventory_id}>
                  <TableCell>{productName(inv.product_id)}</TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'text.secondary' }}>
                    {inv.product_id.slice(0, 12)}…
                  </TableCell>
                  <TableCell sx={{ color: inv.available_quantity === 0 ? 'error.main' : 'success.main', fontWeight: 600 }}>
                    {inv.available_quantity}
                  </TableCell>
                  <TableCell sx={{ color: inv.reserved_quantity > 0 ? 'warning.main' : 'text.secondary' }}>
                    {inv.reserved_quantity}
                  </TableCell>
                  <TableCell sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                    {inv.updated_at ? new Date(inv.updated_at).toLocaleString() : '—'}
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="Adjust available quantity">
                      <IconButton
                        size="small"
                        onClick={() => { setAdjustTarget(inv); setDelta(''); }}
                      >
                        <TuneIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Paper>

      <Dialog open={!!adjustTarget} onClose={() => setAdjustTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Adjust Available Quantity</DialogTitle>
        <DialogContent sx={{ pt: '16px !important' }}>
          {adjustTarget && (
            <Box sx={{ mb: 2, fontSize: '0.82rem', color: 'text.secondary' }}>
              Product: <strong style={{ color: '#e6edf3' }}>{productName(adjustTarget.product_id)}</strong>
              <br />
              Current available: <strong style={{ color: '#e6edf3' }}>{adjustTarget.available_quantity}</strong>
            </Box>
          )}
          <TextField
            label="Delta (positive to add, negative to remove)"
            type="number"
            value={delta}
            onChange={(e) => setDelta(e.target.value)}
            fullWidth
            helperText="e.g. +10 to add 10 units, -5 to remove 5 units"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAdjustTarget(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleAdjust} disabled={saving || !delta}>
            {saving ? 'Adjusting…' : 'Apply'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!snack}
        autoHideDuration={3000}
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
