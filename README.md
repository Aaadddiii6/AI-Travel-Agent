
# AI Travel Agent

**AI Travel Agent** is an AI-powered travel planning platform that helps users discover destinations, generate personalized itineraries, visualize travel experiences with AI-generated images, and book flights, hotels, and activities. The backend is built with FastAPI and integrates with OpenAI, Hugging Face, Supabase, and Amadeus APIs.

---

## Features

- **Destination Discovery:**  
  Generate diverse and exciting travel destinations using AI (OpenAI GPT).

- **Personalized Recommendations:**  
  Get tailored travel suggestions and itineraries based on user preferences, interests, and budget.

- **AI-Powered Visualizations:**  
  Upload your photo and generate AI images of yourself at dream destinations using Hugging Face and DALL-E.

- **Booking System:**  
  Book flights, hotels, activities, and packages with real or mock data (Amadeus API integration).

- **Text-to-Image Generation:**  
  Create travel-themed images from text prompts using DALL-E or DeepAI.

- **Admin & Debug Endpoints:**  
  Health checks, environment debugging, and mock/demo modes for development.

---

## Project Structure

```
AI-Travel-Agent/
  backend/
    main.py                # FastAPI backend with all API endpoints
    requirements.txt       # Python dependencies
    static/uploads/        # Uploaded and generated images
    ...
  frontend/
    index.html             # Main frontend page
    js/                    # Frontend JavaScript files
    css/                   # Stylesheets
    ...
  Dockerfile
  README.md
  .env.example
```

---

## Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/AI-Travel-Agent.git
cd AI-Travel-Agent
```

### 2. Backend Setup

- **Python 3.9+** is required.
- Create a virtual environment and install dependencies:

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # On Windows
# or
source venv/bin/activate  # On Mac/Linux

pip install -r requirements.txt
```

- Copy `.env.example` to `.env` and fill in your API keys:

  - `OPENAI_API_KEY`
  - `HUGGINGFACE_TOKEN`
  - `SUPABASE_URL` and `SUPABASE_KEY` (optional)
  - `AMADEUS_CLIENT_ID` and `AMADEUS_CLIENT_SECRET` (optional)
  - `LIGHTX_API_KEY` (optional)
  - `FACE_SWAP_API_KEY` (optional)

### 3. Run the Backend

```bash
uvicorn backend.main:app --reload
```

The API will be available at [http://localhost:8000](http://localhost:8000).

### 4. Frontend

- Open `frontend/index.html` or other HTML files in your browser.
- The frontend communicates with the backend via REST API endpoints.

---

## API Endpoints

- `/api/destinations` — Get AI-generated travel destinations
- `/api/generate-visualization` — Generate AI travel photo with your face
- `/api/generate-personalized-recommendations` — Get personalized travel recommendations
- `/api/upload-photo` — Upload a user photo
- `/api/book` — Book flights, hotels, activities, or packages
- `/api/search-flights` — Search for flights (Amadeus or mock)
- `/api/search-hotels` — Search for hotels (Amadeus or mock)
- `/api/generate-text-to-image` — Generate images from text prompts
- `/api/generate-photo-app-image` — Generate images using the AI Photo App
- `/api/health` — Health check
- ...and more!

See the FastAPI docs at [http://localhost:8000/docs](http://localhost:8000/docs) for the full API.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```
OPENAI_API_KEY=your_openai_key
HUGGINGFACE_TOKEN=your_huggingface_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret
LIGHTX_API_KEY=your_lightx_api_key
FACE_SWAP_API_KEY=your_deepai_key
RENDER=false
```

---

## Deployment

- **Docker:**  
  Use the provided `Dockerfile` for containerized deployment.
- **Render.com:**  
  See `render.yaml` for Render deployment configuration.
- **Production:**  
  Set `RENDER=true` and update CORS origins in `main.py`.

---

## Notes

- If API keys are missing, the backend will use mock/demo data.
- For production, connect to real Supabase and Amadeus accounts.
- The AI image generation features require valid OpenAI and Hugging Face tokens.

---

## License

This project is licensed under the MIT License.

---

## Acknowledgements

- [OpenAI](https://openai.com/)
- [Hugging Face](https://huggingface.co/)
- [Supabase](https://supabase.com/)
- [Amadeus for Developers](https://developers.amadeus.com/)
- [Unsplash](https://unsplash.com/) (for mock images)

---

**Happy Travels! 🌍✈️**

---