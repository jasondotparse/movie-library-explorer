import { useMemo } from 'react';
import { useAuth } from 'react-oidc-context';
import { createApiClient } from '../services/apiClient';

export const useApiClient = () => {
  const auth = useAuth();

  const apiClient = useMemo(() => {
    return createApiClient(async () => {
      if (auth.user?.access_token) {
        return auth.user.access_token;
      }
      return null;
    });
  }, [auth.user?.access_token]);

  return apiClient;
};
