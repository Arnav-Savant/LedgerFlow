import { Alert, AlertTitle, Button } from '@mui/material';

interface Props {
  error: string;
  onRetry?: () => void;
}

export default function ErrorAlert({ error, onRetry }: Props) {
  return (
    <Alert
      severity="error"
      action={
        onRetry ? (
          <Button color="inherit" size="small" onClick={onRetry}>
            Retry
          </Button>
        ) : undefined
      }
      sx={{ mb: 2 }}
    >
      <AlertTitle>Error</AlertTitle>
      {error}
    </Alert>
  );
}
