import axios, { AxiosInstance } from 'axios';
import config from '../config/aws-config';

export const createApiClient = (getAccessToken?: () => Promise<string | null>): AxiosInstance => {
  const client = axios.create({
    baseURL: config.API.endpoint,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Add auth token to requests
  client.interceptors.request.use(
    async (config) => {
      if (getAccessToken) {
        const token = await getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  return client;
};

// Note: The singleton instance will be created in components with auth context
