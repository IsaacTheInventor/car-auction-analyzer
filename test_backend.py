#!/usr/bin/env python3
"""
Backend API Test Script for Car Auction Analyzer

This script tests the backend API by sending a sample image for analysis
and printing the response. It helps diagnose issues with the backend deployment.
"""

import requests
import json
import sys
import base64
from pprint import pprint

# Test URLs - we'll try both in case one is working
BACKEND_URLS = [
    "https://car-auction-analyzer-i2gb7yqxn-isaactheinventors-projects.vercel.app",
    "https://car-auction-analyzer-2kni3tpgt-isaactheinventors-projects.vercel.app",
    "https://car-auction-analyzer-api.vercel.app"  # Try the main domain too
]

# Endpoint to test
ENDPOINT = "/api/vehicles/analyze"

# A tiny 1x1 pixel transparent PNG image in base64 format
SAMPLE_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

def test_backend(url):
    """Test the backend API with a simple request"""
    full_url = f"{url}{ENDPOINT}"
    print(f"\nTesting backend at: {full_url}")
    
    # Prepare the payload
    payload = {
        "photos": [
            {
                "image_data": SAMPLE_IMAGE,
                "category": "Test Photo"
            }
        ]
    }
    
    # Set headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        # Make the request with a timeout
        response = requests.post(
            full_url, 
            json=payload,
            headers=headers,
            timeout=10
        )
        
        # Print status code
        print(f"Status Code: {response.status_code}")
        
        # Try to parse and print JSON response
        try:
            result = response.json()
            print("\nResponse JSON:")
            pprint(result)
        except json.JSONDecodeError:
            print("\nResponse is not valid JSON. Raw response:")
            print(response.text[:500] + "..." if len(response.text) > 500 else response.text)
            
        return response.status_code >= 200 and response.status_code < 300
            
    except requests.exceptions.Timeout:
        print("Request timed out after 10 seconds")
    except requests.exceptions.ConnectionError:
        print("Connection error - could not connect to server")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    
    return False

def main():
    """Main function to test all backend URLs"""
    print("Car Auction Analyzer Backend API Test")
    print("=====================================")
    
    success = False
    
    # Try each URL until one works
    for url in BACKEND_URLS:
        if test_backend(url):
            print(f"\n✅ SUCCESS: Backend at {url} is working!")
            success = True
            break
    
    if not success:
        print("\n❌ ERROR: Could not connect to any backend URL")
        print("\nPossible issues:")
        print("1. Backend is not deployed or has been taken down")
        print("2. Backend URLs have changed")
        print("3. Backend requires authentication")
        print("4. Network connectivity issues")
        print("\nTry deploying a new backend instance with:")
        print("vercel --prod")
        
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
