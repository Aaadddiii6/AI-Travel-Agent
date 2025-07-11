from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, field_validator
from supabase import create_client, Client
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
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Enhanced CORS for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=False,  # Set to False when using allow_origins=["*"]
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
    if amadeus_client_id and amadeus_client_secret:
        amadeus_client = AmadeusClient(
            client_id=amadeus_client_id,
            client_secret=amadeus_client_secret
        )
        logger.info("Amadeus client initialized successfully")
    else:
        logger.warning("Amadeus credentials not found")
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
async def generate_destinations_with_openai(continent: Optional[str] = None, limit: int = 6) -> List[dict]:
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
        if not content:
            logger.warning("OpenAI returned empty content")
            return []
            
        logger.info(f"OpenAI generated destinations: {content[:200]}...")
        
        # Try to extract JSON from the response
        import json
        import re
        
        # First, try to find JSON array in the response
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
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
        
        # If JSON parsing failed, try to extract individual destinations
        try:
            # Look for individual destination objects
            dest_matches = re.findall(r'\{[^{}]*"name"[^{}]*\}', content, re.DOTALL)
            if dest_matches:
                destinations_data = []
                for match in dest_matches:
                    try:
                        dest = json.loads(match)
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
                    except json.JSONDecodeError:
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

@app.get("/health")
async def health_check():
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "supabase": supabase is not None
        },
        "details": {
            "supabase_initialized": supabase is not None,
            "supabase_connected": False,
            "supabase_error": None
        }
    }
    
    # Check Supabase connection
    if supabase:
        try:
            # Simple query to test connection
            result = supabase.table("destinations").select("id").limit(1).execute()
            health_status["services"]["supabase"] = True
            health_status["details"]["supabase_connected"] = True
            health_status["details"]["destinations_count"] = len(result.data) if result.data else 0
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            health_status["services"]["supabase"] = False
            health_status["details"]["supabase_connected"] = False
            health_status["details"]["supabase_error"] = str(e)
            health_status["status"] = "degraded"
    else:
        health_status["details"]["supabase_error"] = "Supabase client not initialized"
    
    return health_status

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
    limit: int = 50
):
    try:
        # First try to get from database
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
                logger.warning(f"Database query failed, using OpenAI: {e}")
        
        # Use OpenAI to generate destinations
        try:
            openai_destinations = await generate_destinations_with_openai(continent, min(limit, 12))
            
            if openai_destinations:
                logger.info(f"Generated {len(openai_destinations)} destinations with OpenAI")
                return {
                    "success": True,
                    "data": openai_destinations,
                    "count": len(openai_destinations),
                    "continent": continent,
                    "limit": limit,
                    "source": "openai"
                }
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
        
        # Fallback to mock data
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
    try:
        # Rate limiting
        client_ip = get_client_ip(request)
        check_rate_limit(client_ip)
        
        logger.info(f"Generating personalized recommendations for {data.ageGroup} {data.groupSize} group with ${data.budgetRange} budget")
        
        # Create comprehensive prompt for OpenAI
        interests_text = ", ".join(data.interests)
        additional_context = f" Additional notes: {data.additionalNotes}" if data.additionalNotes else ""
        
        prompt = f"""Generate personalized travel recommendations for a {data.ageGroup} age group traveling as {data.groupSize} with a budget of ${data.budgetRange} for a {data.tripDuration} trip. Their interests include: {interests_text}.{additional_context}

Please provide a comprehensive response including:

1. 3-5 recommended destinations with detailed descriptions
2. A custom itinerary for the trip duration
3. Travel tips and recommendations
4. Budget breakdown

Format the response as a valid JSON object with this exact structure:
{{
    "destinations": [
        {{
            "name": "Destination Name",
            "country": "Country",
            "continent": "Continent", 
            "description": "Detailed description",
            "rating": 4.5,
            "price": "$$"
        }}
    ],
    "itinerary": [
        {{
            "title": "Day Title",
            "activities": ["Activity 1", "Activity 2", "Activity 3"]
        }}
    ],
    "travelTips": [
        "Tip 1",
        "Tip 2", 
        "Tip 3"
    ],
    "budgetBreakdown": {{
        "accommodation": 1200,
        "transportation": 800,
        "food": 600,
        "activities": 400,
        "total": 3000
    }}
}}

Make the recommendations realistic, exciting, and tailored to the specific preferences. Consider the age group, group size, budget, and interests when making suggestions."""

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
        if not content:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate recommendations"
            )
        
        # Try to extract JSON from the response
        try:
            # Find JSON content in the response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_content = content[start_idx:end_idx]
            import json
            recommendations = json.loads(json_content)
            
            # Validate the structure
            required_keys = ['destinations', 'itinerary', 'travelTips', 'budgetBreakdown']
            for key in required_keys:
                if key not in recommendations:
                    raise ValueError(f"Missing required key: {key}")
            
            logger.info(f"Successfully generated recommendations with {len(recommendations.get('destinations', []))} destinations")
            
            return {
                "success": True,
                "data": recommendations,
                "generated_at": datetime.now().isoformat()
            }
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            logger.error(f"Raw response: {content}")
            
            # Return fallback recommendations
            fallback_recommendations = {
                "destinations": [
                    {
                        "name": "Bali, Indonesia",
                        "country": "Indonesia",
                        "continent": "Asia",
                        "description": "Perfect for relaxation and cultural experiences with beautiful beaches and temples.",
                        "rating": 4.5,
                        "price": "$$"
                    },
                    {
                        "name": "Barcelona, Spain",
                        "country": "Spain", 
                        "continent": "Europe",
                        "description": "Great for food, culture, and architecture with vibrant nightlife.",
                        "rating": 4.3,
                        "price": "$$"
                    },
                    {
                        "name": "Costa Rica",
                        "country": "Costa Rica",
                        "continent": "North America", 
                        "description": "Ideal for adventure and nature with rainforests and beaches.",
                        "rating": 4.4,
                        "price": "$$"
                    }
                ],
                "itinerary": [
                    {
                        "title": "Day 1: Arrival and Exploration",
                        "activities": ["Check into hotel", "Local market visit", "Welcome dinner"]
                    },
                    {
                        "title": "Day 2: Cultural Immersion", 
                        "activities": ["Museum visit", "Local cooking class", "Evening entertainment"]
                    },
                    {
                        "title": "Day 3: Adventure Day",
                        "activities": ["Outdoor activity", "Scenic viewpoints", "Relaxation time"]
                    }
                ],
                "travelTips": [
                    "Book accommodations in advance for better rates",
                    "Pack according to the local climate",
                    "Learn basic local phrases for better experience",
                    "Keep copies of important documents"
                ],
                "budgetBreakdown": {
                    "accommodation": int(data.budgetRange * 0.4),
                    "transportation": int(data.budgetRange * 0.25),
                    "food": int(data.budgetRange * 0.2),
                    "activities": int(data.budgetRange * 0.15),
                    "total": data.budgetRange
                }
            }
            
            return {
                "success": True,
                "data": fallback_recommendations,
                "generated_at": datetime.now().isoformat(),
                "note": "Used fallback recommendations due to API parsing issue"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Personalized recommendations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate personalized recommendations: {str(e)}"
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
            
            prompt = f"""Given the user input "{query}", suggest 8 popular travel destinations (cities, countries, or regions) that match or are related to this query. 

Return only a JSON array of strings with destination names in this exact format:
["Destination 1", "Destination 2", "Destination 3", ...]

Examples:
- For "par" → ["Paris, France", "Barcelona, Spain", "Milan, Italy", "Bangkok, Thailand", "Mumbai, India", "Buenos Aires, Argentina", "Cairo, Egypt", "Osaka, Japan"]
- For "tok" → ["Tokyo, Japan", "Toronto, Canada", "Stockholm, Sweden", "Istanbul, Turkey", "Bangkok, Thailand", "Moscow, Russia", "Seoul, South Korea", "Melbourne, Australia"]
- For "beach" → ["Bali, Indonesia", "Maldives", "Hawaii, USA", "Santorini, Greece", "Phuket, Thailand", "Cancun, Mexico", "Fiji", "Seychelles"]

Focus on popular, well-known destinations that travelers would actually search for."""
            
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            import re
            
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                suggestions = json.loads(json_match.group())
                logger.info(f"OpenAI suggestions: {suggestions}")
                return {"suggestions": suggestions[:8]}
            else:
                raise Exception("Invalid JSON response from OpenAI")
                
        except Exception as openai_error:
            logger.warning(f"OpenAI suggestions failed: {openai_error}")
            
            # Fallback to static suggestions
            static_suggestions = {
                'par': ['Paris, France', 'Barcelona, Spain', 'Milan, Italy', 'Bangkok, Thailand'],
                'tok': ['Tokyo, Japan', 'Toronto, Canada', 'Stockholm, Sweden', 'Istanbul, Turkey'],
                'lon': ['London, UK', 'Los Angeles, USA', 'Lyon, France', 'Lima, Peru'],
                'new': ['New York, USA', 'New Delhi, India', 'Newcastle, UK', 'New Orleans, USA'],
                'san': ['San Francisco, USA', 'Santorini, Greece', 'Santiago, Chile', 'San Diego, USA'],
                'dub': ['Dubai, UAE', 'Dublin, Ireland', 'Dubrovnik, Croatia', 'Durban, South Africa'],
                'bea': ['Bali, Indonesia', 'Barcelona, Spain', 'Bangkok, Thailand', 'Berlin, Germany'],
                'rom': ['Rome, Italy', 'Roma, Italy', 'Romania', 'Romantic destinations'],
                'sea': ['Seattle, USA', 'Seoul, South Korea', 'Seattle, USA', 'Seville, Spain'],
                'chi': ['Chicago, USA', 'China', 'Chile', 'Chiang Mai, Thailand']
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
                    'Singapore', 'Sydney, Australia', 'Amsterdam, Netherlands', 'Prague, Czech Republic'
                ]
                suggestions = [dest for dest in popular_destinations if query.lower() in dest.lower()]
            
            return {"suggestions": suggestions[:8]}
    
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
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            import re
            
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
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
        
        if not amadeus_client:
            raise HTTPException(
                status_code=503,
                detail="Flight search service is currently unavailable"
            )
        
        # Search for flights
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
        
        return {
            "success": True,
            "flights": flights,
            "count": len(flights)
        }
        
    except ResponseError as e:
        logger.error(f"Amadeus API error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Flight search error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Flight search error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during flight search"
        )

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
    
    try:
        client = Client("multimodalart/Ip-Adapter-FaceID", hf_token=token)
        result = client.predict(
            images=[handle_file(str(selfie_path))],
            prompt=prompt if prompt else "",
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
        uploads_dir = Path(__file__).parent / "static" / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        for i, item in enumerate(result):
            if item and isinstance(item, dict) and "image" in item and item["image"]:
                image_path = item["image"]
                dest_filename = f"generated_{i+1}_{os.path.basename(image_path)}"
                dest_path = uploads_dir / dest_filename
                shutil.copy(image_path, dest_path)
                image_urls.append(f"/static/uploads/{dest_filename}")
        if not image_urls:
            raise ValueError("No images found in result")
        return image_urls
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Hugging Face API error: {error_msg}")
        
        # Check if it's an authentication error
        if "401" in error_msg or "Unauthorized" in error_msg or "Invalid credentials" in error_msg:
            logger.warning("Hugging Face token is invalid or expired, using fallback")
            return generate_fallback_images(prompt)
        
        # For other errors, try fallback
        logger.warning(f"Hugging Face API failed: {error_msg}, using fallback")
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
        # Create a travel-themed prompt if the original is empty
        if not prompt or prompt.strip() == "":
            prompt = "A person enjoying a beautiful travel destination, high quality, photorealistic"
        else:
            # Enhance the prompt for better results
            prompt = f"A person enjoying {prompt}, high quality, photorealistic, travel photography"
        
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        if response.data and len(response.data) > 0:
            image_url = response.data[0].url
            # Download and save the image
            uploads_dir = Path(__file__).parent / "static" / "uploads"
            uploads_dir.mkdir(exist_ok=True)
            
            # Download the image
            img_response = requests.get(image_url)
            if img_response.status_code == 200:
                filename = f"dalle_generated_{int(time.time())}.png"
                filepath = uploads_dir / filename
                with open(filepath, "wb") as f:
                    f.write(img_response.content)
                return [f"/static/uploads/{filename}"]
        
        raise Exception("DALL-E API returned no images")
    except Exception as e:
        logger.error(f"DALL-E generation failed: {e}")
        raise

def generate_mock_images(prompt: str) -> list[str]:
    """Generate mock travel images using Unsplash"""
    try:
        # Create a search query based on the prompt
        if not prompt or prompt.strip() == "":
            search_query = "travel"
        else:
            # Extract key words from prompt for search
            words = prompt.lower().split()
            travel_keywords = ["travel", "vacation", "trip", "destination", "beach", "mountain", "city", "landscape"]
            search_terms = [word for word in words if word in travel_keywords]
            search_query = " ".join(search_terms) if search_terms else "travel"
        
        # Use Unsplash API or direct URLs for mock images
        mock_images = [
            "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&q=80",
            "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800&h=600&fit=crop&q=80",
            "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&h=600&fit=crop&q=80"
        ]
        
        # Download and save mock images
        uploads_dir = Path(__file__).parent / "static" / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        
        image_urls = []
        for i, mock_url in enumerate(mock_images):
            try:
                img_response = requests.get(mock_url)
                if img_response.status_code == 200:
                    filename = f"mock_generated_{i+1}_{int(time.time())}.jpg"
                    filepath = uploads_dir / filename
                    with open(filepath, "wb") as f:
                        f.write(img_response.content)
                    image_urls.append(f"/static/uploads/{filename}")
            except Exception as e:
                logger.error(f"Failed to download mock image {i+1}: {e}")
                continue
        
        if not image_urls:
            # If all downloads fail, return placeholder URLs
            return [
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&q=80",
                "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800&h=600&fit=crop&q=80"
            ]
        
        return image_urls
    except Exception as e:
        logger.error(f"Mock image generation failed: {e}")
        # Return placeholder URLs as last resort
        return [
            "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&q=80",
            "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800&h=600&fit=crop&q=80"
        ]

@app.post("/api/generate-photo-app-image")
async def generate_photo_app_image(
    selfie: UploadFile = File(...),
    prompt: str = Form(...)
):
    try:
        uploads_dir = Path(__file__).parent / "static" / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        filename = selfie.filename or "uploaded.jpg"
        upload_path = uploads_dir / filename
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(selfie.file, buffer)
        safe_prompt = prompt.strip() if prompt is not None and isinstance(prompt, str) else ""
        image_urls = generate_ai_image(upload_path, safe_prompt)
        return {"success": True, "image_urls": image_urls}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
# --- End: AI Photo App Integration ---

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
