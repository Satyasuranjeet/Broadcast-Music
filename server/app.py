from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import json
import queue
import os
import uuid
from collections import defaultdict
from werkzeug.serving import WSGIRequestHandler

app = Flask(__name__)
CORS(app)

# Store rooms and queues
rooms = {}
room_queues = defaultdict(lambda: defaultdict(queue.Queue))

# Get port from environment variable with a default of 10000 (Render's requirement)
port = int(os.environ.get('PORT', 10000))

@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>Music Broadcast</title>
            <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
            <style>
                .gradient-bg {
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                }
                .glass-effect {
                    background: rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }
                .input-style {
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    transition: all 0.3s ease;
                }
                .input-style:focus {
                    background: rgba(255, 255, 255, 0.1);
                    border-color: rgba(255, 255, 255, 0.3);
                    outline: none;
                }
                .btn-primary {
                    background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                    transition: all 0.3s ease;
                }
                .btn-primary:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(76, 175, 80, 0.3);
                }
                .btn-secondary {
                    background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
                    transition: all 0.3s ease;
                }
                .btn-secondary:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(52, 152, 219, 0.3);
                }
                @keyframes pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                    100% { transform: scale(1); }
                }
                .pulse {
                    animation: pulse 2s infinite;
                }
            </style>
        </head>
        <body class="gradient-bg min-h-screen text-white font-sans">
            <div class="container mx-auto px-4 py-8 max-w-2xl">
                <div class="glass-effect rounded-xl p-8 shadow-2xl">
                    <h1 class="text-4xl font-bold text-center mb-8 bg-clip-text text-transparent bg-gradient-to-r from-green-400 to-blue-500">
                        Music Broadcast
                    </h1>
                    
                    <div id="message" class="hidden mb-6 p-4 rounded-lg text-center"></div>
                    
                    <div id="controls" class="space-y-4">
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-300">Username</label>
                            <input type="text" id="username" placeholder="Enter your username" 
                                class="w-full px-4 py-2 rounded-lg input-style text-white">
                        </div>
                        
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-300">Room ID</label>
                            <input type="text" id="roomId" placeholder="Enter room ID" 
                                class="w-full px-4 py-2 rounded-lg input-style text-white">
                        </div>
                        
                        <div class="grid grid-cols-2 gap-4 mt-6">
                            <button onclick="createRoom()" 
                                class="btn-primary px-6 py-3 rounded-lg font-semibold">
                                Create Room
                            </button>
                            <button onclick="joinRoom()" 
                                class="btn-secondary px-6 py-3 rounded-lg font-semibold">
                                Join Room
                            </button>
                        </div>
                    </div>
                    
                    <div id="musicControls" class="hidden space-y-6 mt-8">
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-300">Music URL</label>
                            <input type="text" id="musicUrl" placeholder="Enter music URL" 
                                class="w-full px-4 py-2 rounded-lg input-style text-white">
                        </div>
                        
                        <div class="grid grid-cols-2 gap-4">
                            <button onclick="setMusic()" 
                                class="btn-primary px-6 py-3 rounded-lg font-semibold">
                                Set Music
                            </button>
                            <button onclick="togglePlay()" id="playPauseBtn"
                                class="btn-secondary px-6 py-3 rounded-lg font-semibold">
                                Play
                            </button>
                        </div>
                        
                        <div class="mt-6">
                            <audio id="audio" controls class="w-full"></audio>
                        </div>
                        
                        <div id="users" class="mt-6">
                            <h3 class="text-xl font-semibold mb-3">Connected Users</h3>
                            <ul id="userList" class="list-disc list-inside text-gray-300"></ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
                let isPlaying = false;
                let currentRoom = '';
                
                function showMessage(msg, isError = false) {
                    const messageEl = document.getElementById('message');
                    messageEl.textContent = msg;
                    messageEl.className = `mb-6 p-4 rounded-lg text-center ${isError ? 'bg-red-500/20' : 'bg-green-500/20'}`;
                    messageEl.style.display = 'block';
                    setTimeout(() => {
                        messageEl.style.display = 'none';
                    }, 5000);
                }

                async function createRoom() {
                    const username = document.getElementById('username').value;
                    const roomId = document.getElementById('roomId').value;
                    
                    if (!username || !roomId) {
                        showMessage('Please fill in all fields', true);
                        return;
                    }
                    
                    try {
                        const response = await fetch('/create-room', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({username, roomId})
                        });
                        
                        const data = await response.json();
                        if (data.success) {
                            currentRoom = roomId;
                            document.getElementById('musicControls').style.display = 'block';
                            document.getElementById('controls').style.display = 'none';
                            showMessage('Room created successfully!');
                            connectToEvents();
                            updateUserList([username]);
                        } else {
                            showMessage(data.message || 'Failed to create room', true);
                        }
                    } catch (error) {
                        showMessage('Error creating room', true);
                    }
                }

                async function joinRoom() {
                    const username = document.getElementById('username').value;
                    const roomId = document.getElementById('roomId').value;
                    
                    if (!username || !roomId) {
                        showMessage('Please fill in all fields', true);
                        return;
                    }
                    
                    try {
                        const response = await fetch('/join-room', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({username, roomId})
                        });
                        
                        const data = await response.json();
                        if (data.success) {
                            currentRoom = roomId;
                            document.getElementById('musicControls').style.display = 'block';
                            document.getElementById('controls').style.display = 'none';
                            showMessage('Joined room successfully!');
                            connectToEvents();
                        } else {
                            showMessage('Room not found', true);
                        }
                    } catch (error) {
                        showMessage('Error joining room', true);
                    }
                }

                async function setMusic() {
                    const musicUrl = document.getElementById('musicUrl').value;
                    
                    if (!musicUrl) {
                        showMessage('Please enter a music URL', true);
                        return;
                    }
                    
                    try {
                        const response = await fetch('/set-music', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({roomId: currentRoom, track: musicUrl})
                        });
                        
                        if ((await response.json()).success) {
                            showMessage('Music updated successfully!');
                        }
                    } catch (error) {
                        showMessage('Error setting music', true);
                    }
                }

                async function togglePlay() {
                    const audio = document.getElementById('audio');
                    const playPauseBtn = document.getElementById('playPauseBtn');
                    isPlaying = !isPlaying;
                    playPauseBtn.textContent = isPlaying ? 'Pause' : 'Play';
                    
                    try {
                        await fetch('/play-pause', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                roomId: currentRoom,
                                isPlaying,
                                currentTime: audio.currentTime
                            })
                        });
                    } catch (error) {
                        showMessage('Error updating playback state', true);
                    }
                }

                function updateUserList(users) {
                    const userList = document.getElementById('userList');
                    userList.innerHTML = users.map(user => `
                        <li class="mb-2 flex items-center">
                            <span class="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                            ${user}
                        </li>
                    `).join('');
                }

                function connectToEvents() {
                    const events = new EventSource(`/events?roomId=${currentRoom}`);
                    
                    events.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        
                        if (data.type === 'music_state') {
                            const audio = document.getElementById('audio');
                            const playPauseBtn = document.getElementById('playPauseBtn');
                            
                            audio.src = data.data.track;
                            audio.currentTime = data.data.currentTime;
                            
                            if (data.data.isPlaying) {
                                audio.play();
                                isPlaying = true;
                                playPauseBtn.textContent = 'Pause';
                            } else {
                                audio.pause();
                                isPlaying = false;
                                playPauseBtn.textContent = 'Play';
                            }
                        } else if (data.type === 'user_joined') {
                            showMessage(`${data.data.username} joined the room!`);
                            if (data.data.users) {
                                updateUserList(data.data.users);
                            }
                        }
                    };
                    
                    events.onerror = () => {
                        showMessage('Connection lost. Reconnecting...', true);
                    };
                }
            </script>
        </body>
    </html>
    """  # Note: The full HTML content remains unchanged from the previous version

@app.route('/create-room', methods=['POST'])
def create_room():
    data = request.json
    room_id = data['roomId']
    username = data.get('username', 'Anonymous')
    
    if room_id not in rooms:
        rooms[room_id] = {
            'track': '',
            'isPlaying': False,
            'currentTime': 0,
            'users': [username]
        }
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Room already exists'})

@app.route('/join-room', methods=['POST'])
def join_room():
    data = request.json
    room_id = data['roomId']
    username = data.get('username', 'Anonymous')
    
    if room_id in rooms:
        rooms[room_id]['users'].append(username)
        broadcast_to_room(room_id, {
            'type': 'user_joined',
            'data': {
                'username': username,
                'users': rooms[room_id]['users']
            }
        })
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/set-music', methods=['POST'])
def set_music():
    data = request.json
    room_id = data['roomId']
    
    if room_id in rooms:
        rooms[room_id]['track'] = data['track']
        rooms[room_id]['isPlaying'] = False
        rooms[room_id]['currentTime'] = 0
        
        broadcast_to_room(room_id, {
            'type': 'music_state',
            'data': {
                'track': data['track'],
                'isPlaying': False,
                'currentTime': 0
            }
        })
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/play-pause', methods=['POST'])
def play_pause():
    data = request.json
    room_id = data['roomId']
    
    if room_id in rooms:
        rooms[room_id]['isPlaying'] = data['isPlaying']
        rooms[room_id]['currentTime'] = data['currentTime']
        
        broadcast_to_room(room_id, {
            'type': 'music_state',
            'data': {
                'track': rooms[room_id]['track'],
                'isPlaying': data['isPlaying'],
                'currentTime': data['currentTime']
            }
        })
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/events')
def events():
    room_id = request.args.get('roomId')
    client_id = request.args.get('clientId', str(uuid.uuid4()))
    
    if room_id not in rooms:
        return jsonify({'error': 'Room not found'}), 404

    def generate():
        client_queue = room_queues[room_id][client_id]
        try:
            while True:
                # Get message from queue with timeout
                try:
                    message = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(message)}\n\n"
                except queue.Empty:
                    # Send keepalive ping
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        except GeneratorExit:
            # Clean up when client disconnects
            if client_id in room_queues[room_id]:
                del room_queues[room_id][client_id]
            if not room_queues[room_id]:
                del room_queues[room_id]

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

def broadcast_to_room(room_id, message):
    if room_id in room_queues:
        dead_clients = []
        for client_id, client_queue in room_queues[room_id].items():
            try:
                client_queue.put_nowait(message)
            except queue.Full:
                dead_clients.append(client_id)
        
        # Clean up dead clients
        for client_id in dead_clients:
            del room_queues[room_id][client_id]

if __name__ == '__main__':
    # Increase the timeout for Werkzeug's request handling
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )