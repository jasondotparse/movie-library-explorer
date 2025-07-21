import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import { AuthProvider } from 'react-oidc-context';
import { environment } from './config/environment';

const cognitoAuthConfig = {
  authority: environment.authority,
  client_id: environment.clientId,
  redirect_uri: environment.redirectUri,
  response_type: "code",
  scope: "email openid profile",
};

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

// wrap the application with AuthProvider
root.render(
  <React.StrictMode>
    <AuthProvider {...cognitoAuthConfig}>
      <App />
    </AuthProvider>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
