import { Box } from '@mui/material';
import Sidebar, { SIDEBAR_WIDTH } from './Sidebar';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', backgroundColor: 'background.default' }}>
      <Sidebar />
      <Box
        component="main"
        sx={{ flexGrow: 1, ml: `${SIDEBAR_WIDTH}px`, p: 3, maxWidth: `calc(100% - ${SIDEBAR_WIDTH}px)` }}
      >
        {children}
      </Box>
    </Box>
  );
}
