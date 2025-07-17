#!/usr/bin/env python3
"""
Environment Variable Checker for Travel Agent App
This script checks if all required environment variables are properly configured.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def check_env_vars():
    """Check all required environment variables"""
    print("🔍 Checking Environment Variables...")
    print("=" * 50)
    
    # Required variables
    required_vars = {
        "SUPABASE_URL": "Supabase project URL",
        "SUPABASE_KEY": "Supabase anon key",
        "OPENAI_API_KEY": "OpenAI API key",
        "AMADEUS_CLIENT_ID": "Amadeus API client ID",
        "AMADEUS_CLIENT_SECRET": "Amadeus API client secret",
        "HUGGINGFACE_TOKEN": "Hugging Face API token"
    }
    
    all_good = True
    
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if not value or value.startswith("your_") or value == "":
            print(f"❌ {var_name}: {description} - NOT SET or using placeholder")
            all_good = False
        else:
            # Show first few characters for security
            masked_value = value[:8] + "..." if len(value) > 8 else value
            print(f"✅ {var_name}: {description} - {masked_value}")
    
    print("\n" + "=" * 50)
    
    if all_good:
        print("🎉 All environment variables are properly configured!")
        print("Your app should work correctly.")
    else:
        print("⚠️  Some environment variables are missing or using placeholders.")
        print("\nTo fix this:")
        print("1. Create a .env file in the backend directory")
        print("2. Add your actual API keys and tokens")
        print("3. Make sure to set these in your Render environment variables too")
        print("\nExample .env file:")
        print("SUPABASE_URL=https://your-project.supabase.co")
        print("SUPABASE_KEY=your_supabase_anon_key")
        print("OPENAI_API_KEY=sk-your_openai_key")
        print("AMADEUS_CLIENT_ID=your_amadeus_client_id")
        print("AMADEUS_CLIENT_SECRET=your_amadeus_client_secret")
        print("HUGGINGFACE_TOKEN=your_huggingface_token")
    
    return all_good

if __name__ == "__main__":
    check_env_vars() 