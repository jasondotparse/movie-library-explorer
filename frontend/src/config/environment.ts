// Environment configuration
const getRedirectUri = () => {
  // In production, use the current origin
  if (process.env.NODE_ENV === 'production') {
    return window.location.origin;
  }
  // In development, use localhost
  return 'http://localhost:3000';
};

export const environment = {
  production: process.env.NODE_ENV === 'production',
  redirectUri: getRedirectUri(),
  cognitoDomain: 'https://movie-explorer-756021455455.auth.us-west-1.amazoncognito.com',
  authority: 'https://cognito-idp.us-west-1.amazonaws.com/us-west-1_610LASnzS',
  clientId: '2bpg1k5fna74ijrqi7jgnddhsr',
  apiEndpoint: 'https://b97dryed5d.execute-api.us-west-1.amazonaws.com/v1'
};
