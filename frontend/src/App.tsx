import React, { useState } from 'react';
import { useAuth } from 'react-oidc-context';
import Dashboard from './components/Dashboard';
import MovieSearch from './components/MovieSearch';
import TopRatedMovies from './components/TopRatedMovies';
import AddMovie from './components/AddMovie';
import { environment } from './config/environment';
import './App.css';

type View = 'dashboard' | 'search' | 'topRated' | 'add';

function App() {
  const auth = useAuth();
  const [currentView, setCurrentView] = useState<View>('dashboard');

  const signOutRedirect = () => {
    const clientId = environment.clientId;
    const logoutUri = environment.redirectUri;
    const cognitoDomain = environment.cognitoDomain;
    window.location.href = `${cognitoDomain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(logoutUri)}`;
  };

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard />;
      case 'search':
        return <MovieSearch />;
      case 'topRated':
        return <TopRatedMovies />;
      case 'add':
        return <AddMovie />;
      default:
        return <Dashboard />;
    }
  };

  if (auth.isLoading) {
    return <div className="loading">Loading...</div>;
  }

  if (auth.error) {
    return <div className="error">Authentication error: {auth.error.message}</div>;
  }

  if (!auth.isAuthenticated) {
    return (
      <div className="App">
        <header className="App-header">
          <h1>Movie Library Explorer</h1>
        </header>
        <main className="App-main">
          <div className="sign-in-container">
            <h2>Please sign in to access the movie library</h2>
            <button onClick={() => auth.signinRedirect()}>Sign in</button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>Movie Library Explorer</h1>
        <nav>
          <button 
            onClick={() => setCurrentView('dashboard')}
            className={currentView === 'dashboard' ? 'active' : ''}
          >
            Dashboard
          </button>
          <button 
            onClick={() => setCurrentView('search')}
            className={currentView === 'search' ? 'active' : ''}
          >
            Search Movies
          </button>
          <button 
            onClick={() => setCurrentView('topRated')}
            className={currentView === 'topRated' ? 'active' : ''}
          >
            Top Rated
          </button>
          <button 
            onClick={() => setCurrentView('add')}
            className={currentView === 'add' ? 'active' : ''}
          >
            Add Movie
          </button>
          <button onClick={() => auth.removeUser()}>Sign out</button>
        </nav>
      </header>
      
      <main className="App-main">
        {renderView()}
      </main>
    </div>
  );
}

export default App;
