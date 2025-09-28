import os
import re
from dotenv import load_dotenv
import google.generativeai as genai  # Gemini API
from geopy.geocoders import Nominatim
import googlemaps
import time  # Import time module for delay

# Load environment variables
load_dotenv()

# API keys
gemini_api_key = os.getenv("GEMINI_API_KEY")
serpapi_api_key = os.getenv("SERPAPI_KEY")
google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

if not google_maps_api_key:
    raise ValueError("GOOGLE_MAPS_API_KEY is missing! Please check your environment variables.")
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY is missing! Please check your environment variables.")
if not serpapi_api_key:
    raise ValueError("SERPAPI_KEY is missing! Please check your environment variables.")

# Configure Gemini API
genai.configure(api_key=gemini_api_key)

# Initialize Gemini model
gemini_model = genai.GenerativeModel("gemini-pro")

def run_query(user_input, history=None):
    # Compose prompt (optionally add history)
    prompt = user_input
    if history is not None and len(history) > 0:
        prompt = "\n".join(history[-4:] + [user_input])
    response = gemini_model.generate_content(prompt)
    return response.text if hasattr(response, "text") else response

# Initialize GeoPy Nominatim Geocoder
gmaps = googlemaps.Client(key=google_maps_api_key)

# Function to extract locations using the enforced format
def extract_locations(response_text: str) -> list:
    """Extract locations enclosed in [LOCATION] ... [/LOCATION]."""
    return list(set(re.findall(r'\[LOCATION\](.*?)\[/LOCATION\]', response_text)))

def convert_to_coordinates(locations: list) -> dict:
    """Convert location names to (latitude, longitude) using Google Maps Geocoding API."""
    coordinates = {}
    for location in locations:
        try:
            formatted_location = location.strip()
            geocode_result = gmaps.geocode(formatted_location)
            if geocode_result and len(geocode_result) > 0:
                location_data = geocode_result[0]['geometry']['location']
                coordinates[location] = (location_data['lat'], location_data['lng'])
            else:
                coordinates[location] = "Coordinates not found"
            time.sleep(0.1)  # Optional delay for rate limiting
        except Exception as e:
            coordinates[location] = f"Error: {e}"
    return coordinates

# Wrapper chatbot object for frontend compatibility
class ChatbotWrapper:
    def run(self, user_input, history=None):
        raw_response = run_query(user_input, history)
        class ContentObj:
            def __init__(self, content):
                self.content = content
        return ContentObj(raw_response)

chatbot = ChatbotWrapper()
