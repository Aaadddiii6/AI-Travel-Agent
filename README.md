# AI Travel Agent

An AI-powered travel booking and visualization application that lets you search for flights and hotels, see yourself in amazing destinations around the world, and get intelligent travel recommendations with booking capabilities.

## 🎯 **NEW: Flight & Hotel Booking Now Live!**

- ✅ **Flight Search**: Real-time flight search using Amadeus API
- ✅ **Hotel Search**: Hotel booking with intelligent fallback data
- ✅ **AI Photo Generation**: See yourself in travel destinations
- ✅ **Smart Recommendations**: AI-powered travel suggestions
- ✅ **Complete Booking System**: End-to-end booking flow
- ✅ **Production Ready**: Fully deployable to Render

## 🌐 Live Demo

- **Frontend**: https://ai-travel-agent-frontend.onrender.com
- **Backend API**: https://ai-travel-agent-backend.onrender.com
- **API Documentation**: https://ai-travel-agent-backend.onrender.com/docs

## 🚀 Quick Start

### Option 1: Easy Start (Recommended)

```bash
./start-app.sh
```

This will automatically:

- Check dependencies
- Start the backend server (port 8000)
- Start the frontend server (port 5000)
- Open the app in your browser

### Option 2: Manual Start

#### 1. Install Dependencies

```bash
# Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..
```

#### 2. Start Backend Server

```bash
cd backend
python main.py
```

Backend will be available at: http://localhost:8000

#### 3. Start Frontend Server (in a new terminal)

```bash
   cd frontend
   python3 -m http.server 3000
```

Frontend will be available at: http://localhost:3000

## 📱 App Pages

- **Homepage**: http://localhost:5000/index.html
- **Upload Photo**: http://localhost:5000/upload.html
- **Destinations**: http://localhost:5000/destinations.html
- **Visualizations**: http://localhost:5000/visualizations.html
- **Recommendations**: http://localhost:5000/recommendations.html
- **Booking**: http://localhost:5000/booking.html
- **Test Data**: http://localhost:5000/test-data.html

## 🔧 Features

### Frontend

- ✅ Modern, responsive UI with Tailwind CSS
- ✅ **Flight & Hotel Search**: Real-time search with autocomplete
- ✅ **Booking System**: Complete booking flow for flights and hotels
- ✅ Drag & drop photo upload with AI face swap technology
- ✅ Destination browsing with search and filters
- ✅ AI-powered travel recommendations
- ✅ Interactive booking system with dual currency display
- ✅ Visualization gallery with before/after comparisons
- ✅ Toast notifications and loading states
- ✅ Mobile-friendly design
- ✅ Real-time API integration

### Backend

- ✅ FastAPI REST API with comprehensive endpoints
- ✅ **Amadeus API Integration**: Real-time flight and hotel search
- ✅ **Intelligent Fallbacks**: Graceful degradation when APIs fail
- ✅ Photo upload and AI image generation processing
- ✅ Destination data management with Supabase
- ✅ OpenAI integration for intelligent recommendations
- ✅ Booking system with data persistence
- ✅ CORS support for cross-origin requests
- ✅ Health check and debug endpoints
- ✅ Environment-based configuration
- ✅ **Production Ready**: Optimized for Render deployment

## 🛠️ Technology Stack

### Frontend

- HTML5, CSS3, JavaScript (Vanilla)
- Tailwind CSS for styling
- Font Awesome icons
- Responsive design
- Chart.js for data visualizations

### Backend

- Python 3.11+
- FastAPI framework
- Uvicorn ASGI server
- **Amadeus API** for flight and hotel search
- OpenAI API integration (DALL-E for image generation)
- Hugging Face API for AI image generation
- Supabase database (PostgreSQL)
- Pillow for image processing
- **Production deployment** with Render

## 📁 Project Structure

```
Travel-Agent/
├── frontend/                 # Frontend files
│   ├── index.html           # Homepage
│   ├── upload.html          # Photo upload page
│   ├── destinations.html    # Destinations page
│   ├── visualizations.html  # Visualizations page
│   ├── recommendations.html # AI recommendations page
│   ├── booking.html         # Booking system page
│   ├── test-data.html       # Test data page
│   ├── css/
│   │   ├── style.css        # Main stylesheet
│   │   └── booking.css      # Booking page styles
│   └── js/
│       ├── api.js           # API service
│       ├── components.js    # UI components
│       ├── main.js          # Main app logic
│       ├── upload.js        # Upload page logic
│       ├── destinations.js  # Destinations page logic
│       ├── visualizations.js # Visualizations page logic
│       ├── recommendations.js # Recommendations logic
│       ├── booking.js       # Booking system logic
│       └── ui.js            # UI utilities
├── backend/                  # Backend files
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── insert_destinations.py # Database seeding
├── setup_supabase_database.py # Database setup script
├── setup_supabase_database.sql # SQL schema
├── apply_supabase_policies.py # Database policies
├── start-app.sh             # Startup script
├── start-frontend.sh        # Frontend startup script
├── start.sh                 # Main startup script
└── README.md                # This file
```

## 🔑 Environment Setup

### Local Development

1. Copy the environment template:

   ```bash
   cp backend/env.example backend/.env
   ```

