#!/usr/bin/env python3
"""
Test script to check Amadeus API connectivity
"""
import os
from dotenv import load_dotenv
from amadeus import Client as AmadeusClient, ResponseError

# Load environment variables
load_dotenv()

def test_amadeus_connection():
    """Test Amadeus API connection and credentials"""
    print("Testing Amadeus API connection...")
    
    # Check if credentials exist
    amadeus_client_id = os.getenv("AMADEUS_CLIENT_ID")
    amadeus_client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    
    if not amadeus_client_id or not amadeus_client_secret:
        print("❌ Amadeus credentials not found in environment variables")
        print(f"AMADEUS_CLIENT_ID: {'Set' if amadeus_client_id else 'Not set'}")
        print(f"AMADEUS_CLIENT_SECRET: {'Set' if amadeus_client_secret else 'Not set'}")
        return False
    
    print("✅ Amadeus credentials found")
    
    try:
        # Initialize Amadeus client
        amadeus = AmadeusClient(
            client_id=amadeus_client_id,
            client_secret=amadeus_client_secret
        )
        print("✅ Amadeus client initialized successfully")
        
        # Test a simple API call
        print("Testing flight offers search...")
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode="JFK",
            destinationLocationCode="LAX",
            departureDate="2025-01-15",
            adults=1,
            travelClass="ECONOMY",
            currencyCode="USD",
            max=5
        )
        
        print(f"✅ Flight search successful! Found {len(response.data)} flights")
        
        # Show first flight details
        if response.data:
            first_flight = response.data[0]
            print(f"Sample flight: {first_flight['id']}")
            print(f"Price: {first_flight['price']['total']} {first_flight['price']['currency']}")
        
        return True
        
    except ResponseError as e:
        print(f"❌ Amadeus API error: {e}")
        print(f"Error code: {e.code if hasattr(e, 'code') else 'No code'}")
        print(f"Error description: {e.description if hasattr(e, 'description') else 'No description'}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_amadeus_connection() 