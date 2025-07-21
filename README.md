## API Schema
### GET /api/movies/search?title=inception
{
  "movies": [
    {
      "id": "uuid-here",
      "title": "Inception",
      "genre": "Sci-Fi",
      "rating": 8.8,
      "year": 2010,
      "created_at": "2025-01-20T10:00:00Z"
    }
  ]
}

### GET /api/dashboard
{
  "totalMovies": 32,
  "averageRating": 7.5,
  "topGenres": [
    {"genre": "Action", "count": 8},
    {"genre": "Drama", "count": 6},
    {"genre": "Sci-Fi", "count": 5}
  ],
  "moviesByYear": [
    {"year": 2020, "count": 5},
    {"year": 2021, "count": 8}
  ],
}

### GET /api/movies/top-rated?start=0&limit=10
This returns the top 10 rated moves in the database. /api/movies/top-rated?start=10&limit=10 would return the next 10 highest rated.

### POST /api/movies
Content-Type: application/json

{
  "title": "Midnight Bloom",
  "rating": 6.9,
  "genre": "Romance",
  "year": 2018
}

RESPONSE
{
  "id": "new-uuid",
  "title": "Midnight Bloom",
  "rating": 6.9,
  "genre": "Romance", 
  "year": 2018,
  "created_at": "2025-01-20T18:30:00Z"
}

### GET /api/movies/filter?genre=action&genre=drama&minRating=7&year=2020
{
  "movies": [...],
  "totalCount": 5,
  "filters": {
    "genres": ["action", "drama"],
    "minRating": 7,
    "year": 2020
  }
}


## Postgres table schema

The PostgreSQL database contains a single `movies` table with the following schema:

```sql
CREATE TABLE movies (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core movie attributes
    title VARCHAR(255) NOT NULL,
    genre VARCHAR(100) NOT NULL,
    rating DECIMAL(3,1) CHECK (rating >= 0 AND rating <= 10),
    year INTEGER CHECK (year >= 1900 AND year <= 2100),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes

The following indexes are automatically created for performance:

- `movies_pkey`: Primary key index on `id` (UUID)
- `idx_movies_title`: B-tree index on `title` for fast title searches
- `idx_movies_genre`: B-tree index on `genre` for genre filtering
- `idx_movies_year`: B-tree index on `year` for year-based queries
- `idx_movies_rating`: B-tree index on `rating` for rating-based filtering

### Schema Details

- **id**: UUID primary key with automatic generation via `gen_random_uuid()`
- **title**: Movie title (required, up to 255 characters)
- **genre**: Movie genre (required, up to 100 characters) 
- **rating**: Movie rating (optional, decimal 0.0-10.0)
- **year**: Release year (optional, 1900-2100 range)
- **created_at**: Automatic timestamp when record is created
- **updated_at**: Automatic timestamp when record is modified

### Database Initialization

The database schema is automatically created by an AWS Custom Resource Lambda function that runs during CDK deployment. This ensures the table and indexes are always properly initialized when the infrastructure is deployed.

## Tradoffs considered during system design
* each of the 5 query types supported in the web UI 
* If a job is, for some reason, terminated while the async worker has not yet finished its task, the PostgresDB will be half-updated. We consider this acceptable for the time being, and if we got feedback that this constraint is an issue, we could create a task progress queue to ensure that we know where to start up again if the task is brought back online and it sees the previous job was not completed (because there are items in the queue).
* Since I don't have control of the Netflix_Movie_Collection Google Drive folder, and it has only been shared with holtkam2@gmail.com, I have no way to make a service email account so that my ECS task can be granted direct access to GCP and retrieve a token.json. Therefore, we'll have to settle for a script I can run locally on my mac which lets me sign in, then gets a fresh token and pushes it to AWS Secrets Manager for my ECS task to make requets to the Google Drive API.

### Additional todo items
* SQS to handle inbound POST requests insteaad of directly invoking the update lambda
* Cloudwatch dashboard, alarms, etc
* Elasticache Redis in front of the postgres DB

### Manual actions required post deployment
* security group needs to be modified for the ECS task 
* security group needs to be modified for the GET handler lambda 
  * `aws ec2 authorize-security-group-ingress --group-id sg-abc123 --protocol tcp --port 5432 --source-group sg-xyz789`