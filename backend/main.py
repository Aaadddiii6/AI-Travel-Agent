from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, field_validator
from supabase.client import create_client, Client
import os
from dotenv import load_dotenv
import uuid
from PIL import Image
import io
import httpx
import requests
import logging
from typing import Optional, List
from datetime import datetime
import time
from openai import OpenAI
from gradio_client import Client as GradioClient, handle_file
from pathlib import Path
import shutil
from fastapi.staticfiles import StaticFiles
from amadeus import Client as AmadeusClient, ResponseError# Load environment variables
load_dotenv()

# Configure OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console handler
        logging.FileHandler('app.log')  # File handler
    ]
)
logger = logging.getLogger(__name__)

# LightX API Configuration
LIGHTX_API_KEY = os.getenv("LIGHTX_API_KEY")
LIGHTX_BASE_URL = "https://api.lightxeditor.com"

# Demo mode for testing (set to True to bypass LightX API calls)
LIGHTX_DEMO_MODE = True

# Temporary image storage for LightX API
# In production, use a proper image hosting service like AWS S3, Cloudinary, etc.
temp_images = {}

def create_temp_image_url(base64_data: str) -> str:
    """Convert base64 image data to a temporary URL for LightX API"""
    try:
        # Remove data URL prefix if present
        if base64_data.startswith('data:image'):
            base64_data = base64_data.split(',')[1]
        
        # Generate a unique ID for this image
        image_id = str(uuid.uuid4())
        
        # Store the base64 data temporarily
        temp_images[image_id] = base64_data
        
        # Create a temporary URL that points to our server
        # This is a simplified approach - in production, use a proper image hosting service
        temp_url = f"http://localhost:8000/temp-image/{image_id}"
        
        logger.info(f"Created temporary image URL: {temp_url}")
        return temp_url
        
    except Exception as e:
        logger.error(f"Failed to create temporary image URL: {e}")
        # Fallback to a default image
        return "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop"

app = FastAPI(
    title="AI Travel App API",
    description="AI-powered travel visualization API with face swap capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Serve static files (for generated images)
import os
static_dir = "backend/static"
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Enhanced CORS for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "https://your-frontend-domain.onrender.com",  # Replace with your actual frontend domain
        "https://your-app-name.onrender.com"  # Replace with your actual app domain
    ] if os.getenv("RENDER", "false").lower() == "true" else ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Initialize services
supabase: Optional[Client] = None
try:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if supabase_url and supabase_key:
        # Simple initialization without extra options
        supabase = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully")
    else:
        logger.warning("Supabase credentials not found")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {e}")
    supabase = None

# Initialize Amadeus client
amadeus_client = None
try:
    amadeus_client_id = os.getenv("AMADEUS_CLIENT_ID")
    amadeus_client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    
    # Check if credentials are actually set (not just empty strings)
    if amadeus_client_id and amadeus_client_secret and amadeus_client_id != "your_amadeus_client_id_here" and amadeus_client_secret != "your_amadeus_client_secret_here":
        amadeus_client = AmadeusClient(
            client_id=amadeus_client_id,
            client_secret=amadeus_client_secret
        )
        logger.info("Amadeus client initialized successfully")
    else:
        logger.warning("Amadeus credentials not found or not properly configured")
        amadeus_client = None
except Exception as e:
    logger.error(f"Failed to initialize Amadeus client: {e}")
    amadeus_client = None

# Pydantic models for validation
class VisualizationRequest(BaseModel):
    user_photo_url: str
    destination_id: Optional[str] = None  # Now optional
    prompt: Optional[str] = None  # NEW: Allow prompt from frontend

    @field_validator('user_photo_url')
    @classmethod
    def validate_photo_url(cls, v):
        if not v or not v.startswith(('http://', 'https://')):
            raise ValueError('Invalid photo URL')
        return v

class RecommendationsRequest(BaseModel):
    ageGroup: str
    groupSize: str
    budgetRange: int
    tripDuration: str
    interests: List[str]
    country: Optional[str] = None  # <-- Add country field
    additionalNotes: Optional[str] = None

    @field_validator('ageGroup')
    @classmethod
    def validate_age_group(cls, v):
        valid_groups = ['18-25', '26-35', '36-50', '51-65', '65+']
        if v not in valid_groups:
            raise ValueError('Invalid age group')
        return v

    @field_validator('groupSize')
    @classmethod
    def validate_group_size(cls, v):
        valid_sizes = ['solo', 'couple', 'family', 'friends', 'large-group']
        if v not in valid_sizes:
            raise ValueError('Invalid group size')
        return v

    @field_validator('budgetRange')
    @classmethod
    def validate_budget(cls, v):
        if v < 500 or v > 10000:
            raise ValueError('Budget must be between $500 and $10,000')
        return v

    @field_validator('tripDuration')
    @classmethod
    def validate_duration(cls, v):
        valid_durations = ['weekend', 'week', 'two-weeks', 'month', 'long-term']
        if v not in valid_durations:
            raise ValueError('Invalid trip duration')
        return v

    @field_validator('interests')
    @classmethod
    def validate_interests(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one interest must be selected')
        valid_interests = ['romantic', 'adventure', 'culture', 'relaxation', 'food', 
                          'history', 'nature', 'shopping', 'nightlife', 'photography', 
                          'sports', 'luxury']
        for interest in v:
            if interest not in valid_interests:
                raise ValueError(f'Invalid interest: {interest}')
        return v

class TextToImageRequest(BaseModel):
    prompt: str
    style: Optional[str] = None

    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('Prompt must be at least 10 characters long')
        if len(v) > 500:
            raise ValueError('Prompt must be less than 500 characters')
        return v.strip()

    @field_validator('style')
    @classmethod
    def validate_style(cls, v):
        if v and v not in ['artistic', 'cartoon', 'photographic', 'painting', 'sketch']:
            raise ValueError('Invalid style')
        return v

class LightXImageRequest(BaseModel):
    prompt: str
    image: Optional[str] = None  # Base64 encoded image

    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v):
        if not v or len(v.strip()) < 5:
            raise ValueError('Prompt must be at least 5 characters long')
        if len(v) > 500:
            raise ValueError('Prompt must be less than 500 characters')
        return v.strip()

