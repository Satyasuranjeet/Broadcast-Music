from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import json
import queue
import os
import uuid
import requests
from collections import defaultdict
from werkzeug.serving import WSGIRequestHandler

app = Flask(__name__)
CORS(app)

# Store rooms and queues
rooms = {}
room_queues = defaultdict(lambda: defaultdict(queue.Queue))

# Get port from environment variable with a default of 10000
port = int(os.environ.get('PORT', 10000))

def fetch_song_data(query):
    try:
        url = f'https://saavn.dev/api/search/songs?query={query}'
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                songs = []
                for song in data['data']['results']:
                    song_data = {
                        'id': song.get('id'),
                        'title': song.get('name'),
                        'mp3_url': None,
                        'thumbnail_url': None,
                        'artist': song.get('primaryArtists', 'Unknown Artist')
                    }
                    if song.get('downloadUrl'):
                        for download in song['downloadUrl']:
                            if download.get('quality') == '320kbps':
                                song_data['mp3_url'] = download.get('url')
                                break
                    
                    if song.get('image'):
                        for image in song['image']:
                            if image.get('quality') == '500x500':
                                song_data['thumbnail_url'] = image.get('url')
                                break
                        
                    songs.append(song_data)
                return songs
            return {"error": "No results found"}
    except requests.RequestException as e:
        return {"error": f"Failed to fetch data: {str(e)}"}
    return {"error": "Unknown error occurred"}

@app.route('/songs', methods=['GET'])
def get_songs():
    query = request.args.get('query', 'Stree2')
    
    if not query:
        return jsonify({"error": "No song name provided"}), 400
    
    songs = fetch_song_data(query)
    if isinstance(songs, dict) and "error" in songs:
        return jsonify(songs), 400
    return jsonify(songs)

