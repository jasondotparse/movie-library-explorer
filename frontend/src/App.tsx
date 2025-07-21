import React, { useState } from 'react';
import { useAuth } from 'react-oidc-context';
import Dashboard from './components/Dashboard';
import MovieSearch from './components/MovieSearch';
import TopRatedMovies from './components/TopRatedMovies';
import AddMovie from './components/AddMovie';
import './App.css';

type View = 'dashboard' | 'search' | 'topRated' | 'add';

function App() {
  const auth = useAuth();
  const [currentView, setCurrentView] = useState<View>('dashboard');

  const signOutRedirect = () => {
    const clientId = "2bpg1k5fna74ijrqi7jgnddhsr";
    const logoutUri = "http://localhost:3000";
    const cognitoDomain = "https://your-user-pool-domain.auth.us-west-1.amazoncognito.com"; // TODO: Update with actual domain
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
    return <div>Loading...</div>;
  }

  if (auth.error) {
    return <div>Authentication error: {auth.error.message}</div>;
  }

  if (!auth.isAuthenticated) {
    return (
      <div className="App">
        <header className="App-header">
          <h1>Movie Library Explorer</h1>
        </header>
        <main className="App-main">
          <div style={{ textAlign: 'center', marginTop: '50px' }}>
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
