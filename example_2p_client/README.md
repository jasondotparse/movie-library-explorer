# Movie Library Explorer API Client

A simple Python client demonstrating how to make authenticated requests to the Movie Library Explorer API filter endpoint.

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Add your authentication token to `token.txt`. This can be taken from the web UI or via STS/IAM authorization.

3. Run the script:
   ```bash
   # Get all movies
   python 2p_client.py
   
   # Filter examples
   python 2p_client.py --genre Action --minRating 8.0
   python 2p_client.py --year 2021
   ```

## API Details

- **Endpoint**: `/api/movies/filter`
- **Method**: GET
- **Authentication**: Bearer token in Authorization header
- **Parameters**: `genre`, `minRating`, `year`

This demonstrates the basic pattern for integrating with the Movie Library Explorer API.