@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>Music Broadcast</title>
            <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
            <style>
                .gradient-bg {
                    background: linear-gradient(135deg, #1e3a8a, #1e40af);
                }
                .glass-effect {
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 10px;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
                .input-style {
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
                .btn-primary {
                    background: #3b82f6;
                    color: white;
                }
                .btn-primary:hover {
                    background: #2563eb;
                }
                .btn-secondary {
                    background: #4f46e5;
                    color: white;
                }
                .btn-secondary:hover {
                    background: #4338ca;
                }
                .song-item {
                    transition: all 0.3s ease;
                }
                .song-item:hover {
                    transform: translateX(5px);
                    background: rgba(255, 255, 255, 0.1);
                }
            </style>
        </head>
        <body class="gradient-bg min-h-screen text-white font-sans">
            <div class="container mx-auto px-4 py-8 max-w-3xl">
                <div class="glass-effect rounded-xl p-8 shadow-2xl">
                    <h1 class="text-4xl font-bold text-center mb-8 bg-clip-text text-transparent bg-gradient-to-r from-green-400 to-blue-500">
                        Music Broadcast
                    </h1>
                    
                    <!-- Message Display -->
                    <div id="message" class="hidden mb-6 p-4 rounded-lg text-center"></div>
                    
                    <!-- Room Controls -->
                    <div id="controls" class="space-y-4">
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-300">Create or Join Room</label>
                            <div class="flex space-x-2">
                                <input type="text" id="roomId" placeholder="Enter Room ID" 
                                    class="flex-1 px-4 py-2 rounded-lg input-style text-white">
                                <input type="text" id="username" placeholder="Your Name" 
                                    class="flex-1 px-4 py-2 rounded-lg input-style text-white">
                                <button onclick="createRoom()" 
                                    class="btn-primary px-6 py-2 rounded-lg font-semibold">
                                    Create Room
                                </button>
                                <button onclick="joinRoom()" 
                                    class="btn-secondary px-6 py-2 rounded-lg font-semibold">
                                    Join Room
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Music Controls (Hidden by Default) -->
                    <div id="musicControls" class="hidden space-y-6 mt-8">
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-300">Search Songs</label>
                            <div class="flex space-x-2">
                                <input type="text" id="searchQuery" placeholder="Enter song name" 
                                    class="flex-1 px-4 py-2 rounded-lg input-style text-white">
                                <button onclick="searchSongs()" 
                                    class="btn-primary px-6 py-2 rounded-lg font-semibold">
                                    Search
                                </button>
                            </div>
                        </div>
                        
                        <!-- Search Results -->
                        <div id="searchResults" class="hidden space-y-2">
                            <h3 class="text-xl font-semibold mb-3">Search Results</h3>
                            <div id="songsList" class="space-y-2 max-h-60 overflow-y-auto"></div>
                        </div>
                        
                        <!-- Audio Player -->
                        <div class="mt-6">
                            <audio id="audio" controls class="w-full"></audio>
                        </div>
                        
                        <!-- Play/Pause Button -->
                        <div class="grid grid-cols-2 gap-4">
                            <button onclick="togglePlay()" id="playPauseBtn"
                                class="btn-secondary px-6 py-3 rounded-lg font-semibold">
                                Play
                            </button>
                        </div>
                        
                        <!-- Now Playing -->
                        <div id="nowPlaying" class="hidden mt-4 p-4 glass-effect rounded-lg">
                            <h3 class="text-lg font-semibold mb-2">Now Playing</h3>
                            <div id="currentSong" class="text-gray-300"></div>
                        </div>
                        
                        <!-- Connected Users -->
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
                
                // Show message to the user
                function showMessage(message, isError = false) {
                    const messageDiv = document.getElementById('message');
                    messageDiv.textContent = message;
                    messageDiv.className = isError ? 'bg-red-500' : 'bg-green-500';
                    messageDiv.classList.remove('hidden');
                    setTimeout(() => messageDiv.classList.add('hidden'), 3000);
                }
                
                // Create a new room
                async function createRoom() {
                    const roomId = document.getElementById('roomId').value;
                    const username = document.getElementById('username').value;
                    
                    if (!roomId || !username) {
                        showMessage('Please enter a room ID and username', true);
                        return;
                    }
                    
                    try {
                        const response = await fetch('/create-room', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ roomId, username })
                        });
                        
                        const data = await response.json();
                        if (data.success) {
                            currentRoom = roomId;
                            document.getElementById('controls').style.display = 'none';
                            document.getElementById('musicControls').style.display = 'block';
                            connectToEvents();
                            showMessage('Room created successfully!');
                        } else {
                            showMessage(data.message || 'Failed to create room', true);
                        }
                    } catch (error) {
                        showMessage('Error creating room', true);
                    }
                }
                
                // Join an existing room
                async function joinRoom() {
                    const roomId = document.getElementById('roomId').value;
                    const username = document.getElementById('username').value;
                    
                    if (!roomId || !username) {
                        showMessage('Please enter a room ID and username', true);
                        return;
                    }
                    
                    try {
                        const response = await fetch('/join-room', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ roomId, username })
                        });
                        
                        const data = await response.json();
                        if (data.success) {
                            currentRoom = roomId;
                            document.getElementById('controls').style.display = 'none';
                            document.getElementById('musicControls').style.display = 'block';
                            connectToEvents();
                            showMessage('Joined room successfully!');
                        } else {
                            showMessage(data.message || 'Failed to join room', true);
                        }
                    } catch (error) {
                        showMessage('Error joining room', true);
                    }
                }
                
                // Search for songs
                async function searchSongs() {
                    const query = document.getElementById('searchQuery').value;
                    if (!query) {
                        showMessage('Please enter a song name', true);
                        return;
                    }
                    
                    try {
                        const response = await fetch(`/songs?query=${encodeURIComponent(query)}`);
                        const songs = await response.json();
                        
                        if (response.ok) {
                            displaySearchResults(songs);
                        } else {
                            showMessage(songs.error || 'Failed to search songs', true);
                        }
                    } catch (error) {
                        showMessage('Error searching songs', true);
                    }
                }
                
                // Display search results
                function displaySearchResults(songs) {
                    const songsList = document.getElementById('songsList');
                    const searchResults = document.getElementById('searchResults');
                    
                    songsList.innerHTML = songs.map(song => `
                        <div class="song-item p-3 rounded-lg glass-effect cursor-pointer" 
                             onclick="selectSong('${song.mp3_url}', '${song.title}', '${song.artist}')">
                            <div class="font-medium">${song.title}</div>
                            <div class="text-sm text-gray-400">${song.artist}</div>
                        </div>
                    `).join('');
                    
                    searchResults.style.display = 'block';
                }
                
                // Select a song to play
                async function selectSong(url, title, artist) {
                    if (!url) {
                        showMessage('No playable URL for this song', true);
                        return;
                    }
                    
                    try {
                        const response = await fetch('/set-music', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                roomId: currentRoom,
                                track: url,
                                title: title,
                                artist: artist
                            })
                        });
                        
                        if ((await response.json()).success) {
                            document.getElementById('currentSong').innerHTML = `
                                <div class="font-medium">${title}</div>
                                <div class="text-sm">${artist}</div>
                            `;
                            document.getElementById('nowPlaying').style.display = 'block';
                            showMessage('Music updated successfully!');
                        }
                    } catch (error) {
                        showMessage('Error setting music', true);
                    }
                }
                
                // Toggle play/pause
                function togglePlay() {
                    const audio = document.getElementById('audio');
                    isPlaying = !isPlaying;
                    audio[isPlaying ? 'play' : 'pause']();
                    document.getElementById('playPauseBtn').textContent = isPlaying ? 'Pause' : 'Play';
                    
                    fetch('/play-pause', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            roomId: currentRoom,
                            isPlaying: isPlaying,
                            currentTime: audio.currentTime
                        })
                    });
                }
                
                // Connect to Server-Sent Events (SSE)
                function connectToEvents() {
                    const events = new EventSource(`/events?roomId=${currentRoom}`);
                    
                    events.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        
                        if (data.type === 'music_state') {
                            const audio = document.getElementById('audio');
                            const playPauseBtn = document.getElementById('playPauseBtn');
                            const nowPlaying = document.getElementById('nowPlaying');
                            
                            audio.src = data.data.track;
                            audio.currentTime = data.data.currentTime;
                            
                            if (data.data.title && data.data.artist) {
                                document.getElementById('currentSong').innerHTML = `
                                    <div class="font-medium">${data.data.title}</div>
                                    <div class="text-sm">${data.data.artist}</div>
                                `;
                                nowPlaying.style.display = 'block';
                            }
                            
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
                
                // Update the list of connected users
                function updateUserList(users) {
                    const userList = document.getElementById('userList');
                    userList.innerHTML = users.map(user => `<li>${user}</li>`).join('');
                }
            </script>
        </body>
    </html>
    """

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
        rooms[room_id].update({
            'track': data['track'],
            'title': data.get('title'),
            'artist': data.get('artist'),
            'isPlaying': False,
            'currentTime': 0
        })
        
        broadcast_to_room(room_id, {
            'type': 'music_state',
            'data': {
                'track': data['track'],
                'title': data.get('title'),
                'artist': data.get('artist'),
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
                try:
                    message = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(message)}\n\n"
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        except GeneratorExit:
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
        
        for client_id in dead_clients:
            del room_queues[room_id][client_id]

if __name__ == '__main__':
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )