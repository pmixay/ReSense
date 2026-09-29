import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { ApiError } from './api/client';
import { installJobWatcher } from './api/hooks';
import './styles/fonts.css';
import './styles/tokens.css';
import './styles/base.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2000,
      refetchOnWindowFocus: false,
      // a 4xx will not fix itself and an offline backend is polled anyway: retry only 5xx, once
      retry: (count, err) => err instanceof ApiError && err.status >= 500 && !err.offline && count < 1,
    },
  },
});
installJobWatcher(queryClient);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
