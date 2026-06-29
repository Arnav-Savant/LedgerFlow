import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'dark',
    background: {
      default: '#0f1117',
      paper: '#161b22',
    },
    primary: { main: '#58a6ff' },
    secondary: { main: '#8b949e' },
    success: { main: '#3fb950' },
    warning: { main: '#d29922' },
    error: { main: '#f85149' },
    divider: '#30363d',
    text: {
      primary: '#e6edf3',
      secondary: '#8b949e',
    },
  },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
    fontSize: 13,
    h6: { fontSize: '0.9rem', fontWeight: 600 },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none', border: '1px solid #30363d' },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: '#30363d', padding: '8px 12px', fontSize: '0.82rem' },
        head: {
          backgroundColor: '#161b22',
          fontWeight: 600,
          color: '#8b949e',
          textTransform: 'uppercase' as const,
          fontSize: '0.72rem',
          letterSpacing: '0.05em',
        },
      },
    },
    MuiChip: {
      styleOverrides: { root: { fontSize: '0.72rem', height: 22 } },
    },
    MuiButton: {
      defaultProps: { size: 'small' },
      styleOverrides: { root: { textTransform: 'none', fontSize: '0.8rem' } },
    },
    MuiTextField: {
      defaultProps: { size: 'small' },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover': { backgroundColor: 'rgba(88, 166, 255, 0.04)' },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: { backgroundColor: '#161b22', border: '1px solid #30363d' },
      },
    },
  },
});

export default theme;
