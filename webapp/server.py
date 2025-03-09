
from flask import Flask, send_from_directory, jsonify
import json
import os

app = Flask(__name__)

# Path to historical data JSON file
HISTORY_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              "history_db_generator/russian_history_database.json")

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def send_file(path):
    return send_from_directory('.', path)

@app.route('/api/historical-events')
def get_historical_events():
    try:
        with open(HISTORY_DB_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Extract events from the database
        events = data.get('events', [])
        
        # Return only needed fields to minimize payload
        filtered_events = []
        for event in events:
            # Skip events without location
            if 'location' not in event:
                continue
                
            filtered_event = {
                'id': event.get('id', ''),
                'title': event.get('title', ''),
                'date': event.get('date', ''),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'category': event.get('category', ''),
                'topic': event.get('topic', '')
            }
            filtered_events.append(filtered_event)
            
        return jsonify(filtered_events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