2. Edit `backend/.env` and add your actual API keys:

   ```env
   # Supabase Configuration
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_KEY=your_supabase_anon_key

   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key_here

   # Hugging Face Token
   HUGGINGFACE_TOKEN=your_huggingface_token_here

   # LightX API Configuration
   LIGHTX_API_KEY=your_lightx_api_key_here

   # Face Swap API Key
   FACE_SWAP_API_KEY=your_face_swap_api_key_here

   # Amadeus API Configuration
   AMADEUS_CLIENT_ID=your_amadeus_client_id_here
   AMADEUS_CLIENT_SECRET=your_amadeus_client_secret_here

   # API Configuration
   API_HOST=127.0.0.1
   API_PORT=8000
   DEBUG=False

   # CORS Configuration
   ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5000,https://ai-travel-agent-frontend.onrender.com
   ```

**⚠️ Security Note**: Never commit your `.env` file to version control. It's already included in `.gitignore`.

### Production Deployment (Render)

Set these environment variables in your Render dashboard:

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon/public key
- `OPENAI_API_KEY`: Your OpenAI API key
- `HUGGINGFACE_TOKEN`: Your Hugging Face token
- `AMADEUS_CLIENT_ID`: Your Amadeus API client ID
- `AMADEUS_CLIENT_SECRET`: Your Amadeus API client secret
- `LIGHTX_API_KEY`: Your LightX API key
- `FACE_SWAP_API_KEY`: Your Face Swap API key
- `RENDER`: true (for production CORS)
- `API_HOST`: 0.0.0.0 (for Render)
- `API_PORT`: 10000 (Render's default port)
- `DEBUG`: False

## 🗄️ Database Setup

### Supabase Database

The application requires a Supabase database with the following tables:

- `destinations` - Travel destinations data
- `visualizations` - Generated travel images
- `bookings` - User booking information
- `recommendations` - AI-generated recommendations

Run the setup scripts to initialize your database:

```bash
# Setup database schema and policies
python setup_supabase_database.py

# Insert sample destinations
python backend/insert_destinations.py
```

## 🧪 Testing

### Test Data Loading

Visit http://localhost:5000/test-data.html to test:

- Backend health check
- Destinations data loading
- Continents data loading
- Visualizations data loading
- Supabase connection status

### Flight & Hotel Booking Testing

Visit http://localhost:5000/booking.html to test:

- Flight search with real-time results
- Hotel search with fallback data
- Booking system functionality
- Dual currency display (USD/INR)
- Autocomplete for airports and cities

### API Documentation

Visit http://localhost:8000/docs for interactive API documentation.

### Debug Endpoints

- Health check: `GET /health`
- Debug info: `GET /debug`
- Hotel endpoint test: `GET /api/test-hotels`
- Environment check: `GET /env-check`

## 🐛 Troubleshooting

### Common Issues

1. **Port already in use**

   - Backend: Change port in `backend/main.py`

2. **Flight/Hotel Search Issues**

   - Ensure Amadeus API credentials are set correctly
   - Check that city codes are valid (e.g., "DEL" for Delhi, "NYC" for New York)
   - Hotel search may show fallback data for unavailable properties (this is normal)

3. **Image Generation Issues**

   - Ensure Hugging Face token is valid
   - Check that static directory exists: `backend/backend/static/uploads/`
   - Images are generated with unique timestamps to prevent caching issues
   - Frontend: Use different port: `python3 -m http.server 5001`

4. **Dependencies not found**

   - Run: `pip install -r backend/requirements.txt`

5. **Backend not starting**

   - Check if virtual environment is activated
   - Verify all dependencies are installed
   - Check console for error messages

6. **Frontend not loading data**

   - Ensure backend is running on port 8000
   - Check browser console for CORS errors
   - Verify API endpoints are accessible

7. **Supabase connection issues**

   - Verify environment variables are set correctly
   - Check Supabase project status
   - Ensure database tables exist

8. **Render deployment issues**
   - Verify environment variables in Render dashboard
   - Check build logs for dependency issues
   - Ensure proper port configuration (10000 for Render)

### Debug Mode

To run in debug mode, set `DEBUG=True` in your `.env` file.

## 🔒 Security

### API Key Management

- **Never commit API keys to version control**
- Use environment variables for all sensitive configuration
- The `.env` file is automatically ignored by Git
- Regenerate any exposed API keys immediately

### Required API Keys

- **OpenAI API Key**: For AI-powered recommendations and image generation
- **Hugging Face Token**: For face swap and image processing
- **Supabase Keys**: For database operations
- **LightX API Key**: For advanced image editing
- **Face Swap API Key**: For face swap functionality

### Security Best Practices

1. Use strong, unique API keys
2. Regularly rotate your API keys
3. Monitor API usage for unusual activity
4. Use environment variables in production
5. Never log or display API keys in application output

## 🚀 Deployment

The project is fully optimized for Render deployment with complete configuration files:

### Automatic Deployment (Recommended)

1. **Push to GitHub**
2. **Connect repository to Render**
3. **Use the provided `render.yaml` configuration**
4. **Set environment variables in Render dashboard**

### Manual Configuration

1. **Backend**: Deploy as a Python service

   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Environment: Python 3.11
   - Port: 10000

2. **Frontend**: Deploy as a static site
   - Build Command: None required
   - Publish Directory: `frontend/`

### Deployment Files Included

- `render.yaml` - Render deployment configuration
- `Dockerfile` - Container deployment option
- `DEPLOYMENT.md` - Complete deployment guide
- `backend/start.sh` - Startup script

### Environment Variables

Ensure all required environment variables are set in your Render dashboard for both services.

## 📄 License

This project is for educational purposes.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**Happy Traveling! ✈️🌍**
