import React, { useState, useEffect } from 'react';
import { movieService } from '../services/movie.service';
import { useApiClient } from '../hooks/useApiClient';
import { Movie } from '../types/movie.types';
import MovieCard from './MovieCard';

const TopRatedMovies: React.FC = () => {
  const apiClient = useApiClient();
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [start, setStart] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const limit = 10;

  const loadMovies = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await movieService.getTopRatedMovies(apiClient, start, limit);
      setMovies([...movies, ...result.movies]);
      setHasMore(result.pagination.hasMore);
      setStart(start + limit);
    } catch (err) {
      setError('Failed to load top-rated movies');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMovies();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="top-rated-movies">
      <h2>Top Rated Movies</h2>

      {error && <div className="error">{error}</div>}

      <div className="movies-grid">
        {movies.map((movie) => (
          <MovieCard key={movie.id} movie={movie} />
        ))}
      </div>

      {hasMore && (
        <button 
          onClick={loadMovies} 
          disabled={loading}
          className="load-more-button"
        >
          {loading ? 'Loading...' : 'Load More'}
        </button>
      )}
    </div>
  );
};

export default TopRatedMovies;
