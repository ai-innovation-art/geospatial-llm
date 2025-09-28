import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from agent import chatbot, extract_locations, convert_to_coordinates
import re

app = Flask(__name__)
CORS(app)

# Add health check endpoint for Render
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy", 
        "message": "Geospatial LLM Backend is running!",
        "model": "Gemini 2.0 Flash"
    })

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400
    
    user_input = data['message']
    print(f"Received message: {user_input}")

    try:
        raw_response = chatbot.run(user_input).content
        print(f"Raw response from chatbot: {raw_response}")
        
        cleaned_response = re.sub(r'\[LOCATION\](.*?)\[/LOCATION\]', r'\1', raw_response)
        locations = extract_locations(raw_response)
        coordinates = convert_to_coordinates(locations)
        
        formatted_coordinates = [
            {"name": loc, "lat": coords[0], "lon": coords[1]}
            for loc, coords in coordinates.items() if isinstance(coords, tuple)
        ]
        
        return jsonify({
            "response": cleaned_response,
            "coordinates": formatted_coordinates
        })
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # PRODUCTION SETTINGS - This fixes the port binding issue
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)  # Change debug=False for production
