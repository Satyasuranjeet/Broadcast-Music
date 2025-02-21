from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import json
import queue
import threading
from collections import defaultdict

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["https://broadcast-music-gqhx.vercel.app", "https://broadcast-music.vercel.app"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

# Store rooms and their event queues
rooms = {}
room_queues = defaultdict(lambda: defaultdict(queue.Queue))

@app.route('/')
def index():
    return "Music Broadcast Server Running"

@app.route('/api/create-room', methods=['POST'])
def create_room():
    data = request.json
    room_id = data['roomId']
    username = data.get('username', 'Anonymous')
    
    if room_id not in rooms:
        rooms[room_id] = {
            'current_track': '',
            'is_playing': False,
            'current_time': 0,
            'users': [username]
        }
        return jsonify({'success': True, 'roomId': room_id})
    return jsonify({'success': False, 'message': 'Room already exists'})

@app.route('/api/join-room', methods=['POST'])
def join_room():
    data = request.json
    room_id = data['roomId']
    username = data.get('username', 'Anonymous')
    
    if room_id in rooms:
        rooms[room_id]['users'].append(username)
        # Broadcast user joined event to all clients in the room
        broadcast_to_room(room_id, {
            'type': 'user_joined',
            'data': {'username': username}
        })
        return jsonify({
            'success': True,
            'currentState': rooms[room_id]
        })
    return jsonify({'success': False, 'message': 'Room not found'})

@app.route('/api/set-music', methods=['POST'])
def set_music():
    data = request.json
    room_id = data['roomId']
    
    if room_id in rooms:
        rooms[room_id]['current_track'] = data['track']
        rooms[room_id]['is_playing'] = False
        rooms[room_id]['current_time'] = 0
        
        broadcast_to_room(room_id, {
            'type': 'music_state',
            'data': {
                'track': data['track'],
                'isPlaying': False,
                'currentTime': 0
            }
        })
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Room not found'})

@app.route('/api/play-pause', methods=['POST'])
def play_pause():
    data = request.json
    room_id = data['roomId']
    
    if room_id in rooms:
        rooms[room_id]['is_playing'] = data['isPlaying']
        rooms[room_id]['current_time'] = data['currentTime']
        
        broadcast_to_room(room_id, {
            'type': 'music_state',
            'data': {
                'track': rooms[room_id]['current_track'],
                'isPlaying': data['isPlaying'],
                'currentTime': data['currentTime']
            }
        })
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Room not found'})

@app.route('/api/events')
def events():
    room_id = request.args.get('roomId')
    client_id = request.args.get('clientId')
    
    if room_id not in rooms:
        return jsonify({'error': 'Room not found'}), 404

    def generate():
        client_queue = room_queues[room_id][client_id]
        while True:
            try:
                # Get message from queue
                message = client_queue.get(timeout=30)
                yield f"data: {json.dumps(message)}\n\n"
            except queue.Empty:
                # Send keepalive
                yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

def broadcast_to_room(room_id, message):
    if room_id in room_queues:
        for client_queue in room_queues[room_id].values():
            client_queue.put(message)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)