import { useEffect, useState } from 'react';
import {
  Box, Paper, Table, TableBody, TableCell, TableHead, TableRow,
  IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Button, Tooltip, TablePagination,
} from '@mui/material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutlined';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutlined';
import toast from 'react-hot-toast';
import { listInventory, listProducts, updateStock } from '../api/commerceApi';
import type { Inventory, Product } from '../api/types';
import PageHeader from '../components/common/PageHeader';
import LoadingState from '../components/common/LoadingState';
import ErrorAlert from '../components/common/ErrorAlert';

export default function InventoryPage() {
  const [inventory, setInventory] = useState<Inventory[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stockOp, setStockOp] = useState<'add' | 'remove' | null>(null);
  const [stockTarget, setStockTarget] = useState<Inventory | null>(null);
  const [stockQty, setStockQty] = useState('');
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [invRes, prodRes] = await Promise.all([
        listInventory(page * rowsPerPage, rowsPerPage),
        listProducts(0, 1000),
      ]);
      const invData = invRes.data.data;
      setInventory(invData.items);
      setTotal(invData.total);
      setProducts(prodRes.data.data.items);
    } catch {
      setError('Failed to load inventory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [page, rowsPerPage]);

  const productName = (id: string) => products.find((p) => p.product_id === id)?.name ?? id.slice(0, 8);

  const openDialog = (inv: Inventory, op: 'add' | 'remove') => {
    setStockTarget(inv);
    setStockOp(op);
    setStockQty('');
  };

  const closeDialog = () => {
    setStockTarget(null);
    setStockOp(null);
    setStockQty('');
  };

  const handleStockUpdate = async () => {
    if (!stockTarget || !stockOp || !stockQty) return;
    setSaving(true);
    try {
      await updateStock(stockTarget.product_id, stockOp, parseInt(stockQty, 10));
      toast.success(`Stock ${stockOp}ed successfully`);
      closeDialog();
      load();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message ?? 'Operation failed';
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingState />;
  if (error) return <ErrorAlert error={error} onRetry={load} />;

  return (
    <Box>
      <PageHeader title="Inventory" subtitle={`${total} products tracked`} />

      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Product</TableCell>
              <TableCell>Product ID</TableCell>
              <TableCell>Available</TableCell>
              <TableCell>Reserved</TableCell>
              <TableCell>Last Updated</TableCell>
              <TableCell align="right">Actions</TableCell>
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
                    <Tooltip title="Add Stock">
                      <IconButton
                        size="small"
                        onClick={() => openDialog(inv, 'add')}
                        sx={{ color: 'success.main' }}
                      >
                        <AddCircleOutlineIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Remove Stock">
                      <IconButton
                        size="small"
                        onClick={() => openDialog(inv, 'remove')}
                        sx={{ color: 'error.main' }}
                      >
                        <RemoveCircleOutlineIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
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
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
          rowsPerPageOptions={[10, 20, 50]}
        />
      </Paper>

      <Dialog open={!!stockTarget} onClose={closeDialog} maxWidth="xs" fullWidth>
        <DialogTitle>{stockOp === 'add' ? 'Add Stock' : 'Remove Stock'}</DialogTitle>
        <DialogContent sx={{ pt: '16px !important' }}>
          {stockTarget && (
            <Box sx={{ mb: 2, fontSize: '0.82rem', color: 'text.secondary' }}>
              Product: <strong style={{ color: '#e6edf3' }}>{productName(stockTarget.product_id)}</strong>
              <br />
              Current available: <strong style={{ color: '#e6edf3' }}>{stockTarget.available_quantity}</strong>
            </Box>
          )}
          <TextField
            label="Quantity"
            type="number"
            value={stockQty}
            onChange={(e) => setStockQty(e.target.value)}
            slotProps={{ htmlInput: { min: 1 } }}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialog}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleStockUpdate}
            disabled={saving || !stockQty}
            color={stockOp === 'add' ? 'success' : 'error'}
          >
            {saving ? 'Saving…' : stockOp === 'add' ? 'Add' : 'Remove'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
