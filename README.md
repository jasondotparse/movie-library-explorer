# Movie Library Explorer
## Overview 
Movie Library Explorer is a full stack web application and production-ready API ready for deployment on AWS. This repo contains the entirety of the service, including:
* AWS infrastructure-as-code, defined as CDK stacks in /lib
* Front end React.js UI source code, defined in /frontend
* API layer / service logic, which are deployed as a set of serverless (AWS Lambda) functions defined in /lambda
* ETL service, implemented as a AWS ECS task, easily launched via helper_scripts/run_etl_task.sh
* GCP token creation & upload convenience script (required for the ETL service to interface with GCP APIs), implemented in helper_scripts/update_gcp_token.py

## Architecture

## Deployment and maintenance
### Database Initialization
The database schema is automatically created by an AWS Custom Resource Lambda function that runs during CDK deployment (of the MovieExplorerDatabase Stack). This ensures the table and indexes are always properly initialized when the infrastructure is deployed.

### Manual actions required post cdk stack deployment

**IMPORTANT**: If you need to completely redeploy from scratch (e.g., for duplicate prevention database schema changes), follow these steps in order:

#### 1. Database Security Group Configuration
After deploying the database stack, you must configure the security groups to allow connections from both Lambda functions and ECS tasks:

```bash
# Get the database security group ID
DB_SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=MovieExplorerDatabase-*" \
  --region us-west-1 \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

# Get the Lambda security group ID  
LAMBDA_SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=MovieExplorerApi-ApiLambdaSecurityGroup*" \
  --region us-west-1 \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

# Get the ECS task security group ID
ECS_SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=MovieExplorerEtl-EtlTaskSecurityGroup*" \
  --region us-west-1 \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

# Allow Lambda functions to connect to database
aws ec2 authorize-security-group-ingress \
  --group-id $DB_SG_ID \
  --protocol tcp \
  --port 5432 \
  --source-group $LAMBDA_SG_ID \
  --region us-west-1

# Allow ECS tasks to connect to database  
aws ec2 authorize-security-group-ingress \
  --group-id $DB_SG_ID \
  --protocol tcp \
  --port 5432 \
  --source-group $ECS_SG_ID \
  --region us-west-1
```

#### 2. Authentication Configuration Updates
When deploying new infrastructure, the CloudFront distribution URL changes. Update the authentication stack:

```bash
# Get the new CloudFront distribution URL from the frontend stack output
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
  --stack-name MovieExplorerFrontend \
  --region us-west-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`DistributionUrl`].OutputValue' \
  --output text)

echo "New CloudFront URL: $CLOUDFRONT_URL"
```

Update `lib/auth-stack.ts` with the new CloudFront URL in the `callbackUrls` and `logoutUrls` arrays, then redeploy:

```bash
cdk deploy MovieExplorerAuth
```

#### 3. Frontend Configuration Updates
When API Gateway is recreated, update both frontend configuration files:

```bash
# Get the new API endpoint from the API stack output
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name MovieExplorerApi \
  --region us-west-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

echo "New API Endpoint: $API_ENDPOINT"
```

Update these files with the new API endpoint:
- `frontend/src/config/environment.ts` - Update `apiEndpoint` field
- `frontend/src/config/aws-config.ts` - Update `API.endpoint` field

#### 4. Frontend Rebuild and Redeploy
After updating configuration files, rebuild and redeploy the frontend:

```bash
# Rebuild the frontend with updated configuration
cd frontend && npm run build && cd ..

# Redeploy the frontend stack to upload new build assets
cdk deploy MovieExplorerFrontend
```

#### 5. CORS Configuration (CDK Managed)
CORS is now properly configured in the CDK code (`lib/api-stack.ts`) with:
```typescript
defaultCorsPreflightOptions: {
  allowOrigins: apigateway.Cors.ALL_ORIGINS,
  allowMethods: apigateway.Cors.ALL_METHODS,
  allowHeaders: ['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key', 'X-Amz-Security-Token'],
}
```

No manual CORS configuration should be needed if deploying via CDK.

#### 6. Optional: CloudFront Cache Invalidation
If frontend changes aren't reflecting immediately, invalidate the CloudFront cache:

```bash
# Get the CloudFront distribution ID
DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --stack-name MovieExplorerFrontend \
  --region us-west-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue' \
  --output text)

# Invalidate all cached files
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*" \
  --region us-west-1
```

