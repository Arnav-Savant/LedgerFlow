import { Box, Typography } from '@mui/material';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutlined';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutlined';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';

export interface TimelineEvent {
  id: string;
  label: string;
  timestamp?: string;
  status: 'completed' | 'failed' | 'pending';
  detail?: string;
}

const iconMap = {
  completed: <CheckCircleOutlineIcon sx={{ fontSize: 18, color: '#3fb950' }} />,
  failed: <ErrorOutlineIcon sx={{ fontSize: 18, color: '#f85149' }} />,
  pending: <HourglassEmptyIcon sx={{ fontSize: 18, color: '#8b949e' }} />,
};

export default function Timeline({ events }: { events: TimelineEvent[] }) {
  return (
    <Box>
      {events.map((event, i) => (
        <Box key={event.id} sx={{ display: 'flex', gap: 1.5 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Box sx={{ mt: 0.25 }}>{iconMap[event.status]}</Box>
            {i < events.length - 1 && (
              <Box sx={{ width: 1, flexGrow: 1, backgroundColor: '#30363d', my: 0.5, minHeight: 16 }} />
            )}
          </Box>
          <Box sx={{ pb: 2 }}>
            <Typography
              variant="body2"
              sx={{ color: 'text.primary', fontWeight: 500, lineHeight: 1.3 }}
            >
              {event.label}
            </Typography>
            {event.timestamp && (
              <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                {new Date(event.timestamp).toLocaleString()}
              </Typography>
            )}
            {event.detail && (
              <Typography variant="caption" sx={{ color: '#8b949e', mt: 0.25, display: 'block' }}>
                {event.detail}
              </Typography>
            )}
          </Box>
        </Box>
      ))}
    </Box>
  );
}
