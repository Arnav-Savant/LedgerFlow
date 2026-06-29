import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import theme from './theme';
import AppLayout from './components/layout/AppLayout';
import DashboardPage from './pages/DashboardPage';
import UsersPage from './pages/UsersPage';
import SellersPage from './pages/SellersPage';
import ProductsPage from './pages/ProductsPage';
import InventoryPage from './pages/InventoryPage';
import CheckoutsPage from './pages/CheckoutsPage';
import CheckoutDetailPage from './pages/CheckoutDetailPage';
import OrdersPage from './pages/OrdersPage';
import PaymentsPage from './pages/PaymentsPage';
import PaymentSessionPage from './pages/PaymentSessionPage';

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          {/* Payment simulator — standalone layout (no sidebar) */}
          <Route path="/payments/session/:sessionId" element={<PaymentSessionPage />} />

          {/* All other pages — wrapped in AppLayout with sidebar */}
          <Route
            path="*"
            element={
              <AppLayout>
                <Routes>
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/users" element={<UsersPage />} />
                  <Route path="/sellers" element={<SellersPage />} />
                  <Route path="/products" element={<ProductsPage />} />
                  <Route path="/inventory" element={<InventoryPage />} />
                  <Route path="/checkouts" element={<CheckoutsPage />} />
                  <Route path="/checkouts/:checkoutId" element={<CheckoutDetailPage />} />
                  <Route path="/orders" element={<OrdersPage />} />
                  <Route path="/payments" element={<PaymentsPage />} />
                </Routes>
              </AppLayout>
            }
          />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