class BookingRequest(BaseModel):
    booking_type: str  # flights, hotels, activities, packages, agents
    item_id: str
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    travel_date: str
    return_date: Optional[str] = None
    passengers: int = 1
    special_requests: Optional[str] = None
    total_price: float
    currency: str = "USD"
    
    @field_validator('booking_type')
    @classmethod
    def validate_booking_type(cls, v):
        valid_types = ['flights', 'hotels', 'activities', 'packages', 'agents']
        if v not in valid_types:
            raise ValueError('Invalid booking type')
        return v
    
    @field_validator('customer_email')
    @classmethod
    def validate_email(cls, v):
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v
    
    @field_validator('travel_date')
    @classmethod
    def validate_travel_date(cls, v):
        from datetime import datetime
        try:
            travel_date = datetime.strptime(v, '%Y-%m-%d')
            if travel_date.date() < datetime.now().date():
                raise ValueError('Travel date must be in the future')
        except ValueError as e:
            if 'must be in the future' in str(e):
                raise e
            raise ValueError('Invalid date format. Use YYYY-MM-DD')
        return v
    
    @field_validator('return_date')
    @classmethod
    def validate_return_date(cls, v, info):
        if v and 'travel_date' in info.data:
            from datetime import datetime
            try:
                travel_date = datetime.strptime(info.data['travel_date'], '%Y-%m-%d')
                return_date = datetime.strptime(v, '%Y-%m-%d')
                if return_date <= travel_date:
                    raise ValueError('Return date must be after travel date')
            except ValueError as e:
                if 'must be after' in str(e):
                    raise e
                raise ValueError('Invalid return date format. Use YYYY-MM-DD')
        return v
    
    @field_validator('passengers')
    @classmethod
    def validate_passengers(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Passengers must be between 1 and 10')
        return v
    
    @field_validator('total_price')
    @classmethod
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Total price must be greater than 0')
        return v


class BookingSearchRequest(BaseModel):
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    passengers: int = 1
    class_type: str = "economy"
    search_type: str = "flights"  # flights, hotels, activities, packages

    @field_validator('passengers')
    @classmethod
    def validate_passengers(cls, v):
        if v < 1 or v > 9:
            raise ValueError('Passengers must be between 1 and 9')
        return v

    @field_validator('class_type')
    @classmethod
    def validate_class_type(cls, v):
        valid_classes = ['economy', 'premium', 'business', 'first']
        if v not in valid_classes:
            raise ValueError('Invalid class type')
        return v

    @field_validator('search_type')
    @classmethod
    def validate_search_type(cls, v):
        valid_types = ['flights', 'hotels', 'activities', 'packages']
        if v not in valid_types:
            raise ValueError('Invalid search type')
        return v

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: str

class FlightSearchRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    adults: int = 1
    children: int = 0
    infants: int = 0
    travel_class: str = "ECONOMY"
    currency_code: str = "USD"
    
    @field_validator('origin')
    @classmethod
    def validate_origin(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Origin must be at least 2 characters')
        return v.strip().upper()
    
    @field_validator('destination')
    @classmethod
    def validate_destination(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Destination must be at least 2 characters')
        return v.strip().upper()
    
    @field_validator('departure_date')
    @classmethod
    def validate_departure_date(cls, v):
        from datetime import datetime
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Departure date must be in YYYY-MM-DD format')
        return v
    
    @field_validator('return_date')
    @classmethod
    def validate_return_date(cls, v, info):
        if v:
            from datetime import datetime
            try:
                return_date = datetime.strptime(v, '%Y-%m-%d')
                departure_date = datetime.strptime(info.data['departure_date'], '%Y-%m-%d')
                if return_date <= departure_date:
                    raise ValueError('Return date must be after departure date')
            except ValueError as e:
                if 'Return date' in str(e):
                    raise e
                raise ValueError('Return date must be in YYYY-MM-DD format')
        return v

class HotelSearchRequest(BaseModel):
    city_code: str
    check_in_date: str
    check_out_date: str
    adults: int = 1
    children: int = 0
    room_quantity: int = 1
    currency_code: str = "USD"
    price_range: Optional[str] = None  # e.g., "50-200"
    ratings: Optional[str] = None  # e.g., "3,4,5"
    
    @field_validator('city_code')
    @classmethod
    def validate_city_code(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('City code must be at least 2 characters')
        return v.strip().upper()
    
    @field_validator('check_in_date')
    @classmethod
    def validate_check_in_date(cls, v):
        from datetime import datetime
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Check-in date must be in YYYY-MM-DD format')
        return v
    
    @field_validator('check_out_date')
    @classmethod
    def validate_check_out_date(cls, v, info):
        from datetime import datetime
        try:
            check_out_date = datetime.strptime(v, '%Y-%m-%d')
            check_in_date = datetime.strptime(info.data['check_in_date'], '%Y-%m-%d')
            if check_out_date <= check_in_date:
                raise ValueError('Check-out date must be after check-in date')
        except ValueError as e:
            if 'Check-out date' in str(e):
                raise e
            raise ValueError('Check-out date must be in YYYY-MM-DD format')
        return v
    
    @field_validator('adults')
    @classmethod
    def validate_adults(cls, v):
        if v < 1 or v > 9:
            raise ValueError('Number of adults must be between 1 and 9')
        return v
    
    @field_validator('room_quantity')
    @classmethod
    def validate_room_quantity(cls, v):
        if v < 1 or v > 9:
            raise ValueError('Number of rooms must be between 1 and 9')
        return v

# Rate limiting (simple in-memory implementation)
from collections import defaultdict
import time

request_counts = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # 1 minute
RATE_LIMIT_MAX_REQUESTS = 100  # 100 requests per minute

def check_rate_limit(client_ip: str):
    now = time.time()
    # Remove old requests outside the window
    request_counts[client_ip] = [req_time for req_time in request_counts[client_ip] 
                                if now - req_time < RATE_LIMIT_WINDOW]
    
    if len(request_counts[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    request_counts[client_ip].append(now)

# OpenAI Destination Generation
async def generate_destinations_with_openai(continent: Optional[str] = None, limit: int = 50) -> List[dict]:
    """Generate destination data using OpenAI API"""
    try:
        # Create a comprehensive prompt for destination generation
        continent_filter = f" from {continent}" if continent else ""
        prompt = f"""Generate {limit} diverse and exciting travel destinations from around the world{continent_filter}. Include destinations from different continents, countries, and cultures.

For each destination, provide:

1. A unique name (city/place name)
2. Country
3. Continent
4. A compelling description (2-3 sentences)
5. A realistic rating (4.0-5.0)
6. Price level ($, $$, or $$$)
7. Best time to visit
8. 4 key highlights/attractions

Format as a valid JSON array with these exact fields:
- id (UUID format)
- name
- country  
- city
- continent
- description
- image_url (use Unsplash URLs like: https://images.unsplash.com/photo-[ID]?w=800&h=600&fit=crop)
- rating
- price
- bestTime
- highlights (array of 4 strings)

Make destinations diverse, exciting, and realistic. Include popular and hidden gems from all continents. Ensure the JSON is properly formatted with no trailing commas.

IMPORTANT: Generate exactly {limit} destinations. Include a mix of:
- Major cities (Paris, Tokyo, New York, London, etc.)
- Natural wonders (Grand Canyon, Niagara Falls, Mount Fuji, etc.)
- Beach destinations (Maldives, Bali, Santorini, etc.)
- Cultural sites (Machu Picchu, Petra, Angkor Wat, etc.)
- Adventure destinations (Patagonia, Swiss Alps, New Zealand, etc.)
- Hidden gems and emerging destinations

Example format:
[
  {{
    "id": "uuid-here",
    "name": "Destination Name",
    "country": "Country",
    "city": "City",
    "continent": "Continent",
    "description": "Description here",
    "image_url": "https://images.unsplash.com/photo-1234567890?w=800&h=600&fit=crop",
    "rating": 4.5,
    "price": "$$",
    "bestTime": "Month-Month",
    "highlights": ["Highlight 1", "Highlight 2", "Highlight 3", "Highlight 4"]
  }}
]"""

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a travel expert. Generate realistic, exciting travel destinations with detailed information."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        # Parse the response
        content = response.choices[0].message.content
        if content is None:
            raise Exception("OpenAI returned empty content")
        content = content.strip()
        if not content:
            logger.warning("OpenAI returned empty content")
            return []
            
        logger.info(f"OpenAI generated destinations: {content[:200]}...")
        
        # Try to extract JSON from the response
        import json
        import re
        
        # Clean the content - remove markdown code blocks and fix common JSON issues
        cleaned_content = content.strip() if content is not None else ""
        if cleaned_content.startswith('```json'):
            cleaned_content = cleaned_content[7:]
        if cleaned_content.startswith('```'):
            cleaned_content = cleaned_content[3:]
        if cleaned_content.endswith('```'):
            cleaned_content = cleaned_content[:-3]
        cleaned_content = cleaned_content.strip()
        
        # Fix common JSON formatting issues
        cleaned_content = re.sub(r',\s*}', '}', cleaned_content)  # Remove trailing commas
        cleaned_content = re.sub(r',\s*]', ']', cleaned_content)  # Remove trailing commas in arrays
        
        # First, try to find JSON array in the response
        json_match = re.search(r'\[.*\]', cleaned_content, re.DOTALL) if cleaned_content else None
        if json_match:
            try:
                destinations_data = json.loads(json_match.group())
                
                # Ensure all required fields are present
                for dest in destinations_data:
                    if 'id' not in dest:
                        dest['id'] = str(uuid.uuid4())
                    if 'image_url' not in dest or not dest['image_url']:
                        # Generate a placeholder Unsplash URL
                        dest['image_url'] = f"https://images.unsplash.com/photo-{uuid.uuid4().hex[:8]}?w=800&h=600&fit=crop"
                    # Ensure other required fields
                    if 'rating' not in dest:
                        dest['rating'] = 4.5
                    if 'price' not in dest:
                        dest['price'] = "$$"
                    if 'bestTime' not in dest:
                        dest['bestTime'] = "Year-round"
                    if 'highlights' not in dest:
                        dest['highlights'] = ["Local Attractions", "Cultural Sites", "Natural Beauty", "Local Cuisine"]
                
                return destinations_data
            except json.JSONDecodeError as e:
                logger.warning(f"Could not parse JSON from OpenAI response: {e}")
                logger.debug(f"JSON content: {json_match.group()[:500]}...")
        
        # If JSON parsing failed, try to extract individual destinations
        try:
            # Look for individual destination objects with more flexible pattern
            dest_matches = re.findall(r'\{[^{}]*(?:"name"[^{}]*)[^{}]*\}', cleaned_content, re.DOTALL) if cleaned_content else []
            if dest_matches:
                destinations_data = []
                for match in dest_matches:
                    try:
                        # Clean the individual object
                        clean_match = re.sub(r',\s*}', '}', match)
                        dest = json.loads(clean_match)
                        dest['id'] = str(uuid.uuid4())
                        if 'image_url' not in dest:
                            dest['image_url'] = f"https://images.unsplash.com/photo-{uuid.uuid4().hex[:8]}?w=800&h=600&fit=crop"
                        if 'rating' not in dest:
                            dest['rating'] = 4.5
                        if 'price' not in dest:
                            dest['price'] = "$$"
                        if 'bestTime' not in dest:
                            dest['bestTime'] = "Year-round"
                        if 'highlights' not in dest:
                            dest['highlights'] = ["Local Attractions", "Cultural Sites", "Natural Beauty", "Local Cuisine"]
                        destinations_data.append(dest)
                    except json.JSONDecodeError as e:
                        logger.debug(f"Failed to parse individual destination: {e}")
                        continue
                
                if destinations_data:
                    logger.info(f"Extracted {len(destinations_data)} destinations from malformed JSON")
                    return destinations_data
        except Exception as e:
            logger.warning(f"Failed to extract destinations from malformed response: {e}")
        
        logger.warning("Could not parse any destinations from OpenAI response")
        return []
            
    except Exception as e:
        logger.error(f"OpenAI destination generation failed: {e}")
        return []

# Dependency for getting client IP
def get_client_ip(request: Request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host if request.client else "unknown"

@app.get("/")
async def root():
    return {
        "message": "AI Travel App API v1.0", 
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle OPTIONS requests for CORS preflight"""
    return {"message": "OK"}

@app.get("/api/health")
async def api_health_check():
    return {"status": "ok"}

@app.get("/api/test-hotels")
async def test_hotels():
    """Test endpoint for hotel search"""
    return {
        "message": "Hotel search endpoint is working",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/temp-image/{image_id}")
async def get_temp_image(image_id: str):
    """Serve temporary images for LightX API"""
    try:
        if image_id not in temp_images:
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Get the base64 data
        base64_data = temp_images[image_id]
        
        # Convert base64 to bytes
        import base64
        image_bytes = base64.b64decode(base64_data)
        
        # Return the image with appropriate headers
        from fastapi.responses import Response
        return Response(content=image_bytes, media_type="image/jpeg")
        
    except Exception as e:
        logger.error(f"Failed to serve temp image {image_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve image")

@app.get("/debug")
async def debug_info():
    """Debug endpoint to check environment variables and configuration"""
    debug_info = {
        "environment": {
            "production": os.getenv("RENDER", "false").lower() == "true",
            "port": os.getenv("PORT", "Not Set"),
            "host": os.getenv("HOST", "Not Set")
        },
        "supabase": {
            "url_set": bool(os.getenv("SUPABASE_URL")),
            "key_set": bool(os.getenv("SUPABASE_KEY")),
            "client_initialized": supabase is not None,
            "connection_test": None
        },
        "openai": {
            "key_set": bool(os.getenv("OPENAI_API_KEY"))
        },
        "services": {
            "openai": openai_client is not None
        }
    }
    
    # Test Supabase connection if possible
    if supabase:
        try:
            result = supabase.table("destinations").select("id").limit(1).execute()
            debug_info["supabase"]["connection_test"] = {
                "success": True,
                "destinations_count": len(result.data) if result.data else 0
            }
        except Exception as e:
            debug_info["supabase"]["connection_test"] = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    return debug_info

@app.post("/api/upload-photo")
async def upload_photo(
    file: UploadFile = File(...)
):
    logger.info(f"Photo upload request received")
    
    try:
        # Enhanced validation
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="File must be an image (JPEG, PNG, WebP)"
            )

        # Size validation (max 10MB)
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="File too large (max 10MB)"
            )

        # Image validation and optimization
        try:
            img = Image.open(io.BytesIO(content))
            img.verify()
            # Reopen for processing
            img = Image.open(io.BytesIO(content))

            # Optimize image
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Resize if too large
            max_size = (1200, 1200)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Save optimized image
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=85, optimize=True)
            content = output.getvalue()

        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid image file"
            )

        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"user_{file_id}.jpg"

        # Try to upload to Supabase first
        if supabase:
            try:
                result = supabase.storage.from_("user-photos").upload(filename, content)

                if hasattr(result, 'status_code') and result.status_code != 200:
                    logger.warning(f"Supabase upload failed: {result}")
                    raise Exception("Supabase upload failed")

                # Get public URL
                public_url = supabase.storage.from_("user-photos").get_public_url(filename)

                logger.info(f"Photo uploaded successfully to Supabase: {filename}")
        
                return {
                    "success": True,
                    "photo_url": public_url,
                    "filename": filename,
                    "size": len(content),
                    "uploaded_at": datetime.now().isoformat(),
                    "storage": "supabase"
                }
                
            except Exception as e:
                logger.warning(f"Supabase upload failed, using fallback: {e}")
        
        # Fallback: Save to local storage or return a mock URL
        # For now, we'll return a mock URL that points to a placeholder image
        mock_url = f"https://via.placeholder.com/400x400/FF6B6B/FFFFFF?text=Uploaded+Photo"
        
        logger.info(f"Photo processed successfully (mock storage): {filename}")
        
        return {
            "success": True,
            "photo_url": mock_url,
            "filename": filename,
            "size": len(content),
            "uploaded_at": datetime.now().isoformat(),
            "storage": "mock"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Upload error: {str(e)}"
        )

@app.get("/api/destinations")
async def get_destinations(
    continent: Optional[str] = None, 
    limit: int = 50,
    randomize: bool = True
):
    try:
        # Always use OpenAI to generate fresh destinations for better variety
        try:
            openai_destinations = await generate_destinations_with_openai(continent, limit)
            
            if openai_destinations:
                logger.info(f"Generated {len(openai_destinations)} destinations with OpenAI")
                return {
                    "success": True,
                    "data": openai_destinations,
                    "count": len(openai_destinations),
                    "continent": continent,
                    "limit": limit,
                    "source": "openai",
                    "generated_at": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
        
        # Fallback to database if OpenAI fails
        if supabase:
            try:
                query = supabase.table("destinations").select("*")
                if continent:
                    query = query.eq("continent", continent)
                result = query.limit(limit).order("name").execute()
                
                if result.data and len(result.data) > 0:
                    # Add missing fields to database destinations
                    enhanced_destinations = []
                    for dest in result.data:
                        enhanced_dest = {
                            **dest,
                            "rating": dest.get("rating", 4.5),
                            "price": dest.get("price", "$$"),
                            "bestTime": dest.get("bestTime", "Year-round"),
                            "highlights": dest.get("highlights", [
                                "Local Attractions", 
                                "Cultural Sites", 
                                "Natural Beauty", 
                                "Local Cuisine"
                            ])
                        }
                        enhanced_destinations.append(enhanced_dest)
                    
                    logger.info(f"Retrieved {len(enhanced_destinations)} destinations from database")
                    return {
                        "success": True,
                        "data": enhanced_destinations,
                        "count": len(enhanced_destinations),
                        "continent": continent,
                        "limit": limit,
                        "source": "database"
                    }
            except Exception as e:
                logger.warning(f"Database query failed, using mock data: {e}")
        
        # Final fallback to mock data
        mock_destinations = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "name": "Santorini, Greece",
                "country": "Greece",
                "city": "Santorini",
                "continent": "Europe",
                "description": "Famous for its stunning sunsets, white-washed buildings, and crystal-clear waters. Perfect for romantic getaways and photography enthusiasts.",
                "image_url": "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?w=800&h=600&fit=crop",
                "rating": 4.8,
                "price": "$$$",
                "bestTime": "May-October",
                "highlights": ["Oia Sunset", "Blue Domes", "Wine Tasting", "Beach Hopping"]
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440002",
                "name": "Kyoto, Japan",
                "country": "Japan",
                "city": "Kyoto",
                "continent": "Asia",
                "description": "Ancient capital with traditional temples, beautiful gardens, and cherry blossoms. A perfect blend of history and natural beauty.",
                "image_url": "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=800&h=600&fit=crop",
                "rating": 4.7,
                "price": "$$",
                "bestTime": "March-May, October-November",
                "highlights": ["Cherry Blossoms", "Temples", "Tea Ceremony", "Bamboo Forest"]
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440003",
                "name": "Banff National Park",
                "country": "Canada",
                "city": "Banff",
                "continent": "North America",
                "description": "Stunning mountain landscapes, turquoise lakes, and abundant wildlife. A paradise for nature lovers and outdoor enthusiasts.",
                "image_url": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop",
                "rating": 4.9,
                "price": "$$",
                "bestTime": "June-September",
                "highlights": ["Lake Louise", "Hiking", "Wildlife", "Hot Springs"]
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440004",
                "name": "Machu Picchu",
                "country": "Peru",
                "city": "Cusco",
                "continent": "South America",
                "description": "Ancient Incan citadel set high in the Andes Mountains. One of the most impressive archaeological sites in the world.",
                "image_url": "https://images.unsplash.com/photo-1587595431973-160d0d94add1?w=800&h=600&fit=crop",
                "rating": 4.8,
                "price": "$$",
                "bestTime": "April-October",
                "highlights": ["Inca Trail", "Sun Gate", "Temple of the Sun", "Huayna Picchu"]
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440005",
                "name": "Safari in Serengeti",
                "country": "Tanzania",
                "city": "Serengeti",
                "continent": "Africa",
                "description": "Experience the wild beauty of Africa with incredible wildlife viewing, including the Great Migration.",
                "image_url": "https://images.unsplash.com/photo-1549366021-9f761d450615?w=800&h=600&fit=crop",
                "rating": 4.9,
                "price": "$$$",
                "bestTime": "June-October",
                "highlights": ["Wildlife Safari", "Great Migration", "Lion Spotting", "Sunset Drives"]
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440006",
                "name": "Sydney Opera House",
                "country": "Australia",
                "city": "Sydney",
                "continent": "Oceania",
                "description": "Iconic performing arts center with stunning harbor views. A masterpiece of modern architecture.",
                "image_url": "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?w=800&h=600&fit=crop",
                "rating": 4.6,
                "price": "$$",
                "bestTime": "September-May",
                "highlights": ["Opera Performances", "Harbor Bridge", "Bondi Beach", "Royal Botanic Garden"]
            }
        ]
        
        # Filter by continent if specified
        if continent:
            mock_destinations = [d for d in mock_destinations if d["continent"].lower() == continent.lower()]
        
        # Apply limit
        mock_destinations = mock_destinations[:limit]
        
        logger.info(f"Returning {len(mock_destinations)} mock destinations")
        return {
            "success": True,
            "data": mock_destinations,
            "count": len(mock_destinations),
            "continent": continent,
            "limit": limit,
            "source": "mock"
        }
        
    except Exception as e:
        logger.error(f"Failed to get destinations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )

@app.get("/api/continents")
async def get_continents():
    try:
        # First try to get from database
        if supabase:
            try:
                result = supabase.table("destinations").select("continent").execute()
                continents = list(set([d["continent"] for d in result.data if d["continent"]]))
                # Get count for each continent
                continent_data = []
                for continent in continents:
                    count_result = supabase.table("destinations").select("id").eq("continent", continent).execute()
                    continent_data.append({
                        "name": continent,
                        "count": len(count_result.data)
                    })
                if continent_data:
                    logger.info(f"Retrieved {len(continent_data)} continents from database")
                    return {
                        "success": True,
                        "data": sorted(continent_data, key=lambda x: x["name"])
                    }
            except Exception as e:
                logger.warning(f"Database query failed, using mock data: {e}")
        # Fallback to mock data
        mock_continents = [
            {"name": "Africa", "count": 1},
            {"name": "Asia", "count": 1},
            {"name": "Europe", "count": 1},
            {"name": "North America", "count": 1},
            {"name": "Oceania", "count": 1},
            {"name": "South America", "count": 1}
        ]
        logger.info(f"Returning {len(mock_continents)} mock continents")
        return {
            "success": True,
            "data": mock_continents
        }
    except Exception as e:
        logger.error(f"Failed to get continents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )

@app.post("/api/generate-visualization")
async def generate_visualization(
    data: VisualizationRequest
):
    logger.info(f"Visualization generation request: {data}")
    try:
        # Log the raw data and prompt
        logger.info(f"Raw request data: {data.dict()}")
        logger.info(f"Extracted prompt: {getattr(data, 'prompt', None)}")
        # If prompt is provided, use it directly
        prompt = data.prompt.strip() if getattr(data, 'prompt', None) is not None and isinstance(data.prompt, str) and data.prompt.strip() else ""
        destination = None
        logger.info(f"Final prompt value: '{prompt}' (length: {len(prompt)})")
        
        if not prompt:
            # Get destination - try database first, then fallback to mock data
            if data.destination_id:
                if supabase:
                    try:
                        dest_result = supabase.table("destinations").select("*").eq("id", data.destination_id).execute()
                        if dest_result and hasattr(dest_result, 'data') and dest_result.data:
                            destination = dest_result.data[0]
                    except Exception as e:
                        logger.warning(f"Database query failed: {e}")
                
                # If not found in database, use mock destinations
                if not destination:
                    mock_destinations = [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440001",
                            "name": "Santorini, Greece",
                            "country": "Greece",
                            "city": "Santorini",
                            "continent": "Europe",
                            "image_url": "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?w=800&h=600&fit=crop"
                        },
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440002",
                            "name": "Kyoto, Japan",
                            "country": "Japan",
                            "city": "Kyoto",
                            "continent": "Asia",
                            "image_url": "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=800&h=600&fit=crop"
                        },
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440003",
                            "name": "Banff National Park",
                            "country": "Canada",
                            "city": "Banff",
                            "continent": "North America",
                            "image_url": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop"
                        },
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440004",
                            "name": "Machu Picchu",
                            "country": "Peru",
                            "city": "Cusco",
                            "continent": "South America",
                            "image_url": "https://images.unsplash.com/photo-1587595431973-160d0d94add1?w=800&h=600&fit=crop"
                        },
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440005",
                            "name": "Safari in Serengeti",
                            "country": "Tanzania",
                            "city": "Serengeti",
                            "continent": "Africa",
                            "image_url": "https://images.unsplash.com/photo-1549366021-9f761d450615?w=800&h=600&fit=crop"
                        },
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440006",
                            "name": "Sydney Opera House",
                            "country": "Australia",
                            "city": "Sydney",
                            "continent": "Oceania",
                            "image_url": "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?w=800&h=600&fit=crop"
                        }
                    ]
                    for dest in mock_destinations:
                        if dest["id"] == data.destination_id:
                            destination = dest
                            break
                
                if not destination:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, 
                        detail="Destination not found"
                    )
                prompt = f"A person standing in {destination['name']}, {destination['country']}, with a beautiful travel photo. The scene should be realistic and show the person enjoying the destination."
            else:
                logger.error(f"Both prompt and destination_id are missing. Prompt: '{getattr(data, 'prompt', None)}', destination_id: '{getattr(data, 'destination_id', None)}'")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Either prompt or destination_id must be provided. Please enter a description of your desired scene or select a destination."
                )
        
        result_url = None
        hf_error = None
        try:
            # Download the user photo to a temp file
            import tempfile, requests
            selfie_url = data.user_photo_url
            if selfie_url is None or not selfie_url.strip():
                raise HTTPException(status_code=400, detail="user_photo_url is required")
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_img:
                img_resp = requests.get(selfie_url)
                temp_img.write(img_resp.content)
                temp_img.flush()
                temp_img_path = temp_img.name
            
            # Call Hugging Face Space
            hf_client = GradioClient("multimodalart/Ip-Adapter-FaceID", hf_token=os.getenv("HUGGINGFACE_TOKEN"))
            hf_result = hf_client.predict(
                images=[handle_file(temp_img_path)],
                prompt=prompt if prompt else "",
                negative_prompt="naked, bikini, skimpy, scanty, bare skin, lingerie, swimsuit, exposed, see-through",
                preserve_face_structure=True,
                face_strength=1.3,
                likeness_strength=1,
                nfaa_negative_prompt="naked, bikini, skimpy, scanty, bare skin, lingerie, swimsuit, exposed, see-through",
                api_name="/generate_image"
            )
            
            # hf_result is a list of dicts with 'image' key (file path)
            if hf_result and isinstance(hf_result, list) and len(hf_result) > 0 and isinstance(hf_result[0], dict) and 'image' in hf_result[0]:
                # Upload the image to a public location or serve it from backend
                # For now, return the local file path (not ideal for production)
                result_url = f"/static/generated/{os.path.basename(hf_result[0]['image'])}"
                # Optionally, move/copy the file to a static directory
                import shutil
                static_dir = os.path.join(os.path.dirname(__file__), "static", "generated")
                os.makedirs(static_dir, exist_ok=True)
                shutil.copy(hf_result[0]['image'], os.path.join(static_dir, os.path.basename(hf_result[0]['image'])))
                result_url = f"/static/generated/{os.path.basename(hf_result[0]['image'])}"
            else:
                raise Exception("No image returned from Hugging Face Space")
        except Exception as e:
            hf_error = str(e)
            logger.error(f"Hugging Face image generation failed: {hf_error}")
        
        # --- Fallback: OpenAI DALL-E ---
        if not result_url:
            try:
                response = openai_client.images.generate(
                    model="dall-e-3",
                    prompt=prompt if prompt else "",
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                result_image_url = response.data[0].url if response and hasattr(response, 'data') and response.data and len(response.data) > 0 else None
                if not result_image_url:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                        detail="Image generation failed"
                    )
                result_url = result_image_url
            except Exception as e:
                logger.error(f"OpenAI image generation failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                    detail=f"Image generation failed (HF: {hf_error}, DALL-E: {str(e)})"
                )
        
        # Save record if Supabase is available
        if supabase:
            try:
                viz_record = {
                    "destination_id": getattr(data, 'destination_id', None),
                    "user_photo_url": data.user_photo_url,
                    "generated_image_url": result_url,
                    "prompt": prompt,
                    "created_at": datetime.now().isoformat()
                }
                supabase.table("user_visualizations").insert(viz_record).execute()
            except Exception as e:
                logger.warning(f"Failed to save visualization record: {e}")
        
        logger.info(f"Visualization generated successfully: {result_url}")
        return {
            "success": True,
            "visualization_url": result_url,
            "prompt": prompt,
            "generated_at": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Visualization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Visualization error: {str(e)}"
        )

@app.get("/api/visualizations")
async def get_visualizations(
    limit: int = 20
):
    try:
        # Try to get from database if available
        if supabase:
            try:
                result = supabase.table("user_visualizations").select("""
                    *,
                    destinations (id, name, country, city, continent)
                """).order("created_at", desc=True).limit(limit).execute()

                logger.info(f"Retrieved {len(result.data)} visualizations from database")

                return {
                    "success": True,
                    "data": result.data,
                    "count": len(result.data),
                    "limit": limit
                }
            except Exception as e:
                logger.warning(f"Database query failed, using mock data: {e}")
        
        # Fallback to mock data
        mock_visualizations = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440007",
                "title": "Santorini Sunset Analysis",
                "location": "Oia, Greece",
                "date": "2024-01-15",
                "image": "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?w=400&h=300&fit=crop",
                "type": "sunset",
                "confidence": 0.95,
                "recommendations": ["Best viewing spots", "Optimal timing", "Photography tips"]
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440008",
                "title": "Kyoto Temple Architecture",
                "location": "Kyoto, Japan",
                "date": "2024-01-10",
                "image": "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=400&h=300&fit=crop",
                "type": "architecture",
                "confidence": 0.92,
                "recommendations": ["Historical significance", "Cultural context", "Visit timing"]
            }
        ]
        
        logger.info(f"Returning {len(mock_visualizations)} mock visualizations")
        return {
            "success": True,
            "data": mock_visualizations,
            "count": len(mock_visualizations),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get visualizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )

@app.post("/api/generate-personalized-recommendations")
async def generate_personalized_recommendations(
    data: RecommendationsRequest,
    request: Request
):
    """Generate personalized travel recommendations based on user preferences"""
    import logging
    import uuid
    logger = logging.getLogger("uvicorn.error")
    try:
        # Rate limiting
        client_ip = get_client_ip(request)
        check_rate_limit(client_ip)
        
        logger.info(f"Generating personalized recommendations for {data.ageGroup} {data.groupSize} group with ${data.budgetRange} budget")
        
        # Create comprehensive prompt for OpenAI
        interests_text = ", ".join(data.interests)
        country_text = f" The user's selected country is: {data.country}." if data.country else ""
        additional_context = f" Additional notes: {data.additionalNotes}" if data.additionalNotes else ""
        prompt = f"""Generate personalized travel recommendations for a {data.ageGroup} age group traveling as {data.groupSize} with a budget of ${data.budgetRange} for a {data.tripDuration} trip. The user's selected interests are: {interests_text}.{country_text}{additional_context}\n\nIMPORTANT: Tailor the recommended destinations, activities, and itinerary to match the user's interests and country as closely as possible. The interests and country are the most important factors for your suggestions.\n\nPlease provide a comprehensive response including:\n\n1. 10 recommended destinations with detailed descriptions and high-quality image URLs\n2. A custom itinerary for the trip duration\n3. Travel tips and recommendations\n4. Budget breakdown\n\nFormat the response as a valid JSON object with this exact structure:\n{{\n    "destinations": [ ... ],\n    "itinerary": [ ... ],\n    "travelTips": [ ... ],\n    "budgetBreakdown": {{ ... }}\n}}\n\nFor each destination, include:\n- id (unique identifier)\n- name (destination name)\n- country\n- description (2-3 sentences)\n- image_url (use high-quality Unsplash URLs like: https://images.unsplash.com/photo-[ID]?w=800&h=600&fit=crop)\n- rating (4.0-5.0)\n- price ($, $$, or $$$)\n- highlights (array of 4 key attractions)\n\nMake the recommendations realistic, exciting, and tailored to the specific preferences. Consider the age group, group size, budget, country, and especially the interests when making suggestions."""

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert travel consultant specializing in personalized travel recommendations. Provide detailed, realistic, and exciting travel suggestions tailored to specific user preferences."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2500,
            temperature=0.7
        )
        # Parse the response
        content = response.choices[0].message.content
        logger.info(f"Raw OpenAI response: {content}")
        if content is None:
            raise Exception("OpenAI returned empty content")
        content = content.strip()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate recommendations"
            )
        # Clean up markdown code blocks if present
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        content = content.strip('`\n ')
        # Try to extract JSON from the response using regex
        import re, json
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            json_content = json_match.group()
            try:
                recommendations = json.loads(json_content)
                # Validate the structure
                required_keys = ['destinations', 'itinerary', 'travelTips', 'budgetBreakdown']
                for key in required_keys:
                    if key not in recommendations:
                        raise ValueError(f"Missing required key: {key}")
                # Ensure all destinations have a unique id and image_url
                destinations = recommendations.get('destinations', [])
                for dest in destinations:
                    if not dest.get('id'):
                        dest['id'] = str(uuid.uuid4())
                    # Ensure each destination has a proper image_url
                    if not dest.get('image_url') or not dest['image_url'].startswith('http'):
                        # Generate a fallback Unsplash URL based on destination name
                        dest_name = dest.get('name', 'travel').replace(' ', '-').lower()
                        dest['image_url'] = f"https://images.unsplash.com/photo-{uuid.uuid4().hex[:8]}?w=800&h=600&fit=crop&query={dest_name}"
                    # Ensure other required fields
                    if 'rating' not in dest:
                        dest['rating'] = 4.5
                    if 'price' not in dest:
                        dest['price'] = "$$"
                    if 'highlights' not in dest:
                        dest['highlights'] = ["Local Attractions", "Cultural Sites", "Natural Beauty", "Local Cuisine"]
                logger.info(f"Successfully generated recommendations with {len(destinations)} destinations")
                return {
                    "success": True,
                    "data": recommendations,
                    "generated_at": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Failed to parse OpenAI JSON: {e}")
                logger.error(f"Raw JSON content: {json_content}")
        else:
            logger.error(f"No JSON found in OpenAI response: {content}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse recommendations from OpenAI"
        )
    except Exception as e:
        logger.error(f"Error generating personalized recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )

@app.post("/api/generate-text-to-image")
async def generate_text_to_image(
    data: TextToImageRequest,
    request: Request
):
    """Generate images from text prompts using AI"""
    try:
        # Rate limiting
        client_ip = get_client_ip(request)
        check_rate_limit(client_ip)
        
        logger.info(f"Generating image from text: {data.prompt[:50]}...")
        
        # Try OpenAI DALL-E first (better quality)
        try:
            # Prepare the prompt with style if specified
            prompt = data.prompt.strip() if data.prompt is not None and isinstance(data.prompt, str) else data.prompt
            if data.style:
                style_mappings = {
                    'artistic': 'in an artistic style',
                    'cartoon': 'in a cartoon style',
                    'photographic': 'in a realistic photographic style',
                    'painting': 'in a painting style',
                    'sketch': 'in a sketch style'
                }
                prompt += f" {style_mappings.get(data.style, '')}"
            
            # Call OpenAI DALL-E API
            response = openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            if response.data and len(response.data) > 0:
                image_url = response.data[0].url
                logger.info("Successfully generated image with OpenAI DALL-E")
                
                return {
                    "success": True,
                    "image_url": image_url,
                    "provider": "openai",
                    "generated_at": datetime.now().isoformat()
                }
            else:
                raise ValueError("No image data returned from OpenAI")
            
        except Exception as openai_error:
            logger.warning(f"OpenAI DALL-E failed, trying DeepAI: {openai_error}")
            
            # Fallback to DeepAI
            try:
                deepai_api_key = os.getenv("FACE_SWAP_API_KEY")
                if not deepai_api_key:
                    raise ValueError("DeepAI API key not found")
                
                # Use DeepAI text-to-image endpoint
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.deepai.org/api/text2img",
                        data={
                            'text': data.prompt,
                            'image_type': 'photo' if not data.style else data.style
                        },
                        headers={
                            'api-key': deepai_api_key
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if 'output_url' in result:
                            image_url = result['output_url']
                            logger.info("Successfully generated image with DeepAI")
                            
                            return {
                                "success": True,
                                "image_url": image_url,
                                "provider": "deepai",
                                "generated_at": datetime.now().isoformat()
                            }
                        else:
                            raise ValueError("No image URL in DeepAI response")
                    else:
                        raise ValueError(f"DeepAI API error: {response.status_code}")
                        
            except Exception as deepai_error:
                logger.error(f"DeepAI also failed: {deepai_error}")
                
                # Return a placeholder image as final fallback
                placeholder_url = "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=400&fit=crop"
                
                return {
                    "success": True,
                    "image_url": placeholder_url,
                    "provider": "placeholder",
                    "note": "Using placeholder image due to API issues",
                    "generated_at": datetime.now().isoformat()
                }
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text-to-image generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate image: {str(e)}"
        )

@app.post("/api/generate-lightx-image")
async def generate_lightx_image(
    data: LightXImageRequest,
    request: Request
):
    """
    Generate images using LightX API with optional image upload
    """
    client_ip = get_client_ip(request)
    logger.info(f"LightX image generation request from {client_ip}: {data.prompt[:50]}...")
    
    try:
        # Check rate limiting
        check_rate_limit(client_ip)
        
        # Prepare LightX API request based on documentation
        headers = {
            "x-api-key": LIGHTX_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Determine the endpoint based on whether image is provided
        if data.image:
            # For image enhancement/transformation using background-generator
            # Convert base64 to a temporary public URL
            image_url = create_temp_image_url(data.image)
            
            url = f"{LIGHTX_BASE_URL}/external/api/v1/background-generator"
            payload = {
                "imageUrl": image_url,  # User's uploaded image URL
                "styleImageUrl": image_url,  # Using same image as style for now
                "textPrompt": data.prompt
            }
            mode = "image-enhancement"
        else:
            # For text-to-image generation - use background-generator with a default image
            url = f"{LIGHTX_BASE_URL}/external/api/v1/background-generator"
            
            # Use a default image for text-to-image generation
            default_image_url = "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop"
            
            payload = {
                "imageUrl": default_image_url,
                "styleImageUrl": default_image_url,
                "textPrompt": data.prompt
            }
            mode = "text-to-image"
        
        logger.info(f"Calling LightX API with mode: {mode}")
        logger.info(f"Making request to: {url}")
        
        # Check if demo mode is enabled
        if LIGHTX_DEMO_MODE:
            logger.info("LightX demo mode enabled - returning demo response")
            # Use different demo images based on the prompt
            demo_images = [
                "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop",
                "https://images.unsplash.com/photo-1494790108755-2616b612b786?w=400&h=400&fit=crop",
                "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&h=400&fit=crop"
            ]
            
            # Select a demo image based on prompt content
            import random
            demo_image = random.choice(demo_images)
            
            return {
                "success": True,
                "images": [{
                    "url": demo_image,
                    "prompt": data.prompt,
                    "provider": "lightx_demo",
                    "timestamp": datetime.now().isoformat()
                }],
                "provider": "lightx_demo",
                "prompt": data.prompt,
                "note": "Demo mode - LightX AI enhancement simulation"
            }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                logger.info("LightX API call successful")
                result = response.json()
                
                # Check if the API returned an error
                if result.get("status") == "FAIL":
                    error_code = result.get("statusCode")
                    error_desc = result.get("description", "")
                    
                    if error_code == 5047:  # INVALID_HUMAN_PORTRAIT
                        logger.warning("LightX API: No face found in image")
                        # Return a helpful error message
                        raise Exception("No face detected in the image. LightX AI works best with human portraits.")
                    elif error_code == 1000:  # Generic error
                        logger.warning(f"LightX API generic error: {error_desc}")
                        raise Exception("LightX AI couldn't process this image. Please try with a clear human portrait photo.")
                    else:
                        logger.warning(f"LightX API returned error: {error_desc}")
                        raise Exception(f"LightX AI error: {error_desc}")
                
                # Extract image URLs from the response
                # The exact structure depends on LightX API response format
                if "images" in result:
                    images = result["images"]
                elif "data" in result and "images" in result["data"]:
                    images = result["data"]["images"]
                elif "imageUrl" in result:
                    images = [{"url": result["imageUrl"]}]
                else:
                    # Fallback: create a single image entry
                    images = [{"url": result.get("imageUrl", result.get("url", ""))}]
                
                return {
                    "success": True,
                    "images": [{
                        "url": img.get("url", img.get("imageUrl", "")),
                        "prompt": data.prompt,
                        "provider": "lightx",
                        "timestamp": datetime.now().isoformat()
                    } for img in images if img.get("url") or img.get("imageUrl")],
                    "provider": "lightx",
                    "prompt": data.prompt
                }
            else:
                logger.warning(f"LightX API call failed with status {response.status_code}: {response.text}")
                # Fall back to demo response
                raise Exception(f"LightX API returned status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"LightX API request failed: {e}")
            # Fall back to demo response
            raise Exception(f"LightX API request failed: {e}")
        
        # Fallback demo response if API call fails
        logger.info("LightX API not accessible - returning demo response")
        
        # Use different demo images based on the prompt
        demo_images = [
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop",
            "https://images.unsplash.com/photo-1494790108755-2616b612b786?w=400&h=400&fit=crop",
            "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&h=400&fit=crop"
        ]
        
        # Select a demo image based on prompt content
        import random
        demo_image = random.choice(demo_images)
        
        return {
            "success": True,
            "images": [{
                "url": demo_image,
                "prompt": data.prompt,
                "provider": "lightx_demo",
                "timestamp": datetime.now().isoformat()
            }],
            "provider": "lightx_demo",
            "prompt": data.prompt,
            "note": "Demo mode - LightX AI enhancement simulation"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LightX image generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate LightX image: {str(e)}"
        )

# Booking API Endpoints
@app.get("/api/destination-suggestions")
async def get_destination_suggestions(
    query: str,
    request: Request
):
    """Get destination suggestions based on user input using OpenAI"""
    client_ip = get_client_ip(request)
    check_rate_limit(client_ip)
    
    try:
        if not query or len(query.strip()) < 2:
            return {"suggestions": []}
        
        query = query.strip()
        logger.info(f"Getting destination suggestions for: {query}")
        
        # Try OpenAI for intelligent suggestions
        try:
            if not openai_client.api_key:
                raise Exception("OpenAI API key not configured")
            
            prompt = f"""Given the user input "{query}", suggest 12 popular travel destinations (cities, countries, regions, landmarks, or natural wonders) that match or are related to this query. 

Return only a JSON array of strings with destination names in this exact format:
["Destination 1", "Destination 2", "Destination 3", ...]

Include a mix of:
- Major cities and capitals
- Popular tourist destinations
- Natural wonders and landmarks
- Countries and regions
- Beach destinations
- Cultural sites
- Adventure destinations

Examples:
- For "par" → ["Paris, France", "Barcelona, Spain", "Milan, Italy", "Bangkok, Thailand", "Mumbai, India", "Buenos Aires, Argentina", "Cairo, Egypt", "Osaka, Japan", "Park City, USA", "Paros, Greece", "Paraguay", "Patagonia"]
- For "tok" → ["Tokyo, Japan", "Toronto, Canada", "Stockholm, Sweden", "Istanbul, Turkey", "Bangkok, Thailand", "Moscow, Russia", "Seoul, South Korea", "Melbourne, Australia", "Toulouse, France", "Toledo, Spain", "Tuscany, Italy", "Tahiti"]
- For "beach" → ["Bali, Indonesia", "Maldives", "Hawaii, USA", "Santorini, Greece", "Phuket, Thailand", "Cancun, Mexico", "Fiji", "Seychelles", "Bora Bora", "Maui, Hawaii", "Gold Coast, Australia", "Copacabana, Brazil"]
- For "mountain" → ["Swiss Alps", "Rocky Mountains", "Mount Fuji", "Himalayas", "Andes", "Alps", "Mount Kilimanjaro", "Banff National Park", "Patagonia", "Yosemite", "Matterhorn", "Mount Everest"]

Focus on popular, well-known destinations that travelers would actually search for. Be creative and include diverse options."""
            
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.8
            )
            
            content = response.choices[0].message.content
            if content is None:
                raise Exception("OpenAI returned empty content")
            content = content.strip()
            
            # Parse JSON response
            import json
            import re
            
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', content, re.DOTALL) if content else None
            if json_match:
                suggestions = json.loads(json_match.group())
                logger.info(f"OpenAI suggestions: {suggestions}")
                return {"suggestions": suggestions[:12]}
            else:
                raise Exception("Invalid JSON response from OpenAI")
                
        except Exception as openai_error:
            logger.warning(f"OpenAI suggestions failed: {openai_error}")
            
            # Enhanced fallback to static suggestions
            static_suggestions = {
                'par': ['Paris, France', 'Barcelona, Spain', 'Milan, Italy', 'Bangkok, Thailand', 'Park City, USA', 'Paros, Greece'],
                'tok': ['Tokyo, Japan', 'Toronto, Canada', 'Stockholm, Sweden', 'Istanbul, Turkey', 'Toulouse, France', 'Toledo, Spain'],
                'lon': ['London, UK', 'Los Angeles, USA', 'Lyon, France', 'Lima, Peru', 'Long Beach, USA', 'Lombok, Indonesia'],
                'new': ['New York, USA', 'New Delhi, India', 'Newcastle, UK', 'New Orleans, USA', 'New Zealand', 'Newfoundland, Canada'],
                'san': ['San Francisco, USA', 'Santorini, Greece', 'Santiago, Chile', 'San Diego, USA', 'San Antonio, USA', 'San Jose, Costa Rica'],
                'dub': ['Dubai, UAE', 'Dublin, Ireland', 'Dubrovnik, Croatia', 'Durban, South Africa', 'Dubai Marina', 'Dublin Castle'],
                'bea': ['Bali, Indonesia', 'Barcelona, Spain', 'Bangkok, Thailand', 'Berlin, Germany', 'Beach destinations', 'Beirut, Lebanon'],
                'rom': ['Rome, Italy', 'Roma, Italy', 'Romania', 'Romantic destinations', 'Rome, Georgia', 'Roman Colosseum'],
                'sea': ['Seattle, USA', 'Seoul, South Korea', 'Seville, Spain', 'Seaside destinations', 'Serengeti, Tanzania', 'Seychelles'],
                'chi': ['Chicago, USA', 'China', 'Chile', 'Chiang Mai, Thailand', 'Chichen Itza, Mexico', 'Chamonix, France'],
                'mou': ['Mount Fuji, Japan', 'Mount Everest', 'Mountain destinations', 'Moscow, Russia', 'Mumbai, India', 'Munich, Germany'],
                'bea': ['Beach destinations', 'Bali, Indonesia', 'Barcelona, Spain', 'Bangkok, Thailand', 'Berlin, Germany', 'Beirut, Lebanon'],
                'is': ['Istanbul, Turkey', 'Island destinations', 'Israel', 'Isle of Skye, Scotland', 'Isla Mujeres, Mexico', 'Ischia, Italy']
            }
            
            # Find matching suggestions
            suggestions = []
            for key, values in static_suggestions.items():
                if query.lower().startswith(key.lower()):
                    suggestions.extend(values)
                    break
            
            # Add some popular destinations if no match
            if not suggestions:
                popular_destinations = [
                    'Paris, France', 'Tokyo, Japan', 'New York, USA', 'London, UK',
                    'Barcelona, Spain', 'Rome, Italy', 'Bali, Indonesia', 'Dubai, UAE',
                    'Singapore', 'Sydney, Australia', 'Amsterdam, Netherlands', 'Prague, Czech Republic',
                    'Machu Picchu, Peru', 'Petra, Jordan', 'Angkor Wat, Cambodia', 'Taj Mahal, India',
                    'Grand Canyon, USA', 'Niagara Falls', 'Mount Fuji, Japan', 'Swiss Alps',
                    'Maldives', 'Hawaii, USA', 'Santorini, Greece', 'Phuket, Thailand'
                ]
                suggestions = [dest for dest in popular_destinations if query.lower() in dest.lower()]
            
            return {"suggestions": suggestions[:12]}
    
    except Exception as e:
        logger.error(f"Destination suggestions failed: {e}")
        return {"suggestions": []}

@app.post("/api/book")
async def create_booking(
    data: BookingRequest,
    request: Request
):
    """Create a new booking"""
    logger.info(f"Booking request received: {data.booking_type}")
    
    try:
        # Rate limiting
        client_ip = get_client_ip(request)
        check_rate_limit(client_ip)
        
        # Generate unique booking ID
        booking_id = f"BK{uuid.uuid4().hex[:8].upper()}"
        
        # Prepare booking data
        booking_data = {
            "id": booking_id,
            "booking_type": data.booking_type,
            "item_id": data.item_id,
            "customer_name": data.customer_name,
            "customer_email": data.customer_email,
            "customer_phone": data.customer_phone,
            "travel_date": data.travel_date,
            "return_date": data.return_date,
            "passengers": data.passengers,
            "special_requests": data.special_requests,
            "total_price": data.total_price,
            "currency": data.currency,
            "status": "confirmed",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Save to database if available
        if supabase:
            try:
                result = supabase.table("bookings").insert(booking_data).execute()
                logger.info(f"Booking saved to database: {booking_id}")
            except Exception as e:
                logger.error(f"Failed to save booking to database: {e}")
                # Continue with mock storage
        else:
            logger.warning("Supabase not available, using mock storage")
        
        # Send confirmation email (mock for now)
        # In production, integrate with email service like SendGrid, Mailgun, etc.
        logger.info(f"Mock email sent to {data.customer_email} for booking {booking_id}")
        
        logger.info(f"Booking created successfully: {booking_id}")
        
        return {
            "success": True,
            "booking_id": booking_id,
            "message": "Booking confirmed successfully!",
            "booking": booking_data,
            "next_steps": [
                "Check your email for booking confirmation",
                "Review your booking details",
                "Contact us if you need any changes"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Booking error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Booking failed: {str(e)}"
        )

@app.post("/api/search-bookings")
async def search_bookings(
    data: BookingSearchRequest,
    request: Request
):
    """Search for flights, hotels, activities, or packages using OpenAI for pricing and availability"""
    client_ip = get_client_ip(request)
    check_rate_limit(client_ip)
    
    try:
        logger.info(f"Searching {data.search_type} for: {data.from_location} to {data.to_location}")
        
        # Try OpenAI for intelligent booking data
        try:
            if not openai_client.api_key:
                raise Exception("OpenAI API key not configured")
            
            # Create context-aware prompt based on search type
            if data.search_type == "flights":
                prompt = f"""Generate 6 realistic flight options from {data.from_location or 'any major city'} to {data.to_location or 'any major city'} for {data.passengers} passenger(s) in {data.class_type} class.

Consider:
- Real airline names (Delta, United, American, Emirates, Lufthansa, etc.)
- Realistic prices based on distance and class
- Realistic flight durations
- Realistic departure times
- Aircraft types

Return as JSON array with these exact fields:
```json
[
  {{
    "id": "unique_id",
    "airline": "Airline Name",
    "flightNumber": "XX1234",
    "from": "Departure City",
    "to": "Destination City", 
    "departureTime": "HH:MM AM/PM",
    "departureDate": "YYYY-MM-DD",
    "duration": "Xh Ym",
    "price": 123,
    "aircraft": "Boeing 737/Airbus A320/etc",
    "stops": 0,
    "class": "{data.class_type}"
  }}
]```"""
            
            elif data.search_type == "hotels":
                prompt = f"""Generate 6 realistic hotel options in {data.to_location or 'a popular destination'} for {data.passengers} guest(s).

Consider:
- Real hotel chains (Marriott, Hilton, Hyatt, etc.) and boutique hotels
- Realistic prices based on location and quality
- Realistic ratings (4.0-5.0)
- Realistic amenities
- Realistic locations

Return as JSON array with these exact fields:
```json
[
  {{
    "id": "unique_id",
    "name": "Hotel Name",
    "location": "City, Country",
    "rating": 4.5,
    "price": 123,
    "amenities": ["WiFi", "Pool", "Spa"],
    "description": "Brief description",
    "image": "https://images.unsplash.com/photo-...",
    "distance": "0.5 km from center"
  }}
]```"""
            
            elif data.search_type == "activities":
                prompt = f"""Generate 6 realistic activity options in {data.to_location or 'a popular destination'} for {data.passengers} participant(s).

Consider:
- Popular tourist activities
- Realistic prices
- Realistic durations
- Realistic ratings
- Realistic descriptions

Return as JSON array with these exact fields:
```json
[
  {{
    "id": "unique_id",
    "name": "Activity Name",
    "location": "City, Country",
    "rating": 4.5,
    "price": 123,
    "duration": "3 hours",
    "description": "Brief description",
    "image": "https://images.unsplash.com/photo-...",
    "category": "Adventure/Culture/Food/etc"
  }}
]```"""
            
            else:  # packages
                prompt = f"""Generate 6 realistic travel package options from {data.from_location or 'any major city'} to {data.to_location or 'any major city'} for {data.passengers} traveler(s).

Consider:
- All-inclusive packages
- Realistic prices
- Realistic durations
- Realistic inclusions
- Realistic descriptions

Return as JSON array with these exact fields:
```json
[
  {{
    "id": "unique_id",
    "name": "Package Name",
    "from": "Departure City",
    "to": "Destination City",
    "duration": "7 days",
    "price": 1234,
    "description": "Brief description",
    "inclusions": ["Flight", "Hotel", "Transfers"],
    "image": "https://images.unsplash.com/photo-..."
  }}
]```"""
            
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            if content is None:
                raise Exception("OpenAI returned empty content")
            content = content.strip()
            
            # Parse JSON response
            import json
            import re
            
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', content, re.DOTALL) if content else None
            if json_match:
                results = json.loads(json_match.group())
                logger.info(f"OpenAI {data.search_type} results: {len(results)} items")
                return {"results": results, "provider": "openai"}
            else:
                raise Exception("Invalid JSON response from OpenAI")
                
        except Exception as openai_error:
            logger.warning(f"OpenAI booking search failed: {openai_error}")
            
            # Fallback to mock data
            results = get_mock_booking_results(data.search_type, data.from_location, data.to_location, data.passengers, data.class_type)
            return {"results": results, "provider": "mock"}
    
    except Exception as e:
        logger.error(f"Booking search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search bookings: {str(e)}"
        )

def get_mock_flight_results(origin: str, destination: str):
    """Generate mock flight results for fallback"""
    import random
    from datetime import datetime, timedelta
    
    airlines = ["American Airlines", "Delta", "United", "Southwest", "JetBlue", "Alaska Airlines"]
    flight_numbers = [f"{random.choice(['AA', 'DL', 'UA', 'WN', 'B6', 'AS'])}{random.randint(1000, 9999)}" for _ in range(6)]
    
    flights = []
    for i in range(6):
        # Generate random departure time
        departure_hour = random.randint(6, 22)
        departure_minute = random.choice([0, 15, 30, 45])
        departure_time = datetime.now().replace(hour=departure_hour, minute=departure_minute, second=0, microsecond=0)
        
        # Flight duration between 1-8 hours
        duration_hours = random.randint(1, 8)
        duration_minutes = random.randint(0, 59)
        arrival_time = departure_time + timedelta(hours=duration_hours, minutes=duration_minutes)
        
        # Price between $200-$1500
        base_price = random.randint(200, 1500)
        price = base_price + (i * 50)  # Slight price variation
        
        flight = {
            "id": f"mock_flight_{i+1}",
            "price": {
                "total": str(price),
                "currency": "USD"
            },
            "itineraries": [{
                "segments": [{
                    "departure": {
                        "iataCode": origin,
                        "terminal": str(random.randint(1, 5)),
                        "at": departure_time.strftime("%Y-%m-%dT%H:%M:%S")
                    },
                    "arrival": {
                        "iataCode": destination,
                        "terminal": str(random.randint(1, 5)),
                        "at": arrival_time.strftime("%Y-%m-%dT%H:%M:%S")
                    },
                    "carrierCode": flight_numbers[i][:2],
                    "number": flight_numbers[i][2:],
                    "aircraft": {
                        "code": random.choice(["738", "739", "320", "321", "777", "787"])
                    },
                    "operating": {
                        "carrierCode": flight_numbers[i][:2]
                    },
                    "duration": f"PT{duration_hours}H{duration_minutes}M",
                    "id": f"segment_{i+1}",
                    "numberOfStops": 0,
                    "blacklistedInEU": False
                }]
            }],
            "numberOfBookableSeats": random.randint(1, 50),
            "travelerPricings": [{
                "travelerId": "1",
                "fareOption": "STANDARD",
                "pricingOptions": {
                    "fareType": ["PUBLISHED"]
                },
                "price": {
                    "currency": "USD",
                    "total": str(price),
                    "base": str(int(price * 0.8))
                }
            }]
        }
        flights.append(flight)
    
    return flights

def get_mock_hotel_results(city_code: str):
    """Generate mock hotel data for a specific city"""
    hotel_chains = ["Marriott", "Hilton", "Hyatt", "InterContinental", "Four Seasons", "Ritz-Carlton", "W Hotels", "Sheraton", "Westin", "Renaissance"]
    amenities = [["WiFi", "Pool", "Spa"], ["WiFi", "Gym", "Restaurant"], ["WiFi", "Pool", "Gym", "Spa"], ["WiFi", "Restaurant", "Bar"], ["WiFi", "Pool", "Gym", "Restaurant", "Spa"]]
    
    hotels = []
    for i in range(6):
        base_price = 150 + (i * 75)
        hotels.append({
            "id": f"mock_hotel_{i+1}",
            "name": f"{hotel_chains[i % len(hotel_chains)]} {city_code}",
            "rating": 4.0 + (i * 0.1),
            "location": {
                "latitude": 40.7128 + (i * 0.01),
                "longitude": -74.0060 + (i * 0.01),
                "address": {
                    "cityName": city_code,
                    "countryCode": "US"
                },
            },
            "amenities": amenities[i % len(amenities)],
            "price": {
                "total": str(base_price),
                "currency": "USD"
            },
            "room": {"description": "Standard Room"},
            "boardType": "ROOM_ONLY",
            "image_url": f"https://images.unsplash.com/photo-{1550000000 + i * 100000}?w=800&h=600&fit=crop&q=80"
        })
    return hotels

def get_mock_booking_results(search_type: str, from_location: Optional[str] = None, to_location: Optional[str] = None, passengers: int = 1, class_type: str = "economy"):
    """Generate realistic mock booking data"""
    
    if search_type == "flights":
        airlines = ["Delta", "United", "American", "Emirates", "Lufthansa", "British Airways", "Air France", "KLM", "Singapore Airlines", "Qatar Airways"]
        aircraft = ["Boeing 737", "Airbus A320", "Boeing 787", "Airbus A350", "Boeing 777", "Airbus A380"]
        
        flights = []
        for i in range(6):
            # Generate realistic prices based on class
            base_price = 200 + (i * 50)
            if class_type == "premium":
                base_price *= 1.5
            elif class_type == "business":
                base_price *= 2.5
            elif class_type == "first":
                base_price *= 4
            
            # Generate realistic duration based on distance
            duration_hours = 2 + (i % 4)  # 2-5 hours
            duration_minutes = (i * 15) % 60
            
            flights.append({
                "id": f"flight_{i+1}",
                "airline": airlines[i % len(airlines)],
                "flightNumber": f"{airlines[i % len(airlines)][:2].upper()}{1000 + i}",
                "from": from_location or "New York",
                "to": to_location or "London",
                "departureTime": f"{8 + (i * 2) % 12}:{30 + (i * 15) % 30:02d} {'AM' if (8 + (i * 2) % 12) < 12 else 'PM'}",
                "departureDate": "2024-06-15",
                "duration": f"{duration_hours}h {duration_minutes}m",
                "price": int(base_price * passengers),
                "aircraft": aircraft[i % len(aircraft)],
                "stops": i % 2,
                "class": class_type
            })
        return flights
    
    elif search_type == "hotels":
        hotel_chains = ["Marriott", "Hilton", "Hyatt", "InterContinental", "Four Seasons", "Ritz-Carlton", "W Hotels", "Sheraton", "Westin", "Renaissance"]
        amenities = [["WiFi", "Pool", "Spa"], ["WiFi", "Gym", "Restaurant"], ["WiFi", "Pool", "Gym", "Spa"], ["WiFi", "Restaurant", "Bar"], ["WiFi", "Pool", "Gym", "Restaurant", "Spa"]]
        
        hotels = []
        for i in range(6):
            base_price = 150 + (i * 75)
            hotels.append({
                "id": f"hotel_{i+1}",
                "name": f"{hotel_chains[i % len(hotel_chains)]} {to_location or 'Grand Hotel'}",
                "location": to_location or "New York, USA",
                "rating": 4.0 + (i * 0.1),
                "price": int(base_price * passengers),
                "amenities": amenities[i % len(amenities)],
                "description": f"Luxurious {hotel_chains[i % len(hotel_chains)]} property in the heart of {to_location or 'the city'}",
                "image": f"https://images.unsplash.com/photo-{1550000000 + i * 100000}?w=400&h=300&fit=crop",
                "distance": f"{0.5 + (i * 0.3):.1f} km from center"
            })
        return hotels
    
    elif search_type == "activities":
        activities = ["City Tour", "Museum Visit", "Adventure Hike", "Cooking Class", "Wine Tasting", "Boat Cruise", "Photography Tour", "Historical Walk", "Food Tour", "Spa Treatment"]
        categories = ["Culture", "Adventure", "Food", "Nature", "Wellness", "History"]
        
        activity_results = []
        for i in range(6):
            base_price = 50 + (i * 25)
            activity_results.append({
                "id": f"activity_{i+1}",
                "name": activities[i % len(activities)],
                "location": to_location or "New York, USA",
                "rating": 4.0 + (i * 0.1),
                "price": int(base_price * passengers),
                "duration": f"{2 + (i % 4)} hours",
                "description": f"Experience the best {activities[i % len(activities)].lower()} in {to_location or 'the city'}",
                "image": f"https://images.unsplash.com/photo-{1560000000 + i * 100000}?w=400&h=300&fit=crop",
                "category": categories[i % len(categories)]
            })
        return activity_results
    
    else:  # packages
        package_types = ["All-Inclusive Beach", "City Break", "Adventure Tour", "Cultural Experience", "Luxury Escape", "Family Fun"]
        
        packages = []
        for i in range(6):
            base_price = 800 + (i * 200)
            packages.append({
                "id": f"package_{i+1}",
                "name": f"{package_types[i % len(package_types)]} Package",
                "from": from_location or "New York",
                "to": to_location or "Paris",
                "duration": f"{5 + (i % 7)} days",
                "price": int(base_price * passengers),
                "description": f"Complete {package_types[i % len(package_types)].lower()} experience from {from_location or 'New York'} to {to_location or 'Paris'}",
                "inclusions": ["Flight", "Hotel", "Transfers", "Some Meals", "Guided Tours"],
                "image": f"https://images.unsplash.com/photo-{1570000000 + i * 100000}?w=400&h=300&fit=crop"
            })
        return packages

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    error_response = ErrorResponse(
        detail=exc.detail,
        error_code=f"HTTP_{exc.status_code}",
        timestamp=datetime.now().isoformat()
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_response)
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    error_response = ErrorResponse(
        detail="Internal server error",
        error_code="INTERNAL_ERROR",
        timestamp=datetime.now().isoformat()
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(error_response)
    )

@app.post("/api/search-flights")
async def search_flights(
    data: FlightSearchRequest,
    request: Request
):
    """
    Search for flights using Amadeus API
    """
    try:
        # Rate limiting
        client_ip = get_client_ip(request)
        check_rate_limit(client_ip)
        
        # Log the incoming request for debugging
        logger.info(f"Flight search request: {data}")
        
        if not amadeus_client:
            logger.warning("Amadeus client not available, returning mock data")
            return {
                "success": True,
                "flights": get_mock_flight_results(data.origin, data.destination),
                "count": 6,
                "provider": "Mock Data (Amadeus unavailable)"
            }
        
        # Validate airport codes (basic validation)
        if len(data.origin) != 3 or len(data.destination) != 3:
            logger.warning(f"Invalid airport codes: {data.origin} -> {data.destination}")
            return {
                "success": True,
                "flights": get_mock_flight_results(data.origin, data.destination),
                "count": 6,
                "provider": "Mock Data (Invalid airport codes)"
            }
        
        # Log the cleaned airport codes
        logger.info(f"Using airport codes: {data.origin} -> {data.destination}")
        
        # Validate dates
        try:
            from datetime import datetime
            departure_date = datetime.strptime(data.departure_date, "%Y-%m-%d")
            if data.return_date:
                return_date = datetime.strptime(data.return_date, "%Y-%m-%d")
                if return_date <= departure_date:
                    logger.warning("Return date must be after departure date")
                    return {
                        "success": True,
                        "flights": get_mock_flight_results(data.origin, data.destination),
                        "count": 6,
                        "provider": "Mock Data (Invalid dates)"
                    }
        except ValueError as e:
            logger.warning(f"Invalid date format: {e}")
            return {
                "success": True,
                "flights": get_mock_flight_results(data.origin, data.destination),
                "count": 6,
                "provider": "Mock Data (Invalid date format)"
            }
        
        # Search for flights
        try:
            if data.return_date:
                # Round trip
                response = amadeus_client.shopping.flight_offers_search.get(
                    originLocationCode=data.origin,
                    destinationLocationCode=data.destination,
                    departureDate=data.departure_date,
                    returnDate=data.return_date,
                    adults=data.adults,
                    children=data.children,
                    infants=data.infants,
                    travelClass=data.travel_class,
                    currencyCode=data.currency_code,
                    max=50
                )
            else:
                # One way
                response = amadeus_client.shopping.flight_offers_search.get(
                    originLocationCode=data.origin,
                    destinationLocationCode=data.destination,
                    departureDate=data.departure_date,
                    adults=data.adults,
                    children=data.children,
                    infants=data.infants,
                    travelClass=data.travel_class,
                    currencyCode=data.currency_code,
                    max=50
                )
            
            # Process and format the response
            flights = []
            for offer in response.data:
                flight = {
                    "id": offer['id'],
                    "price": {
                        "total": offer['price']['total'],
                        "currency": offer['price']['currency']
                    },
                    "itineraries": offer['itineraries'],
                    "numberOfBookableSeats": offer.get('numberOfBookableSeats', 'N/A'),
                    "travelerPricings": offer['travelerPricings']
                }
                flights.append(flight)
            
            logger.info(f"Found {len(flights)} flights from Amadeus API")
            return {
                "success": True,
                "flights": flights,
                "count": len(flights),
                "provider": "Amadeus API"
            }
            
        except ResponseError as e:
            logger.error(f"Amadeus API error: {e}")
            logger.error(f"Amadeus error details: {e.description if hasattr(e, 'description') else 'No description'}")
            logger.error(f"Amadeus error code: {e.code if hasattr(e, 'code') else 'No code'}")
            # Return mock data instead of throwing an error
            return {
                "success": True,
                "flights": get_mock_flight_results(data.origin, data.destination),
                "count": 6,
                "provider": "Mock Data (Amadeus API error)"
            }
        
    except Exception as e:
        logger.error(f"Flight search error: {e}")
        # Return mock data instead of throwing an error
        return {
            "success": True,
            "flights": get_mock_flight_results(data.origin, data.destination),
            "count": 6,
            "provider": "Mock Data (Server error)"
        }

@app.post("/api/search-hotels")
async def search_hotels(
    data: HotelSearchRequest,
    request: Request
):
    """
    Search for hotels using Amadeus API
    """
    logger.info(f"Hotel search request received: {data}")
    try:
        # Rate limiting
        client_ip = get_client_ip(request)
        check_rate_limit(client_ip)
        
        if not amadeus_client:
            raise HTTPException(
                status_code=503,
                detail="Hotel search service is currently unavailable"
            )
        
        # Search for hotels using the correct Amadeus API method
        # First, get hotel list for the city
        hotels_response = amadeus_client.reference_data.locations.hotels.by_city.get(
            cityCode=data.city_code
        )
        
        if not hotels_response.data or len(hotels_response.data) == 0:
            # If no hotels found, return mock data
            logger.warning(f"No hotels found for city code: {data.city_code}")
            return {
                "success": True,
                "hotels": get_mock_hotel_results(data.city_code),
                "count": 6
            }
        
        # Get hotel offers for the first few hotels
        hotels = []
        hotel_count = min(10, len(hotels_response.data))  # Limit to 10 hotels
        
        for i, hotel_info in enumerate(hotels_response.data[:hotel_count]):
            try:
                # Get hotel offers for this specific hotel
                offers_response = amadeus_client.shopping.hotel_offers_search.get(
                    hotelIds=hotel_info['hotelId'],
                    checkInDate=data.check_in_date,
                    checkOutDate=data.check_out_date,
                    adults=data.adults,
                    children=data.children,
                    roomQuantity=data.room_quantity,
                    currencyCode=data.currency_code,
                    bestRateOnly=True
                )
                
                if offers_response.data and len(offers_response.data) > 0:
                    offer = offers_response.data[0]
                    hotel = {
                        "id": offer['id'],
                        "name": hotel_info.get('name', 'Hotel'),
                        "rating": hotel_info.get('rating', 4.0),
                        "location": {
                            "latitude": hotel_info.get('geoCode', {}).get('latitude'),
                            "longitude": hotel_info.get('geoCode', {}).get('longitude'),
                            "address": {
                                "cityName": hotel_info.get('address', {}).get('cityName'),
                                "countryCode": hotel_info.get('address', {}).get('countryCode')
                            },
                        },
                        "amenities": hotel_info.get('amenities', []),
                        "price": {
                            "total": offer['offers'][0]['price']['total'],
                            "currency": offer['offers'][0]['price']['currency']
                        },
                        "room": offer['offers'][0]['room'],
                        "boardType": offer['offers'][0].get('boardType', 'ROOM_ONLY'),
                        "image_url": f"https://images.unsplash.com/photo-{uuid.uuid4().hex[:8]}?w=800&h=600&fit=crop&q=80"
                    }
                    hotels.append(hotel)
                else:
                    # Create a hotel entry with mock pricing if no offers available
                    hotel = {
                        "id": f"hotel_{hotel_info['hotelId']}",
                        "name": hotel_info.get('name', 'Hotel'),
                        "rating": hotel_info.get('rating', 4.0),
                        "location": {
                            "latitude": hotel_info.get('geoCode', {}).get('latitude'),
                            "longitude": hotel_info.get('geoCode', {}).get('longitude'),
                            "address": {
                                "cityName": hotel_info.get('address', {}).get('cityName'),
                                "countryCode": hotel_info.get('address', {}).get('countryCode')
                            },
                        },
                        "amenities": hotel_info.get('amenities', []),
                        "price": {
                            "total": str(150 + (i * 50)),  # Mock pricing
                            "currency": data.currency_code
                        },
                        "room": {"description": "Standard Room"},
                        "boardType": "ROOM_ONLY",
                        "image_url": f"https://images.unsplash.com/photo-{uuid.uuid4().hex[:8]}?w=800&h=600&fit=crop&q=80"
                    }
                    hotels.append(hotel)
                    
            except Exception as e:
                logger.warning(f"Error getting offers for hotel {hotel_info.get('name', 'Unknown')}: {e}")
                continue
        
        # Hotels are already processed in the loop above
        
        return {
            "success": True,
            "hotels": hotels,
            "count": len(hotels)
        }
        
    except ResponseError as e:
        logger.error(f"Amadeus API error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Hotel search error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Hotel search error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during hotel search"
        )

# --- Begin: AI Photo App Integration ---
def generate_ai_image(selfie_path: Path, prompt: str) -> list[str]:
    from gradio_client import Client, handle_file
    import os
    import requests
    
    # Use the new Hugging Face token
    token = os.getenv("HUGGINGFACE_TOKEN")
    logger.info(f"Using Hugging Face token (first 8 chars): {token[:8] if token else 'None'}")
    
    # Check if we have a valid token
    if not token or token == "your_huggingface_token_here":
        logger.warning("No valid Hugging Face token found, using fallback")
        return generate_fallback_images(prompt)
    
    try:
        logger.info("Attempting to use Hugging Face API for image generation")
        client = Client("multimodalart/Ip-Adapter-FaceID", hf_token=token)
        
        # Set a longer timeout for the prediction
        result = client.predict(
            images=[handle_file(str(selfie_path))],
            prompt=prompt if prompt else "A person enjoying a beautiful travel destination",
            negative_prompt="",
            preserve_face_structure=True,
            face_strength=1.3,
            likeness_strength=1.0,
            nfaa_negative_prompt="naked, bikini, skimpy, scanty, bare skin, lingerie, swimsuit, exposed, see-through",
            api_name="/generate_image"
        )
        
        if not result or not isinstance(result, list) or len(result) == 0:
            raise ValueError("Unexpected response structure from Hugging Face")
        
        image_urls = []
        uploads_dir = Path(__file__).parent / "backend" / "static" / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        timestamp = int(time.time())
        
        for i, item in enumerate(result):
            if item and isinstance(item, dict) and "image" in item and item["image"]:
                image_path = item["image"]
                dest_filename = f"generated_{i+1}_{timestamp}_{os.path.basename(image_path)}"
                dest_path = uploads_dir / dest_filename
                shutil.copy(image_path, dest_path)
                image_urls.append(f"/static/uploads/{dest_filename}")
        
        if not image_urls:
            raise ValueError("No images found in result")
        
        logger.info(f"Successfully generated {len(image_urls)} images with Hugging Face")
        return image_urls
        
    except Exception as e:
        import traceback
        logger.error(f"Hugging Face API error: {e}")
        logger.error(traceback.format_exc())
        # Check for specific error types
        if any(keyword in str(e).lower() for keyword in [
            "401", "unauthorized", "invalid credentials", "token", "authentication",
            "upstream gradio app has raised an exception", "timeout", "connection"
        ]):
            logger.warning("Hugging Face API failed due to authentication or connection issues, using fallback")
        else:
            logger.warning(f"Hugging Face API failed with error: {e}, using fallback")
        return generate_fallback_images(prompt)

def generate_fallback_images(prompt: str) -> list[str]:
    """Generate fallback images using DALL-E or mock images when Hugging Face fails"""
    try:
        # Try DALL-E as fallback
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            logger.info("Using DALL-E as fallback for image generation")
            return generate_dalle_images(prompt)
        else:
            logger.info("No valid OpenAI key, using mock images")
            return generate_mock_images(prompt)
    except Exception as e:
        logger.error(f"Fallback generation failed: {e}")
        return generate_mock_images(prompt)

def generate_dalle_images(prompt: str) -> list[str]:
    """Generate images using DALL-E API"""
    try:
        # Check if we have a valid OpenAI key
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key or openai_key == "your_openai_api_key_here":
            logger.warning("No valid OpenAI key found, using mock images")
            return generate_mock_images(prompt)
        
        # Create a travel-themed prompt if the original is empty
        if not prompt or prompt.strip() == "":
            prompt = "A person enjoying a beautiful travel destination, high quality, photorealistic"
        else:
            # Enhance the prompt for better results
            prompt = f"A person enjoying {prompt}, high quality, photorealistic, travel photography"
        
        logger.info(f"Generating DALL-E image with prompt: {prompt}")
        
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        if response.data and len(response.data) > 0:
            image_url = response.data[0].url
            if not image_url:
                logger.error("DALL-E API returned empty image URL")
                raise Exception("DALL-E API returned empty image URL")
            
            # Download and save the image
            uploads_dir = Path(__file__).parent / "backend" / "static" / "uploads"
            uploads_dir.mkdir(exist_ok=True)
            
            # Download the image
            img_response = requests.get(image_url, timeout=30)
            if img_response.status_code == 200:
                filename = f"dalle_generated_{int(time.time())}.png"
                filepath = uploads_dir / filename
                with open(filepath, "wb") as f:
                    f.write(img_response.content)
                logger.info(f"Successfully generated DALL-E image: {filename}")
                return [f"/static/uploads/{filename}"]
            else:
                logger.error(f"Failed to download DALL-E image: {img_response.status_code}")
        
        raise Exception("DALL-E API returned no images")
    except Exception as e:
        logger.error(f"DALL-E generation failed: {e}")
        # Don't raise, return mock images instead
        return generate_mock_images(prompt)

def generate_mock_images(prompt: str) -> list[str]:
    """Generate mock travel images using Unsplash"""
    try:
        logger.info("Generating mock travel images")
        
        # Use reliable Unsplash URLs for mock images
        mock_images = [
            "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&q=80",
            "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800&h=600&fit=crop&q=80",
            "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&h=600&fit=crop&q=80"
        ]
        
        # Download and save mock images
        uploads_dir = Path(__file__).parent / "backend" / "static" / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        
        image_urls = []
        # Filter out None values and ensure all URLs are strings
        mock_images = [str(url) for url in mock_images if url is not None]
        
        for i, mock_url in enumerate(mock_images):
            try:
                if not mock_url:
                    logger.warning(f"Skipping empty mock URL at index {i}")
                    continue
                img_response = requests.get(mock_url, timeout=10)
                if img_response.status_code == 200:
                    filename = f"mock_generated_{i+1}_{int(time.time())}.jpg"
                    filepath = uploads_dir / filename
                    with open(filepath, "wb") as f:
                        f.write(img_response.content)
                    image_urls.append(f"/static/uploads/{filename}")
                    logger.info(f"Successfully downloaded mock image {i+1}: {filename}")
            except Exception as e:
                logger.error(f"Failed to download mock image {i+1}: {e}")
                continue
        
        if not image_urls:
            # If all downloads fail, return placeholder URLs
            logger.warning("All mock image downloads failed, returning placeholder URLs")
            return [
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&q=80",
                "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800&h=600&fit=crop&q=80"
            ]
        
        logger.info(f"Successfully generated {len(image_urls)} mock images")
        return image_urls
    except Exception as e:
        logger.error(f"Mock image generation failed: {e}")
        # Return placeholder URLs as last resort
        return [
            "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&q=80",
            "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800&h=600&fit=crop&q=80"
        ]
# --- Begin: Prompt Enhancement for IP-Adapter ---
def enhance_prompt_with_openai(user_prompt: str) -> str:
    """Enhance a user prompt for photorealistic AI image generation using OpenAI GPT."""
    try:
        system_prompt = (
            "You are an expert at creating prompts for AI face swap image generation. "
            "Rewrite the user's prompt to focus on the PERSON and their FACE being in the scene, "
            "while keeping the travel destination as background context. "
            "The goal is to show the person's face clearly in the travel setting. "
            "Use phrases like 'a person with their face clearly visible', 'showing the person's face', "
            "'the person's face is prominent, as well as the background details are important', etc. "
            "Keep it under 200 words and focus on the person first, then the location."
        )
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        enhanced = response.choices[0].message.content.strip() if response.choices[0].message.content else user_prompt
        logger.info(f"Enhanced prompt: {enhanced}")
        return enhanced
    except Exception as e:
        logger.error(f"Prompt enhancement failed: {e}")
        return user_prompt  # Fallback to original prompt
# --- End: Prompt Enhancement for IP-Adapter ---
@app.post("/api/generate-photo-app-image")
async def generate_photo_app_image(
    selfie: UploadFile = File(...),
    prompt: str = Form(...)
):
    try:
        uploads_dir = Path(__file__).parent / "backend" / "static" / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        filename = selfie.filename or "uploaded.jpg"
        upload_path = uploads_dir / filename
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(selfie.file, buffer)
        safe_prompt = prompt.strip() if prompt is not None and isinstance(prompt, str) else ""
         # Enhance the prompt using OpenAI before sending to IP-Adapter
        enhanced_prompt = enhance_prompt_with_openai(safe_prompt)
        image_urls = generate_ai_image(upload_path, enhanced_prompt)
        return {"success": True, "image_urls": image_urls}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
# --- End: AI Photo App Integration ---

# New OpenAI-powered endpoints for the enhanced travel planner

class ContinentGenerationRequest(BaseModel):
    prompt: str

class CountryGenerationRequest(BaseModel):
    continent: str
    prompt: str

class CityGenerationRequest(BaseModel):
    country: str
    prompt: str

class AreaGenerationRequest(BaseModel):
    city: str
    prompt: str

class ItineraryGenerationRequest(BaseModel):
    destinationId: str
    preferences: dict
    prompt: str

class ImageGenerationRequest(BaseModel):
    destinationId: str
    userPhotoUrl: str
    prompt: str

class RecommendationsGenerationRequest(BaseModel):
    preferences: dict
    prompt: str

class DestinationFilterRequest(BaseModel):
    criteria: dict
    prompt: str

class DestinationImagesRequest(BaseModel):
    destinations: List[dict]
    prompt: str

@app.post("/api/generate-continents")
async def generate_continents(
    data: ContinentGenerationRequest,
    request: Request
):
    """Generate continents using OpenAI API"""
    try:
        client_ip = get_client_ip(request)
        if not check_rate_limit(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

        # Use OpenAI to generate continent data
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a travel expert. Generate detailed continent information in JSON format."
                },
                {
                    "role": "user",
                    "content": data.prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000
        )

        # Parse the response and extract continent data
        content = response.choices[0].message.content
        # Extract JSON from the response
        import json
        import re
        
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', content if content is not None else '', re.DOTALL)
        if json_match:
            continent_data = json.loads(json_match.group())
            continents = continent_data.get('continents', [])
        else:
            # Fallback: generate structured data
            continents = [
                {
                    "name": "Asia",
                    "count": 48,
                    "description": "Largest continent with diverse cultures, ancient civilizations, and modern cities",
                    "visual_theme": "diverse landscapes and cultures"
                },
                {
                    "name": "Europe", 
                    "count": 44,
                    "description": "Historic continent with rich culture, art, and architecture",
                    "visual_theme": "historic cities and cultural heritage"
                },
                {
                    "name": "North America",
                    "count": 23,
                    "description": "Vast continent with diverse landscapes from Arctic to tropical",
                    "visual_theme": "natural wonders and modern cities"
                },
                {
                    "name": "Africa",
                    "count": 54,
                    "description": "Continent of incredible wildlife, ancient history, and diverse cultures",
                    "visual_theme": "wildlife and natural beauty"
                },
                {
                    "name": "Oceania",
                    "count": 14,
                    "description": "Island continent with stunning beaches and unique wildlife",
                    "visual_theme": "island paradise and marine life"
                },
                {
                    "name": "South America",
                    "count": 12,
                    "description": "Continent of Amazon rainforest, Andes mountains, and vibrant cultures",
                    "visual_theme": "rainforest and mountain landscapes"
                },
                {
                    "name": "Antarctica",
                    "count": 0,
                    "description": "Frozen continent of pristine wilderness and scientific research",
                    "visual_theme": "ice and snow landscapes"
                }
            ]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "continents": continents,
                "message": f"Generated {len(continents)} continents with OpenAI"
            }
        )

    except Exception as e:
        logger.error(f"Error generating continents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate continents: {str(e)}"
        )

@app.post("/api/generate-countries")
async def generate_countries(
    data: CountryGenerationRequest,
    request: Request
):
    """Generate countries for a continent using OpenAI API"""
    try:
        client_ip = get_client_ip(request)
        if not check_rate_limit(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

        # Use OpenAI to generate country data
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a travel expert. Generate detailed country information in JSON format."
                },
                {
                    "role": "user",
                    "content": data.prompt
                }
            ],
            temperature=0.7,
            max_tokens=3000
        )

        content = response.choices[0].message.content or ''
        import json
        import re
        
        json_match = re.search(r'\{.*\}', content if content is not None else '', re.DOTALL)
        if json_match:
            country_data = json.loads(json_match.group())
            countries = country_data.get('countries', [])
        else:
            # Fallback data for the continent
            continent_countries = {
                "Asia": [
                    {"name": "Japan", "description": "Land of the rising sun with ancient traditions and modern technology", "cities": ["Tokyo", "Kyoto", "Osaka"]},
                    {"name": "Thailand", "description": "Land of smiles with beautiful beaches and rich culture", "cities": ["Bangkok", "Phuket", "Chiang Mai"]},
                    {"name": "India", "description": "Incredible diversity with ancient history and vibrant culture", "cities": ["Mumbai", "Delhi", "Jaipur"]},
                    {"name": "Vietnam", "description": "Stunning landscapes and delicious cuisine", "cities": ["Ho Chi Minh City", "Hanoi", "Da Nang"]},
                    {"name": "South Korea", "description": "Modern cities and traditional culture", "cities": ["Seoul", "Busan", "Jeju"]}
                ],
                "Europe": [
                    {"name": "France", "description": "Art, culture, and culinary excellence", "cities": ["Paris", "Lyon", "Nice"]},
                    {"name": "Italy", "description": "Ancient history, art, and delicious food", "cities": ["Rome", "Florence", "Venice"]},
                    {"name": "Spain", "description": "Vibrant culture, beaches, and architecture", "cities": ["Madrid", "Barcelona", "Seville"]},
                    {"name": "Germany", "description": "Efficient cities and beautiful countryside", "cities": ["Berlin", "Munich", "Hamburg"]},
                    {"name": "Netherlands", "description": "Windmills, tulips, and cycling culture", "cities": ["Amsterdam", "Rotterdam", "The Hague"]}
                ]
            }
            countries = continent_countries.get(data.continent, [])

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "countries": countries,
                "message": f"Generated {len(countries)} countries for {data.continent}"
            }
        )

    except Exception as e:
        logger.error(f"Error generating countries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate countries: {str(e)}"
        )

@app.post("/api/generate-cities")
async def generate_cities(
    data: CityGenerationRequest,
    request: Request
):
    """Generate cities for a country using OpenAI API"""
    try:
        client_ip = get_client_ip(request)
        if not check_rate_limit(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

        # Use OpenAI to generate city data
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a travel expert. Generate detailed city information in JSON format."
                },
                {
                    "role": "user",
                    "content": data.prompt
                }
            ],
            temperature=0.7,
            max_tokens=3000
        )

        content = response.choices[0].message.content or ''
        import json
        import re
        
        json_match = re.search(r'\{.*\}', content if content is not None else '', re.DOTALL)
        if json_match:
            city_data = json.loads(json_match.group())
            cities = city_data.get('cities', [])
        else:
            # Fallback data for the country
            country_cities = {
                "Japan": [
                    {"id": "tokyo", "name": "Tokyo", "description": "Modern metropolis with ancient traditions", "areas": ["Shibuya", "Shinjuku", "Harajuku"]},
                    {"id": "kyoto", "name": "Kyoto", "description": "Ancient capital with temples and gardens", "areas": ["Gion", "Arashiyama", "Higashiyama"]},
                    {"id": "osaka", "name": "Osaka", "description": "Food capital with vibrant nightlife", "areas": ["Dotonbori", "Namba", "Umeda"]}
                ],
                "France": [
                    {"id": "paris", "name": "Paris", "description": "City of light with art and romance", "areas": ["Eiffel Tower", "Louvre", "Montmartre"]},
                    {"id": "lyon", "name": "Lyon", "description": "Gastronomic capital of France", "areas": ["Vieux Lyon", "Presqu'île", "Croix-Rousse"]},
                    {"id": "nice", "name": "Nice", "description": "Beautiful coastal city on the French Riviera", "areas": ["Promenade des Anglais", "Old Town", "Cimiez"]}
                ]
            }
            cities = country_cities.get(data.country, [])

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "cities": cities,
                "message": f"Generated {len(cities)} cities for {data.country}"
            }
        )

    except Exception as e:
        logger.error(f"Error generating cities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate cities: {str(e)}"
        )

@app.post("/api/generate-areas")
async def generate_areas(
    data: AreaGenerationRequest,
    request: Request
):
    """Generate areas for a city using OpenAI API"""
    try:
        client_ip = get_client_ip(request)
        if not check_rate_limit(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

        # Use OpenAI to generate area data
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a travel expert. Generate detailed area information in JSON format."
                },
                {
                    "role": "user",
                    "content": data.prompt
                }
            ],
            temperature=0.7,
            max_tokens=3000
        )

        content = response.choices[0].message.content or ''
        import json
        import re
        
        json_match = re.search(r'\{.*\}', content if content is not None else '', re.DOTALL)
        if json_match:
            area_data = json.loads(json_match.group())
            areas = area_data.get('areas', [])
        else:
            # Fallback data for the city
            city_areas = {
                "Tokyo": [
                    {"id": "shibuya", "name": "Shibuya", "description": "Fashion and youth culture district", "activities": ["Shopping", "People watching", "Nightlife"]},
                    {"id": "shinjuku", "name": "Shinjuku", "description": "Business and entertainment district", "activities": ["Skyscrapers", "Golden Gai", "Shinjuku Gyoen"]},
                    {"id": "harajuku", "name": "Harajuku", "description": "Fashion and street culture", "activities": ["Takeshita Street", "Meiji Shrine", "Yoyogi Park"]}
                ],
                "Paris": [
                    {"id": "eiffel", "name": "Eiffel Tower Area", "description": "Iconic landmark and surrounding gardens", "activities": ["Eiffel Tower", "Champ de Mars", "Trocadéro"]},
                    {"id": "louvre", "name": "Louvre District", "description": "Art and culture center", "activities": ["Louvre Museum", "Tuileries Garden", "Palais Royal"]},
                    {"id": "montmartre", "name": "Montmartre", "description": "Artistic hilltop neighborhood", "activities": ["Sacré-Cœur", "Place du Tertre", "Moulin Rouge"]}
                ]
            }
            areas = city_areas.get(data.city, [])

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "areas": areas,
                "message": f"Generated {len(areas)} areas for {data.city}"
            }
        )

    except Exception as e:
        logger.error(f"Error generating areas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate areas: {str(e)}"
        )

