import { Box, Typography, Button } from '@mui/material';

interface Action {
  label: string;
  onClick: () => void;
  icon?: React.ReactNode;
}

interface Props {
  title: string;
  subtitle?: string;
  action?: Action;
}

export default function PageHeader({ title, subtitle, action }: Props) {
  return (
    <Box sx={{ mb: 2.5, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
      <Box>
        <Typography variant="h6" sx={{ color: 'text.primary', mb: 0.25 }}>
          {title}
        </Typography>
        {subtitle && (
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            {subtitle}
          </Typography>
        )}
      </Box>
      {action && (
        <Button variant="outlined" size="small" startIcon={action.icon} onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </Box>
  );
}
