import React, { useEffect, useState } from 'react';
import { movieService } from '../services/movie.service';
import { useApiClient } from '../hooks/useApiClient';

interface DashboardData {
  totalMovies: number;
  averageRating: number;
  topGenres: Array<{ genre: string; count: number }>;
  moviesByYear: Array<{ year: number; count: number }>;
}

const Dashboard: React.FC = () => {
  const apiClient = useApiClient();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const dashboardData = await movieService.getDashboard(apiClient);
        setData(dashboardData);
      } catch (err) {
        setError('Failed to load dashboard data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
  }, [apiClient]);

  if (loading) return <div>Loading dashboard...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!data) return <div>No data available</div>;

  return (
    <div className="dashboard">
      <h2>Movie Library Dashboard</h2>
      
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Movies</h3>
          <p>{data.totalMovies}</p>
        </div>
        
        <div className="stat-card">
          <h3>Average Rating</h3>
          <p>{data.averageRating.toFixed(1)}/10</p>
        </div>
      </div>

      <div className="genres-section">
        <h3>Top Genres</h3>
        <ul>
          {data.topGenres.map((genre) => (
            <li key={genre.genre}>
              {genre.genre}: {genre.count} movies
            </li>
          ))}
        </ul>
      </div>

      <div className="years-section">
        <h3>Movies by Year</h3>
        <ul>
          {data.moviesByYear.map((year) => (
            <li key={year.year}>
              {year.year}: {year.count} movies
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default Dashboard;
