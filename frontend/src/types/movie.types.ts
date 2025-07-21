export interface Movie {
  id: string;
  title: string;
  genre: string;
  rating: number;
  year: number;
  created_at: string;
  updated_at?: string;
}

export interface MovieFilters {
  genre?: string;
  minRating?: number;
  year?: number;
}

export interface PaginatedMoviesResponse {
  movies: Movie[];
  pagination: {
    start: number;
    limit: number;
    total: number;
    hasMore: boolean;
  };
}

export interface FilteredMoviesResponse {
  movies: Movie[];
  totalCount: number;
  filters: {
    genres?: string[];
    minRating?: number;
    year?: number;
  };
}

export interface SearchMoviesResponse {
  movies: Movie[];
}

export interface CreateMovieRequest {
  title: string;
  genre: string;
  rating: number;
  year: number;
}
