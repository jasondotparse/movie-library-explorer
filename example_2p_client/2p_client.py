#!/usr/bin/env python3
"""
Simple API client for Movie Library Explorer
Demonstrates how to make authenticated requests to the filter endpoint.
"""

import requests
import json
import argparse
import sys
from pathlib import Path

# API Configuration
API_BASE_URL = "https://orrxyywtrk.execute-api.us-west-1.amazonaws.com/v1"
TOKEN_FILE = "token.txt"

def load_token():
    """Load bearer token from token.txt file"""
    token_path = Path(TOKEN_FILE)
    if not token_path.exists():
        print(f"Error: {TOKEN_FILE} not found!")
        print("Please create token.txt with your bearer token")
        sys.exit(1)
    
    token = token_path.read_text().strip()
    if not token:
        print(f"Error: {TOKEN_FILE} is empty!")
        sys.exit(1)
    
    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
    
    return token

def make_api_request(genre=None, min_rating=None, year=None):
    """Make request to /api/movies/filter endpoint"""
    token = load_token()
    
    # Build query parameters
    params = {}
    if genre:
        params['genre'] = genre
    if min_rating:
        params['minRating'] = min_rating
    if year:
        params['year'] = year
    
    # Prepare request
    url = f"{API_BASE_URL}/api/movies/filter"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"Making request to: {url}")
        if params:
            print(f"Filters: {params}")
        else:
            print("No filters applied - getting all movies")
        print()
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Display results
        print("API Response:")
        print("=" * 50)
        print(f"Total movies found: {data.get('totalCount', 0)}")
        
        if 'filters' in data and data['filters']:
            print(f"Applied filters: {data['filters']}")
        
        print()
        
        movies = data.get('movies', [])
        if movies:
            print("Movies:")
            print("-" * 50)
            for movie in movies:
                print(f"Title: {movie.get('title', 'Unknown')}")
                print(f"Genre: {movie.get('genre', 'Unknown')}")
                print(f"Rating: {movie.get('rating', 'N/A')}")
                print(f"Year: {movie.get('year', 'Unknown')}")
                print()
        else:
            print("No movies found matching your criteria.")
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Movie Library Explorer API Client')
    parser.add_argument('--genre', help='Filter by genre')
    parser.add_argument('--minRating', type=float, help='Minimum rating (e.g., 7.5)')
    parser.add_argument('--year', type=int, help='Filter by year')
    
    args = parser.parse_args()
    
    make_api_request(
        genre=args.genre,
        min_rating=args.minRating,
        year=args.year
    )

if __name__ == "__main__":
    main()