@app.post("/api/generate-itinerary")
async def generate_itinerary(
    data: ItineraryGenerationRequest,
    request: Request
):
    """Generate personalized itinerary using OpenAI API"""
    import logging
    logger = logging.getLogger("uvicorn.error")
    try:
        client_ip = get_client_ip(request)
        logger.info(f"/api/generate-itinerary called from {client_ip} with data: {data}")
        if not check_rate_limit(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

        # Build a fallback prompt if not provided
        prompt = data.prompt.strip() if hasattr(data, 'prompt') and isinstance(data.prompt, str) and data.prompt.strip() else None
        if not prompt:
            # Build a prompt using destinationId and preferences
            prefs = data.preferences if hasattr(data, 'preferences') else {}
            prefs_str = ", ".join(f"{k}: {v}" for k, v in prefs.items())
            prompt = f"Generate a detailed {len(prefs.get('tripDuration', ''))}-day itinerary for a trip to {data.destinationId}. User preferences: {prefs_str}. Include daily activities and a budget breakdown. Format as JSON with 'days' and 'budgetBreakdown'."
            logger.info(f"Fallback prompt used: {prompt}")

        # Use OpenAI to generate itinerary
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a travel expert. Generate detailed itineraries in JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=4000
        )

        content = response.choices[0].message.content
        import json
        import re
        
        json_match = re.search(r'\{.*\}', content if content is not None else '', re.DOTALL)
        if json_match:
            itinerary_data = json.loads(json_match.group())
            itinerary = itinerary_data.get('itinerary', {})
        else:
            # Fallback itinerary
            itinerary = {
                "destination": data.destinationId,
                "days": [
                    {
                        "title": "Day 1: Arrival and Orientation",
                        "activities": [
                            "Check into hotel",
                            "Explore the local area",
                            "Visit a local restaurant for dinner",
                            "Rest and prepare for tomorrow"
                        ]
                    },
                    {
                        "title": "Day 2: Main Attractions",
                        "activities": [
                            "Visit the main landmarks",
                            "Explore cultural sites",
                            "Try local cuisine",
                            "Evening entertainment"
                        ]
                    }
                ]
            }

        logger.info(f"Returning itinerary for {data.destinationId}: {itinerary}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "itinerary": itinerary,
                "message": f"Generated itinerary for {data.destinationId}"
            }
        )

    except Exception as e:
        logger.error(f"Error generating itinerary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate itinerary: {str(e)}"
        )

