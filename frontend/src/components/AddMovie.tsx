import React, { useState } from 'react';
import { movieService } from '../services/movie.service';
import { useApiClient } from '../hooks/useApiClient';
import { CreateMovieRequest } from '../types/movie.types';

const AddMovie: React.FC = () => {
  const apiClient = useApiClient();
  const [formData, setFormData] = useState<CreateMovieRequest>({
    title: '',
    genre: '',
    rating: 0,
    year: new Date().getFullYear()
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: name === 'rating' || name === 'year' ? Number(value) : value
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      await movieService.createMovie(apiClient, formData);
      setSuccess(true);
      // Reset form
      setFormData({
        title: '',
        genre: '',
        rating: 0,
        year: new Date().getFullYear()
      });
    } catch (err) {
      setError('Failed to add movie');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="add-movie">
      <h2>Add New Movie</h2>

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="title">Title:</label>
          <input
            type="text"
            id="title"
            name="title"
            value={formData.title}
            onChange={handleChange}
            required
            disabled={loading}
          />
        </div>

        <div>
          <label htmlFor="genre">Genre:</label>
          <input
            type="text"
            id="genre"
            name="genre"
            value={formData.genre}
            onChange={handleChange}
            required
            disabled={loading}
          />
        </div>

        <div>
          <label htmlFor="rating">Rating:</label>
          <input
            type="number"
            id="rating"
            name="rating"
            value={formData.rating}
            onChange={handleChange}
            min="0"
            max="10"
            step="0.1"
            required
            disabled={loading}
          />
        </div>

        <div>
          <label htmlFor="year">Year:</label>
          <input
            type="number"
            id="year"
            name="year"
            value={formData.year}
            onChange={handleChange}
            min="1900"
            max={new Date().getFullYear() + 5}
            required
            disabled={loading}
          />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? 'Adding...' : 'Add Movie'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}
      {success && <div className="success">Request received! The database may take a few minutes to update depending on current traffic.</div>}
    </div>
  );
};

export default AddMovie;
