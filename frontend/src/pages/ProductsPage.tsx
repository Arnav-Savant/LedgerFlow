import { useEffect, useState } from 'react';
import {
  Box, Paper, Table, TableBody, TableCell, TableHead, TableRow,
  IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Button, Tooltip, Snackbar, Alert, Chip,
  MenuItem, Select, FormControl, InputLabel,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import BlockIcon from '@mui/icons-material/Block';
import { listProducts, createProduct, updateProduct, deactivateProduct, listSellers } from '../api/commerceApi';
import type { Product, Seller } from '../api/types';
import PageHeader from '../components/common/PageHeader';
import LoadingState from '../components/common/LoadingState';
import ErrorAlert from '../components/common/ErrorAlert';
import MoneyDisplay from '../components/common/MoneyDisplay';

const CURRENCIES = ['INR', 'USD', 'GBP', 'EUR', 'JPY'];

interface ProductForm {
  seller_id: string;
  name: string;
  price: string;
  currency: string;
}
const emptyForm: ProductForm = { seller_id: '', name: '', price: '', currency: 'INR' };

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Product | null>(null);
  const [form, setForm] = useState<ProductForm>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [snack, setSnack] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [pRes, sRes] = await Promise.all([listProducts(), listSellers()]);
      setProducts(pRes.data.data as Product[]);
      setSellers(sRes.data.data as Seller[]);
    } catch {
      setError('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const sellerName = (id: string) => sellers.find((s) => s.seller_id === id)?.name ?? id.slice(0, 8);

  const openCreate = () => {
    setEditTarget(null);
    setForm(emptyForm);
    setDialogOpen(true);
  };

  const openEdit = (product: Product) => {
    setEditTarget(product);
    setForm({
      seller_id: product.seller_id,
      name: product.name,
      price: String(product.price),
      currency: product.currency,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editTarget) {
        const payload: Partial<{ name: string; price: number }> = {};
        if (form.name) payload.name = form.name;
        if (form.price) payload.price = parseInt(form.price, 10);
        await updateProduct(editTarget.product_id, payload);
        setSnack('Product updated');
      } else {
        await createProduct({
          seller_id: form.seller_id,
          name: form.name,
          price: parseInt(form.price, 10),
          currency: form.currency,
        });
        setSnack('Product created');
      }
      setDialogOpen(false);
      load();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message ?? 'Save failed';
      setSnack(`Error: ${msg}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async (product: Product) => {
    if (!window.confirm(`Deactivate product ${product.name}? Historical orders remain valid.`)) return;
    try {
      await deactivateProduct(product.product_id);
      setSnack('Product deactivated');
      load();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message ?? 'Deactivate failed';
      setSnack(`Error: ${msg}`);
    }
  };

  if (loading) return <LoadingState />;
  if (error) return <ErrorAlert error={error} onRetry={load} />;

  return (
    <Box>
      <PageHeader
        title="Products"
        subtitle={`${products.length} total`}
        action={{ label: 'New Product', icon: <AddIcon />, onClick: openCreate }}
      />

      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Seller</TableCell>
              <TableCell>Price</TableCell>
              <TableCell>Currency</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {products.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ color: 'text.secondary', py: 3 }}>
                  No products
                </TableCell>
              </TableRow>
            ) : (
              products.map((p) => (
                <TableRow key={p.product_id}>
                  <TableCell>{p.name}</TableCell>
                  <TableCell sx={{ color: 'text.secondary' }}>{sellerName(p.seller_id)}</TableCell>
                  <TableCell>
                    <MoneyDisplay amount={p.price} currency={p.currency} />
                  </TableCell>
                  <TableCell sx={{ color: 'text.secondary' }}>{p.currency}</TableCell>
                  <TableCell>
                    <Chip
                      label={p.is_active ? 'Active' : 'Inactive'}
                      color={p.is_active ? 'success' : 'default'}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                    {p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="Edit">
                      <IconButton size="small" onClick={() => openEdit(p)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    {p.is_active && (
                      <Tooltip title="Deactivate">
                        <IconButton size="small" color="warning" onClick={() => handleDeactivate(p)}>
                          <BlockIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Paper>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{editTarget ? 'Edit Product' : 'New Product'}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '16px !important' }}>
          {!editTarget && (
            <FormControl size="small" required>
              <InputLabel>Seller</InputLabel>
              <Select
                value={form.seller_id}
                label="Seller"
                onChange={(e: SelectChangeEvent) => setForm({ ...form, seller_id: e.target.value })}
              >
                {sellers.filter((s) => s.is_active).map((s) => (
                  <MenuItem key={s.seller_id} value={s.seller_id}>{s.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
          <TextField
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          <TextField
            label="Price (in smallest unit, e.g. paise)"
            type="number"
            value={form.price}
            onChange={(e) => setForm({ ...form, price: e.target.value })}
            required
            helperText="e.g. 50000 = ₹500.00"
          />
          {!editTarget && (
            <FormControl size="small">
              <InputLabel>Currency</InputLabel>
              <Select
                value={form.currency}
                label="Currency"
                onChange={(e: SelectChangeEvent) => setForm({ ...form, currency: e.target.value })}
              >
                {CURRENCIES.map((c) => <MenuItem key={c} value={c}>{c}</MenuItem>)}
              </Select>
            </FormControl>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
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