@app.post("/api/generate-image")
async def generate_image(
    data: ImageGenerationRequest,
    request: Request
):
    """Generate AI travel photo using OpenAI DALL-E"""
    try:
        client_ip = get_client_ip(request)
        if not check_rate_limit(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

        # Use OpenAI DALL-E to generate image
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=data.prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )

        image_url = response.data[0].url

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "image": {
                    "url": image_url,
                    "prompt": data.prompt
                },
                "message": "Generated AI travel photo with DALL-E"
            }
        )

    except Exception as e:
        logger.error(f"Error generating image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate image: {str(e)}"
        )

@app.post("/api/generate-recommendations")
async def generate_recommendations(
    data: RecommendationsGenerationRequest,
    request: Request
):
    """Generate personalized recommendations using OpenAI API"""
    try:
        client_ip = get_client_ip(request)
        if not check_rate_limit(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

        # Use OpenAI to generate recommendations
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a travel expert. Generate personalized travel recommendations in JSON format."
                },
                {
                    "role": "user",
                    "content": data.prompt
                }
            ],
            temperature=0.7,
            max_tokens=4000
        )

        content = response.choices[0].message.content
        import json
        import re
        
        json_match = re.search(r'\{.*\}', content if content is not None else '', re.DOTALL)
        if json_match:
            recommendations_data = json.loads(json_match.group())
            recommendations = recommendations_data
        else:
            # Fallback recommendations
            recommendations = {
                "destinations": [
                    {
                        "id": "tokyo",
                        "name": "Tokyo",
                        "country": "Japan",
                        "continent": "Asia",
                        "description": "Perfect for your interests and budget",
                        "rating": 4.8,
                        "price": "$$$"
                    }
                ],
                "itinerary": [
                    {
                        "title": "Day 1: Arrival",
                        "activities": ["Check in", "Explore local area"]
                    }
                ]
            }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "recommendations": recommendations,
                "message": "Generated personalized recommendations"
            }
        )

    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )

