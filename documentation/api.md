# Movie Library Explorer API Documentation

## Base URL
```
https://b97dryed5d.execute-api.us-west-1.amazonaws.com/v1
```

## Authentication

All API endpoints require authentication using Amazon Cognito User Pool JWT tokens. Include the token in the Authorization header:

```
Authorization: Bearer <jwt_token>
```

### Getting an Access Token

1. **Web Application Flow**: Use the Cognito hosted UI for OAuth2/OIDC authentication
2. **Direct API Integration**: Implement Cognito authentication in your application using AWS SDK or Cognito libraries
3. **Cognito Domain**: `https://movie-explorer-756021455455.auth.us-west-1.amazoncognito.com`

The JWT token must be a valid `id_token` from the Cognito User Pool (not an access token).

---

## Endpoints

### GET /api/dashboard

Returns aggregate statistics about the movie library.

**Authentication**: Required

**Query Parameters**: None

**Response**:
```json
{
  "totalMovies": 33,
  "averageRating": 7.4,
  "topGenres": [
    {"genre": "Action", "count": 8},
    {"genre": "Drama", "count": 6},
    {"genre": "Sci-Fi", "count": 5}
  ],
  "moviesByYear": [
    {"year": 2020, "count": 5},
    {"year": 2021, "count": 8},
    {"year": 2022, "count": 4}
  ]
}
```

**Response Fields**:
- `totalMovies` (number): Total number of movies in the database
- `averageRating` (number): Average rating across all movies
- `topGenres` (array): Top 10 genres by movie count
- `moviesByYear` (array): Movie count grouped by release year

**Caching**: This endpoint is cached for 30 seconds for improved performance.

---

### GET /api/movies/search

Search for movies by title using partial matching.

**Authentication**: Required

**Query Parameters**:
- `title` (required, string): Search term to match against movie titles

**Example**:
```
GET /api/movies/search?title=inception
```

**Response**:
```json
{
  "movies": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Inception",
      "genre": "Sci-Fi",
      "rating": 8.8,
      "year": 2010,
      "created_at": "2025-01-20T10:00:00Z"
    }
  ]
}
```

**Response Fields**:
- `movies` (array): Array of movie objects matching the search criteria
- `id` (string): UUID of the movie
- `title` (string): Movie title
- `genre` (string): Movie genre
- `rating` (number): Movie rating (0.0-10.0)
- `year` (number): Release year
- `created_at` (string): ISO 8601 timestamp when the movie was added

---

### GET /api/movies/filter

Filter movies by genre, minimum rating, and/or release year.

**Authentication**: Required

**Query Parameters**:
- `genre` (optional, string): Filter by genre (can be specified multiple times for multiple genres)
- `minRating` (optional, number): Minimum rating threshold (0.0-10.0)
- `year` (optional, number): Filter by release year

**Example**:
```
GET /api/movies/filter?genre=action&genre=drama&minRating=7&year=2020
```

**Response**:
```json
{
  "movies": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Tenet",
      "genre": "Action",
      "rating": 7.4,
      "year": 2020,
      "created_at": "2025-01-20T10:00:00Z"
    }
  ],
  "totalCount": 5,
  "filters": {
    "genres": ["action", "drama"],
    "minRating": 7,
    "year": 2020
  }
}
```

**Response Fields**:
- `movies` (array): Array of movie objects matching the filter criteria
- `totalCount` (number): Total number of movies matching the filters
- `filters` (object): Echo of the applied filters for confirmation

---

### GET /api/movies/top-rated

Returns the highest-rated movies with pagination support.

**Authentication**: Required

**Query Parameters**:
- `start` (optional, number): Starting index for pagination (default: 0)
- `limit` (optional, number): Maximum number of movies to return (default: 10, max: 100)

**Example**:
```
GET /api/movies/top-rated?start=0&limit=10
GET /api/movies/top-rated?start=10&limit=10
```

**Response**:
```json
{
  "movies": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "The Shawshank Redemption",
      "genre": "Drama",
      "rating": 9.3,
      "year": 1994,
      "created_at": "2025-01-20T10:00:00Z"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "title": "The Godfather",
      "genre": "Crime",
      "rating": 9.2,
      "year": 1972,
      "created_at": "2025-01-20T10:00:00Z"
    }
  ],
  "pagination": {
    "start": 0,
    "limit": 10,
    "hasMore": true
  }
}
```

**Response Fields**:
- `movies` (array): Array of movie objects sorted by rating (highest first)
- `pagination` (object): Pagination information
  - `start` (number): Starting index used for this request
  - `limit` (number): Limit used for this request
  - `hasMore` (boolean): Whether more movies are available

---

### POST /api/movies

Add a new movie to the library.

**Authentication**: Required

**Content-Type**: `application/json`

**Request Body**:
```json
{
  "title": "Midnight Bloom",
  "genre": "Romance",
  "rating": 6.9,
  "year": 2018
}
```

**Request Fields**:
- `title` (required, string): Movie title (1-255 characters)
- `genre` (required, string): Movie genre (1-100 characters)
- `rating` (required, number): Movie rating (0.0-10.0)
- `year` (required, number): Release year (1900-2100)

**Response** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Movie creation request received"
}
```

**Response Fields**:
- `id` (string): Request ID for tracking the movie creation (currently unused)
- `message` (string): Confirmation message

**Important Notes**:
- Movie creation is asynchronous - the movie is queued for processing
- The response indicates the request was received, not that the movie was immediately created
- Duplicate movies (same title, genre, rating, and year) will result in a no-op
- Processing typically completes within seconds

---

## Error Responses

All endpoints return consistent error responses:

**400 Bad Request**:
```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "Invalid request parameters"
  }
}
```

**401 Unauthorized**:
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or missing authentication token"
  }
}
```

**500 Internal Server Error**:
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An internal server error occurred"
  }
}
```

---

## Rate Limiting

The API implements rate limiting of 1000 requests per minute per authenticated user. If you exceed this limit, you will receive a 429 Too Many Requests response.

## CORS

Cross-Origin Resource Sharing (CORS) is enabled for all origins. Include the Authorization header in your requests for authentication.

## Caching

- `/api/dashboard`: Cached for 30 seconds
- `/api/movies/search`: Not cached (always returns fresh results)
- `/api/movies/filter`: Not cached (always returns fresh results)
- `/api/movies/top-rated`: Not cached (always returns fresh results)

## Example Integration

For an example, refer to movie-library-explorer/example_2p_client/2p_client.py. Note that this example does not include authorization logic - it relies upon a token being provided prior to script invocation.