#### Current Production URLs (as of Session 10)
- **Frontend**: https://d2hpvy9mz6bh86.cloudfront.net
- **API**: https://b97dryed5d.execute-api.us-west-1.amazonaws.com/v1/
- **CloudFront Distribution ID**: E37IS4CV2O6Y6J
- **Cognito Domain**: https://movie-explorer-756021455455.auth.us-west-1.amazoncognito.com

### triggering an ETL job
* Currently, this can only be done locally because I have to sign into google (using my personal email that has been granted to the google drive folder) in order to get a token
* helper_scripts/update_gcp_token.py puts a fresh GCP token in AWS Secrets manager, such that it can be used by the ETL task when it is run
* helper_scripts/run_etl_task.sh automates the process kicking off a task on ECS. This task traverses the Google Drive folder and uploads movies to the database. 

## Scalability 

## Observability & Auditability 

## API Documentation
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Duplicate prevention constraint
    UNIQUE (title, genre, rating, year)
);
```

### Indexes

The following indexes are automatically created for performance:

- `movies_pkey`: Primary key index on `id` (UUID)
- `idx_movies_title`: B-tree index on `title` for fast title searches
- `idx_movies_genre`: B-tree index on `genre` for genre filtering
- `idx_movies_year`: B-tree index on `year` for year-based queries
- `idx_movies_rating`: B-tree index on `rating` for rating-based filtering
- `movies_title_genre_rating_year_key`: Unique constraint index on `(title, genre, rating, year)` for duplicate prevention

### Duplicate Prevention

The database implements duplicate prevention through a unique constraint on the combination of `(title, genre, rating, year)`. This prevents the same movie with identical attributes from being inserted multiple times.

**ETL Behavior**: The ETL worker uses `INSERT ... ON CONFLICT DO NOTHING` to gracefully handle duplicates:
- First ETL run: Inserts new movies normally  
- Subsequent ETL runs: Skips movies that already exist (based on the unique constraint)
- No errors are thrown for duplicates - they are silently ignored

**API Behavior**: When adding movies via the API, duplicate entries will be rejected and return an appropriate error response.

### Schema Details

- **id**: UUID primary key with automatic generation via `gen_random_uuid()`
- **title**: Movie title (required, up to 255 characters)
- **genre**: Movie genre (required, up to 100 characters) 
- **rating**: Movie rating (optional, decimal 0.0-10.0)
- **year**: Release year (optional, 1900-2100 range)
- **created_at**: Automatic timestamp when record is created
- **updated_at**: Automatic timestamp when record is modified
- **Unique constraint**: Combination of (title, genre, rating, year) must be unique across all records

## Tradoffs considered during system design
* each of the 5 query types supported in the web UI 
* If a job is, for some reason, terminated while the async worker has not yet finished its task, the PostgresDB will be half-updated. We consider this acceptable for the time being, and if we got feedback that this constraint is an issue, we could create a task progress queue to ensure that we know where to start up again if the task is brought back online and it sees the previous job was not completed (because there are items in the queue).
* Since I don't have control of the Netflix_Movie_Collection Google Drive folder, and it has only been shared with holtkam2@gmail.com, I have no way to make a service email account so that my ECS task can be granted direct access to GCP and retrieve a token.json. Therefore, we'll have to settle for a script I can run locally on my mac which lets me sign in, then gets a fresh token and pushes it to AWS Secrets Manager for my ECS task to make requets to the Google Drive API.
* due to the fact that API Gateway pushes update requests to an SQS queue, our lambda cannot directly communicate with the front end in the event of an error to add a movie. For this, we'd need a DLQ. I think this is acceptable given the interface for movies is simple and write requests will fail rarely.
  * mitigation: if users complained about this, we could implement a websocket API gateway endpoint. It would pass the request to SQS and Lambda, including the websocket URL. Then, once the lambda has updated the db (or failed to do so) it could send its status to the websocket URL, which APIG would deliver to the front end. But, for the scope of v1 of this project, that sounds like over-engineering.

### Improvements
* ETL worker could be made more efficient by doing batch updates, and it could be given the ability to start/stop in-progress jobs by traversing the folder breadth-first and putting its todo items in a SQS queue which it pulls/pushes to.
* Cloudwatch dashboard, alarms, etc
* Elasticache Redis in front of the postgres DB