@app.post("/api/filter-destinations")
async def filter_destinations(
    data: DestinationFilterRequest,
    request: Request
):
    """Filter destinations using OpenAI API"""
    try:
        client_ip = get_client_ip(request)
        if not check_rate_limit(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

        # Use OpenAI to filter destinations
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a travel expert. Filter destinations based on criteria in JSON format."
                },
                {
                    "role": "user",
                    "content": data.prompt
                }
            ],
            temperature=0.7,
            max_tokens=3000
        )

        content = response.choices[0].message.content
        import json
        import re
        
        json_match = re.search(r'\{.*\}', content if content is not None else '', re.DOTALL)
        if json_match:
            filter_data = json.loads(json_match.group())
            destinations = filter_data.get('destinations', [])
        else:
            # Fallback filtered destinations
            destinations = []

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "destinations": destinations,
                "message": "Filtered destinations based on criteria"
            }
        )

    except Exception as e:
        logger.error(f"Error filtering destinations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to filter destinations: {str(e)}"
        )

@app.post("/api/generate-destination-images")
async def generate_destination_images(
    data: DestinationImagesRequest,
    request: Request
):
    """Generate images for destinations using OpenAI DALL-E"""
    try:
        client_ip = get_client_ip(request)
        if not check_rate_limit(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

        images = {}
        
        # Generate images for each destination
        for destination in data.destinations[:5]:  # Limit to 5 to avoid rate limits
            try:
                response = openai_client.images.generate(
                    model="dall-e-3",
                    prompt=f"Beautiful travel photo of {destination.get('name', 'destination')} - {data.prompt}",
                    size="1024x1024",
                    quality="standard",
                    n=1
                )
                
                images[destination.get('name', 'Unknown')] = response.data[0].url
                
                # Small delay to avoid rate limits
                import time
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to generate image for {destination.get('name', 'Unknown')}: {e}")
                # Use fallback image
                images[destination.get('name', 'Unknown')] = f"https://source.unsplash.com/400x200/?{destination.get('name', 'travel')}"

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "images": images,
                "message": f"Generated images for {len(images)} destinations"
            }
        )

    except Exception as e:
        logger.error(f"Error generating destination images: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate destination images: {str(e)}"
        )

