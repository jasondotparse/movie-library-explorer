import React from 'react';
import { Movie } from '../types/movie.types';

interface MovieCardProps {
  movie: Movie;
}

const MovieCard: React.FC<MovieCardProps> = ({ movie }) => {
  return (
    <div className="movie-card">
      <h3 className="movie-title">{movie.title}</h3>
      <div className="movie-details">
        <span className="movie-genre">{movie.genre}</span>
        <span className="movie-year">{movie.year}</span>
      </div>
      <div className="movie-rating">
        <span className="rating-value">{movie.rating}</span>
        <span className="rating-max">/10</span>
      </div>
    </div>
  );
};

export default MovieCard;
