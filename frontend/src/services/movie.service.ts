import { AxiosInstance } from 'axios';
import { CreateMovieRequest, SearchMoviesResponse, FilteredMoviesResponse, PaginatedMoviesResponse } from '../types/movie.types';

export const movieService = {
  // Get dashboard statistics
  getDashboard: async (apiClient: AxiosInstance) => {
    const response = await apiClient.get('/api/dashboard');
    return response.data;
  },

  // Search movies by title
  searchMovies: async (apiClient: AxiosInstance, title: string): Promise<SearchMoviesResponse> => {
    const response = await apiClient.get('/api/movies/search', {
      params: { title }
    });
    return response.data;
  },

  // Get filtered movies
  getFilteredMovies: async (
    apiClient: AxiosInstance,
    filters: {
      genre?: string;
      minRating?: number;
      year?: number;
    }
  ): Promise<FilteredMoviesResponse> => {
    const response = await apiClient.get('/api/movies/filter', {
      params: filters
    });
    return response.data;
  },

  // Get top-rated movies with pagination
  getTopRatedMovies: async (
    apiClient: AxiosInstance,
    start: number = 0,
    limit: number = 10
  ): Promise<PaginatedMoviesResponse> => {
    const response = await apiClient.get('/api/movies/top-rated', {
      params: { start, limit }
    });
    return response.data;
  },

  // Create a new movie
  createMovie: async (apiClient: AxiosInstance, movie: CreateMovieRequest): Promise<{ message: string }> => {
    const response = await apiClient.post('/api/movies', movie);
    return response.data;
  }
};
