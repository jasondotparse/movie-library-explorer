import { useMemo } from 'react';
import { useAuth } from 'react-oidc-context';
import { createApiClient } from '../services/apiClient';

export const useApiClient = () => {
  const auth = useAuth();

  const apiClient = useMemo(() => {
    return createApiClient(async () => {
      if (auth.user?.id_token) {
        return auth.user.id_token;
      }
      return null;
    });
  }, [auth.user?.id_token]);

  return apiClient;
};
