import React, { useState } from 'react';
import { movieService } from '../services/movie.service';
import { useApiClient } from '../hooks/useApiClient';
import { Movie } from '../types/movie.types';
import MovieCard from './MovieCard';

const MovieSearch: React.FC = () => {
  const apiClient = useApiClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    setLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const result = await movieService.searchMovies(apiClient, searchTerm);
      setMovies(result.movies);
    } catch (err) {
      setError('Failed to search movies');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="movie-search">
      <h2>Search Movies</h2>
      
      <form onSubmit={handleSearch}>
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Enter movie title..."
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {hasSearched && !loading && movies.length === 0 && (
        <div>No movies found matching "{searchTerm}"</div>
      )}

      <div className="movies-grid">
        {movies.map((movie) => (
          <MovieCard key={movie.id} movie={movie} />
        ))}
      </div>
    </div>
  );
};

export default MovieSearch;
