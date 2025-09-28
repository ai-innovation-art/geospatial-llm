import os
import re
from dotenv import load_dotenv
from google import genai  # New GenAI client
from geopy.geocoders import Nominatim
import googlemaps
import time

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

# Initialize the GenAI client
client = genai.Client(api_key=gemini_api_key)

# Get model info and set up model
try:
    model_info = client.models.get(model="gemini-2.0-flash")
    print(f"✓ Using model: {model_info.name}")
    model_name = "gemini-2.0-flash"
except Exception as e:
    print(f"✗ gemini-2.0-flash failed: {e}")
    # Fallback to other models
    try:
        model_info = client.models.get(model="gemini-1.5-flash")
        print(f"✓ Using model: {model_info.name}")
        model_name = "gemini-1.5-flash"
    except Exception as e2:
        print(f"✗ gemini-1.5-flash failed: {e2}")
        raise Exception("Could not initialize any Gemini model")

# System prompt - kept from your original code
SYSTEM_PROMPT = """You are an advanced geospatial assistant specializing in location intelligence.

LOCATION FORMATTING RULES (HIGHEST PRIORITY):
- ANY geographical entity mentioned in your response MUST be formatted with [LOCATION] tags: [LOCATION]entity name, address details[/LOCATION]
- This includes but is not limited to: cities, neighborhoods, landmarks, businesses, streets, parks, buildings, monuments, natural features, etc.
- Format EACH distinct location separately with its own tags, even in lists or when locations are near each other
- Include precise details when possible: [LOCATION]Starbucks, FC Road, Shivajinagar, Pune[/LOCATION]
- For general areas: [LOCATION]Koregaon Park, Pune[/LOCATION]
- For cities/regions: [LOCATION]Pune, Maharashtra[/LOCATION]

RESPONSE QUALITY GUIDELINES:
- Use **bold formatting** for important information, headings, and key details
- Provide comprehensive, accurate information based on your knowledge
- Engage with both specific and general location queries with equal detail
- Structure complex responses (itineraries, comparisons) logically with clear sections
- For multi-day plans, clearly label days and timeframes
- Balance detail with readability - provide enough context for each recommendation

DATA FRESHNESS:
- Only use SerpAPI for queries requiring real-time data (current events, new businesses, etc.)
- Clearly indicate when information might need verification due to potential changes

EXAMPLES:
"I recommend visiting [LOCATION]Shaniwar Wada, Shivajinagar, Pune[/LOCATION] in the morning, followed by lunch at [LOCATION]Vaishali Restaurant, FC Road, Pune[/LOCATION]."

"The three best hospitals are [LOCATION]Ruby Hall Clinic, Sassoon Road, Pune[/LOCATION], [LOCATION]Jehangir Hospital, Sassoon Road, Pune[/LOCATION], and [LOCATION]Aditya Birla Memorial Hospital, Thergaon, Pimpri-Chinchwad[/LOCATION]."
"""

def run_query(user_input, history=None):
    # Compose prompt with system instructions and history
    prompt_parts = [SYSTEM_PROMPT]
    
    # Add conversation history if available
    if history is not None and len(history) > 0:
        prompt_parts.append("\nConversation History:")
        prompt_parts.extend(history[-4:])  # Last 4 responses
    
    prompt_parts.append(f"\nUser Query: {user_input}")
    full_prompt = "\n".join(prompt_parts)
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[{"parts": [{"text": full_prompt}]}]
        )
        return response.candidates[0].content.parts[0].text
    except Exception as e:
        print(f"Error generating content: {e}")
        return f"Sorry, I encountered an error: {str(e)}"

# Initialize Google Maps client
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
            # Ensure location format is correct for geocoding
            formatted_location = location.strip()
            
            # Get geocoding result from Google Maps
            geocode_result = gmaps.geocode(formatted_location)
            
            if geocode_result and len(geocode_result) > 0:
                # Extract location data from the first result
                location_data = geocode_result[0]['geometry']['location']
                coordinates[location] = (location_data['lat'], location_data['lng'])
            else:
                coordinates[location] = "Coordinates not found"
                
            # Optional: Add a small delay to respect rate limits if needed
            time.sleep(0.1)
            
        except Exception as e:
            coordinates[location] = f"Error: {e}"

    return coordinates

# Wrapper chatbot object for frontend compatibility (same interface as Agno)
class ChatbotWrapper:
    def __init__(self):
        self.conversation_history = []
    
    def run(self, user_input, history=None):
        # Use provided history or maintain internal history
        current_history = history if history is not None else self.conversation_history
        
        # Generate response
        raw_response = run_query(user_input, current_history)
        
        # Update internal history
        self.conversation_history.append(f"User: {user_input}")
        self.conversation_history.append(f"Assistant: {raw_response}")
        
        # Keep only last 8 entries (4 exchanges)
        if len(self.conversation_history) > 8:
            self.conversation_history = self.conversation_history[-8:]
        
        # Return response in same format as before
        class ContentObj:
            def __init__(self, content):
                self.content = content
        return ContentObj(raw_response)

chatbot = ChatbotWrapper()
