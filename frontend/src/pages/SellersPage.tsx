import { useEffect, useState } from 'react';
import {
  Box, Paper, Table, TableBody, TableCell, TableHead, TableRow,
  IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Button, Tooltip, Chip, TablePagination,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import BlockIcon from '@mui/icons-material/Block';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { listSellers, createSeller, updateSeller, disableSeller, reactivateSeller } from '../api/commerceApi';
import type { Seller } from '../api/types';
import PageHeader from '../components/common/PageHeader';
import LoadingState from '../components/common/LoadingState';
import ErrorAlert from '../components/common/ErrorAlert';
import toast from 'react-hot-toast';

interface SellerForm { name: string; email: string; }
const emptyForm: SellerForm = { name: '', email: '' };

export default function SellersPage() {
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const [total, setTotal] = useState(0);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Seller | null>(null);
  const [form, setForm] = useState<SellerForm>(emptyForm);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listSellers(page * rowsPerPage, rowsPerPage);
      setSellers(res.data.data.items);
      setTotal(res.data.data.total);
    } catch {
      setError('Failed to load sellers');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [page, rowsPerPage]);

  const openCreate = () => {
    setEditTarget(null);
    setForm(emptyForm);
    setDialogOpen(true);
  };

  const openEdit = (seller: Seller) => {
    setEditTarget(seller);
    setForm({ name: seller.name, email: seller.email });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editTarget) {
        await updateSeller(editTarget.seller_id, { name: form.name, email: form.email });
        toast.success('Seller updated');
      } else {
        await createSeller({ name: form.name, email: form.email });
        toast.success('Seller created');
      }
      setDialogOpen(false);
      load();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message ?? 'Save failed';
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDisable = async (seller: Seller) => {
    if (!window.confirm(`Disable seller ${seller.name}? Historical orders will remain intact.`)) return;
    try {
      await disableSeller(seller.seller_id);
      toast.success('Seller disabled');
      load();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message ?? 'Disable failed';
      toast.error(msg);
    }
  };

  const handleReactivate = async (seller: Seller) => {
    try {
      await reactivateSeller(seller.seller_id);
      toast.success(`${seller.name} reactivated`);
      load();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message ?? 'Reactivate failed';
      toast.error(msg);
    }
  };

  if (loading) return <LoadingState />;
  if (error) return <ErrorAlert error={error} onRetry={load} />;

  return (
    <Box>
      <PageHeader
        title="Sellers"
        subtitle={`${total} total`}
        action={{ label: 'New Seller', icon: <AddIcon />, onClick: openCreate }}
      />

      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sellers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ color: 'text.secondary', py: 3 }}>
                  No sellers
                </TableCell>
              </TableRow>
            ) : (
              sellers.map((s) => (
                <TableRow key={s.seller_id}>
                  <TableCell>{s.name}</TableCell>
                  <TableCell sx={{ color: 'text.secondary' }}>{s.email}</TableCell>
                  <TableCell>
                    <Chip
                      label={s.is_active ? 'Active' : 'Disabled'}
                      color={s.is_active ? 'success' : 'default'}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                    {s.created_at ? new Date(s.created_at).toLocaleDateString() : '—'}
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="Edit">
                      <IconButton size="small" onClick={() => openEdit(s)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    {s.is_active ? (
                      <Tooltip title="Disable">
                        <IconButton size="small" color="warning" onClick={() => handleDisable(s)}>
                          <BlockIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    ) : (
                      <Tooltip title="Reactivate">
                        <IconButton size="small" color="success" onClick={() => handleReactivate(s)}>
                          <CheckCircleIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
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
          onPageChange={(_, p) => setPage(p)}
          onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
          rowsPerPageOptions={[10, 20, 50, 100]}
        />
      </Paper>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{editTarget ? 'Edit Seller' : 'New Seller'}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '16px !important' }}>
          <TextField
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
            fullWidth
          />
          <TextField
            label="Email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
