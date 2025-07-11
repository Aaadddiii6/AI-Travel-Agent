#!/bin/bash

# Create static directory if it doesn't exist
mkdir -p static/uploads

# Start the FastAPI application
uvicorn main:app --host 0.0.0.0 --port $PORT 