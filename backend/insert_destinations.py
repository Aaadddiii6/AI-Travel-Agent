#!/usr/bin/env python3
"""
Fully GPT-powered destination generator and Supabase uploader
"""

import os
import uuid
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI
import json

# Load env vars
load_dotenv()

# Setup clients
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 1️⃣ GPT prompt to create destinations
def generate_destinations_via_gpt(num=5):
    prompt = f"""
Create {num} unique travel destinations around the world.
For each, return:
- name
- country
- city
- continent
- description (1-2 catchy sentences)
- highlights (list of 3-5)
- Unsplash-style image_url (fake if needed)

Return ONLY valid JSON list.
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful travel data API that returns strict JSON."},
            {"role": "user", "content": prompt}
        ]
    )
    # Extract and parse JSON safely
    text = response.choices[0].message.content.strip()
    try:
        data = json.loads(text)
    except Exception as e:
        print("❌ Failed to parse GPT response as JSON!")
        print("Raw GPT output:\n", text)
        raise e
    return data

# 2️⃣ Insert into Supabase
def insert_destinations(destinations):
    for dest in destinations:
        dest["id"] = str(uuid.uuid4())
        try:
            result = supabase.table("destinations").insert(dest).execute()
            print(f"✅ Inserted: {dest['name']}")
        except Exception as e:
            print(f"❌ Failed to insert {dest['name']}: {e}")

    print(f"\nDone! Inserted {len(destinations)} destinations.\n")

if __name__ == "__main__":
    generated = generate_destinations_via_gpt(num=5)
    print(json.dumps(generated, indent=2))  # See what GPT made
    insert_destinations(generated)