@app.post("/api/generate-detailed-itinerary")
async def generate_detailed_itinerary(
    data: dict,
    request: Request
):
    """Generate detailed itinerary with pricing using OpenAI"""
    import logging
    logger = logging.getLogger("uvicorn.error")
    
    try:
        client_ip = get_client_ip(request)
        check_rate_limit(client_ip)
        
        destination = data.get("destination", "Unknown")
        duration = data.get("duration", "7 days")
        budget_level = data.get("budget_level", "mid-range")
        travelers = data.get("travelers", 2)
        
        logger.info(f"Generating detailed itinerary for {destination}, {duration}, {budget_level} budget")
        
        prompt = f"""Generate a comprehensive travel itinerary for {destination} for {duration} with {travelers} travelers on a {budget_level} budget.

Please provide a detailed response in this exact JSON format:

{{
    "tripOverview": {{
        "title": "Trip title",
        "destination": "{destination}",
        "duration": "{duration}",
        "travelers": {travelers},
        "bestTime": "Best time to visit",
        "weather": "Typical weather",
        "summary": "Brief trip summary"
    }},
    "dailyItinerary": [
        {{
            "day": 1,
            "title": "Day title",
            "morning": ["Activity 1", "Activity 2"],
            "afternoon": ["Activity 3", "Activity 4"],
            "evening": ["Activity 5", "Activity 6"],
            "accommodation": "Hotel name",
            "meals": ["Breakfast", "Lunch", "Dinner"],
            "transportation": "Transport method"
        }}
    ],
    "budgetBreakdown": {{
        "accommodation": {{
            "total": 350,
            "perNight": 50,
            "type": "3-star hotel",
            "description": "Comfortable accommodation in city center"
        }},
        "meals": {{
            "total": 210,
            "perDay": 30,
            "breakdown": {{
                "breakfast": 8,
                "lunch": 12,
                "dinner": 10
            }}
        }},
        "activities": {{
            "total": 180,
            "breakdown": {{
                "sightseeing": 45,
                "adventures": 80,
                "cultural": 55
            }}
        }},
        "transportation": {{
            "total": 120,
            "breakdown": {{
                "airport_transfer": 25,
                "daily_transport": 95
            }}
        }},
        "miscellaneous": {{
            "total": 50,
            "breakdown": {{
                "tips": 20,
                "souvenirs": 30
            }}
        }},
        "totalTripCost": 910,
        "costPerPerson": 455,
        "currency": "USD"
    }},
    "travelTips": [
        {{
            "category": "Packing",
            "tips": ["Tip 1", "Tip 2", "Tip 3"]
        }},
        {{
            "category": "Local Customs", 
            "tips": ["Tip 1", "Tip 2", "Tip 3"]
        }},
        {{
            "category": "Safety",
            "tips": ["Tip 1", "Tip 2", "Tip 3"]
        }}
    ],
    "accommodations": [
        {{
            "name": "Hotel name",
            "type": "3-star",
            "location": "Location",
            "amenities": ["WiFi", "Pool", "Restaurant"],
            "price": "50/night",
            "rating": 4.2,
            "pros": ["Pro 1", "Pro 2"],
            "cons": ["Con 1", "Con 2"]
        }}
    ],
    "restaurants": [
        {{
            "name": "Restaurant name",
            "cuisine": "Local cuisine",
            "specialty": "Famous dish",
            "priceRange": "$$",
            "location": "Location",
            "rating": 4.5,
            "bestDishes": ["Dish 1", "Dish 2"],
            "reservationRequired": false
        }}
    ]
}}

IMPORTANT GUIDELINES:
1. Make all prices realistic for the destination and budget level
2. For budget level: "budget" = 60% of normal prices, "mid-range" = normal prices, "luxury" = 150% of normal prices
3. Adjust prices based on number of travelers
4. Include specific, realistic activities for the destination
5. Provide practical travel tips
6. Make accommodation and restaurant recommendations specific to the destination
7. Ensure all costs are in USD and realistic for the destination
8. Include seasonal considerations in pricing and recommendations"""

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert travel planner with deep knowledge of destinations worldwide. Provide accurate, realistic pricing and detailed itineraries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        logger.info(f"OpenAI response received for itinerary generation")
        
        # Parse JSON response with better error handling
        import re, json
        
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', content if content is not None else '', re.DOTALL)
        
        if json_match:
            json_content = json_match.group()
            
            # Try to fix common JSON issues
            try:
                itinerary_data = json.loads(json_content)
            except json.JSONDecodeError as e:
                logger.warning(f"Initial JSON parsing failed: {e}")
                
                # Try to fix trailing commas
                json_content = re.sub(r',(\s*[}\]])', r'\1', json_content)
                
                # Try to fix other common issues
                json_content = re.sub(r',\s*,', ',', json_content)  # Remove double commas
                json_content = re.sub(r',\s*}', '}', json_content)  # Remove trailing commas before }
                json_content = re.sub(r',\s*]', ']', json_content)  # Remove trailing commas before ]
                
                try:
                    itinerary_data = json.loads(json_content)
                    logger.info("Successfully parsed JSON after fixing trailing commas")
                except json.JSONDecodeError as e2:
                    logger.error(f"Failed to parse itinerary JSON even after fixes: {e2}")
                    logger.error(f"JSON content: {json_content[:500]}...")
                    
                    # Return a fallback itinerary
                    itinerary_data = {
                        "tripOverview": {
                            "title": f"{destination} Adventure",
                            "destination": destination,
                            "duration": duration,
                            "travelers": travelers,
                            "bestTime": "Year-round",
                            "weather": "Tropical",
                            "summary": f"An amazing {duration} adventure in {destination}!"
                        },
                        "dailyItinerary": [
                            {
                                "day": 1,
                                "title": "Arrival and Exploration",
                                "morning": ["Check into hotel", "Explore local area"],
                                "afternoon": ["Visit main attractions", "Local lunch"],
                                "evening": ["Dinner at local restaurant", "Evening stroll"],
                                "accommodation": "3-star hotel",
                                "meals": ["Breakfast", "Lunch", "Dinner"],
                                "transportation": "Local transport"
                            }
                        ],
                        "budgetBreakdown": {
                            "accommodation": {"total": 350, "perNight": 50, "type": "3-star hotel"},
                            "meals": {"total": 210, "perDay": 30},
                            "activities": {"total": 180},
                            "transportation": {"total": 120},
                            "miscellaneous": {"total": 50},
                            "totalTripCost": 910,
                            "costPerPerson": 455,
                            "currency": "USD"
                        },
                        "travelTips": [
                            {"category": "Packing", "tips": ["Pack light", "Bring sunscreen", "Comfortable shoes"]},
                            {"category": "Local Customs", "tips": ["Respect local culture", "Learn basic phrases", "Dress appropriately"]}
                        ],
                        "accommodations": [
                            {"name": "Local Hotel", "type": "3-star", "location": "City center", "price": "50/night"}
                        ],
                        "restaurants": [
                            {"name": "Local Restaurant", "cuisine": "Local", "priceRange": "$$"}
                        ]
                    }
            
            logger.info(f"Successfully generated detailed itinerary with {len(itinerary_data.get('dailyItinerary', []))} days")
            
            return {
                "success": True,
                "data": itinerary_data,
                "generated_at": datetime.now().isoformat()
            }
        else:
            logger.error(f"No JSON found in itinerary response")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate itinerary"
            )
            
    except Exception as e:
        logger.error(f"Error generating detailed itinerary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate itinerary: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,
        access_log=True,
        log_level="info"
    )
