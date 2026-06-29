import { Drawer, List, ListItemButton, ListItemIcon, ListItemText, Box, Typography } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import DashboardIcon from '@mui/icons-material/Dashboard';
import PeopleIcon from '@mui/icons-material/People';
import StoreIcon from '@mui/icons-material/Store';
import InventoryIcon from '@mui/icons-material/Inventory';
import WarehouseIcon from '@mui/icons-material/Warehouse';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import ReceiptIcon from '@mui/icons-material/Receipt';
import PaymentIcon from '@mui/icons-material/Payment';

export const SIDEBAR_WIDTH = 200;

const navItems = [
  { label: 'Dashboard', icon: <DashboardIcon fontSize="small" />, path: '/' },
  { label: 'Users', icon: <PeopleIcon fontSize="small" />, path: '/users' },
  { label: 'Sellers', icon: <StoreIcon fontSize="small" />, path: '/sellers' },
  { label: 'Products', icon: <InventoryIcon fontSize="small" />, path: '/products' },
  { label: 'Inventory', icon: <WarehouseIcon fontSize="small" />, path: '/inventory' },
  { label: 'Checkouts', icon: <ShoppingCartIcon fontSize="small" />, path: '/checkouts' },
  { label: 'Orders', icon: <ReceiptIcon fontSize="small" />, path: '/orders' },
  { label: 'Payments', icon: <PaymentIcon fontSize="small" />, path: '/payments' },
];

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: SIDEBAR_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: SIDEBAR_WIDTH,
          boxSizing: 'border-box',
          backgroundColor: '#0d1117',
          borderRight: '1px solid #30363d',
        },
      }}
    >
      <Box sx={{ p: 2, borderBottom: '1px solid #30363d' }}>
        <Typography
          variant="subtitle2"
          sx={{ color: '#58a6ff', fontWeight: 700, fontSize: '0.85rem', letterSpacing: '0.05em' }}
        >
          LEDGERFLOW
        </Typography>
        <Typography variant="caption" sx={{ color: '#8b949e' }}>
          Engineering Console
        </Typography>
      </Box>
      <List dense sx={{ pt: 1 }}>
        {navItems.map((item) => {
          const selected =
            item.path === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.path);
          return (
            <ListItemButton
              key={item.path}
              selected={selected}
              onClick={() => navigate(item.path)}
              sx={{
                py: 0.75,
                px: 1.5,
                '&.Mui-selected': {
                  backgroundColor: 'rgba(88, 166, 255, 0.1)',
                  borderRight: '2px solid #58a6ff',
                },
                '&.Mui-selected .MuiListItemIcon-root': { color: '#58a6ff' },
                '&.Mui-selected .MuiListItemText-primary': { color: '#58a6ff' },
              }}
            >
              <ListItemIcon sx={{ minWidth: 32, color: '#8b949e' }}>{item.icon}</ListItemIcon>
              <ListItemText
                primary={item.label}
                slotProps={{ primary: { style: { fontSize: '0.82rem' } } }}
              />
            </ListItemButton>
          );
        })}
      </List>
    </Drawer>
  );
}
