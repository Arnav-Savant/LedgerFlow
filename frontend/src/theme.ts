import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'dark',
    background: { default: '#0c0e13', paper: '#13161e' },
    primary: { main: '#6e8efb' },
    secondary: { main: '#8b949e' },
    success: { main: '#3fb950' },
    warning: { main: '#d29922' },
    error: { main: '#f85149' },
    divider: '#21262d',
    text: { primary: '#e6edf3', secondary: '#7d8590' },
  },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", system-ui, sans-serif',
    fontSize: 13,
    h5: { fontWeight: 600, letterSpacing: '-0.01em' },
    h6: { fontSize: '0.9rem', fontWeight: 600, letterSpacing: '-0.01em' },
    subtitle2: { fontWeight: 600 },
  },
  shape: { borderRadius: 8 },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none', border: '1px solid #21262d', boxShadow: '0 1px 3px rgba(0,0,0,0.3)' },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: '#21262d', padding: '10px 14px', fontSize: '0.82rem' },
        head: {
          backgroundColor: '#0c0e13',
          fontWeight: 600,
          color: '#7d8590',
          textTransform: 'uppercase' as const,
          fontSize: '0.69rem',
          letterSpacing: '0.08em',
        },
      },
    },
    MuiChip: {
      styleOverrides: { root: { fontSize: '0.72rem', height: 22, fontWeight: 500 } },
    },
    MuiButton: {
      defaultProps: { size: 'small' },
      styleOverrides: {
        root: { textTransform: 'none', fontSize: '0.82rem', fontWeight: 500, borderRadius: 6 },
        contained: { boxShadow: 'none', '&:hover': { boxShadow: '0 2px 8px rgba(110,142,251,0.3)' } },
      },
    },
    MuiTextField: { defaultProps: { size: 'small' } },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          '& .MuiOutlinedInput-notchedOutline': { borderColor: '#30363d' },
          '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(110,142,251,0.4)' },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#6e8efb', borderWidth: '1.5px' },
        },
      },
    },
    MuiSelect: { styleOverrides: { root: { borderRadius: 6 } } },
    MuiTableRow: {
      styleOverrides: {
        root: { transition: 'background-color 0.1s', '&:hover': { backgroundColor: 'rgba(110,142,251,0.05)' } },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: { backgroundColor: '#13161e', border: '1px solid #21262d', borderRadius: '10px' },
      },
    },
    MuiTablePagination: {
      styleOverrides: {
        root: { borderTop: '1px solid #21262d', color: '#7d8590', fontSize: '0.8rem' },
        select: { fontSize: '0.8rem' },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: { fontSize: '0.85rem', '&.Mui-focused': { color: '#6e8efb' } },
      },
    },
    MuiDivider: { styleOverrides: { root: { borderColor: '#21262d' } } },
  },
});

export default theme;
