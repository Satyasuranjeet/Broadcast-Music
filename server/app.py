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
    <!DOCTYPE html>
<html>
    <head>
        <title>Music Broadcast</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <style>
            @keyframes gradient {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }

            @keyframes slideUp {
                from { transform: translateY(20px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }

            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }

            .gradient-bg {
                background: linear-gradient(-45deg, #0f172a, #1e293b, #172554, #1e1b4b);
                background-size: 400% 400%;
                animation: gradient 15s ease infinite;
            }

            .glass-effect {
                background: rgba(30, 41, 59, 0.7);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(148, 163, 184, 0.1);
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                animation: slideUp 0.6s ease-out;
            }

            .input-style {
                background: rgba(30, 41, 59, 0.6);
                border: 1px solid rgba(148, 163, 184, 0.2);
                transition: all 0.3s ease;
            }

            .input-style:focus {
                background: rgba(30, 41, 59, 0.8);
                border-color: rgba(96, 165, 250, 0.5);
                outline: none;
                box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.2);
            }

            .btn-primary {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }

            .btn-primary::after {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                transition: 0.5s;
            }

            .btn-primary:hover::after {
                left: 100%;
            }

            .btn-secondary {
                background: rgba(30, 41, 59, 0.8);
                border: 1px solid rgba(148, 163, 184, 0.2);
                transition: all 0.3s ease;
            }

            .song-item {
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                animation: slideUp 0.5s ease-out;
            }

            .song-item:hover {
                transform: translateX(10px) scale(1.02);
                background: rgba(96, 165, 250, 0.1);
                border-color: rgba(96, 165, 250, 0.3);
            }

            /* Custom Audio Player Styling */
            .custom-player {
                background: rgba(30, 41, 59, 0.8);
                border-radius: 16px;
                padding: 20px;
                position: relative;
            }

            .progress-bar {
                width: 100%;
                height: 6px;
                background: rgba(148, 163, 184, 0.2);
                border-radius: 3px;
                cursor: pointer;
                position: relative;
            }

            .progress {
                height: 100%;
                background: #3b82f6;
                border-radius: 3px;
                position: relative;
                transition: width 0.1s linear;
            }

            .progress::after {
                content: '';
                position: absolute;
                right: -6px;
                top: -4px;
                width: 14px;
                height: 14px;
                background: #60a5fa;
                border-radius: 50%;
                transform: scale(0);
                transition: transform 0.2s ease;
            }

            .progress-bar:hover .progress::after {
                transform: scale(1);
            }

            .visualizer {
                display: flex;
                align-items: flex-end;
                height: 40px;
                gap: 2px;
                margin-bottom: 10px;
            }

            .visualizer-bar {
                width: 4px;
                background: #3b82f6;
                border-radius: 2px;
                transition: height 0.2s ease;
            }

            @keyframes bounce {
                0%, 100% { transform: scaleY(0.3); }
                50% { transform: scaleY(1); }
            }

            .playing .visualizer-bar {
                animation: bounce 1s ease infinite;
                animation-delay: calc(var(--delay) * 0.1s);
            }

            /* Message Animation */
            #message {
                animation: slideUp 0.3s ease-out;
            }

            /* Now Playing Animation */
            .now-playing-animation {
                display: inline-block;
                margin-right: 8px;
            }

            .now-playing-animation span {
                display: inline-block;
                width: 4px;
                height: 4px;
                margin-right: 2px;
                background: #60a5fa;
                border-radius: 50%;
                animation: bounce 0.8s ease infinite;
            }

            .now-playing-animation span:nth-child(2) {
                animation-delay: 0.2s;
            }

            .now-playing-animation span:nth-child(3) {
                animation-delay: 0.4s;
            }
        </style>
    </head>
    <body class="gradient-bg min-h-screen text-gray-100 font-sans antialiased">
        <div class="container mx-auto px-4 py-12 max-w-3xl">
            <div class="glass-effect rounded-2xl p-8 shadow-2xl">
                <h1 class="text-5xl font-bold text-center mb-12 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-500">
                    Music Broadcast
                </h1>
                
                <!-- Message Display -->
                <div id="message" class="hidden mb-8 p-4 rounded-xl text-center transition-all duration-300"></div>
                
                <!-- Room Controls -->
                <div id="controls" class="space-y-6">
                    <div class="space-y-4">
                        <label class="block text-lg font-medium text-gray-300 mb-2">Create or Join Room</label>
                        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                            <input type="text" id="roomId" placeholder="Enter Room ID" 
                                class="w-full px-4 py-3 rounded-xl input-style text-gray-100 placeholder-gray-400">
                            <input type="text" id="username" placeholder="Your Name" 
                                class="w-full px-4 py-3 rounded-xl input-style text-gray-100 placeholder-gray-400">
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <button onclick="createRoom()" 
                                class="btn-primary px-6 py-3 rounded-xl font-semibold w-full">
                                Create Room
                            </button>
                            <button onclick="joinRoom()" 
                                class="btn-secondary px-6 py-3 rounded-xl font-semibold w-full">
                                Join Room
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Music Controls -->
                <div id="musicControls" class="hidden space-y-8 mt-10">
                    <div class="space-y-4">
                        <label class="block text-lg font-medium text-gray-300">Search Songs</label>
                        <div class="flex space-x-3">
                            <input type="text" id="searchQuery" placeholder="Enter song name" 
                                class="flex-1 px-4 py-3 rounded-xl input-style text-gray-100 placeholder-gray-400">
                            <button onclick="searchSongs()" 
                                class="btn-primary px-8 py-3 rounded-xl font-semibold whitespace-nowrap">
                                Search
                            </button>
                        </div>
                    </div>
                    
                    <!-- Search Results -->
                    <div id="searchResults" class="hidden space-y-4">
                        <h3 class="text-xl font-semibold mb-4">Search Results</h3>
                        <div id="songsList" class="space-y-3 max-h-72 overflow-y-auto pr-2"></div>
                    </div>
                    
                    <!-- Custom Audio Player -->
                    <div class="custom-player">
                        <div class="visualizer" id="audioVisualizer">
                            <!-- Visualizer bars will be added by JavaScript -->
                        </div>
                        <audio id="audio" class="hidden"></audio>
                        <div class="progress-bar" id="progressBar">
                            <div class="progress" id="progress" style="width: 0%"></div>
                        </div>
                        <div class="flex justify-between items-center mt-4">
                            <span id="currentTime" class="text-sm">0:00</span>
                            <div class="flex space-x-4">
                                <button onclick="togglePlay()" id="playPauseBtn"
                                    class="btn-primary px-8 py-2 rounded-xl font-semibold">
                                    Play
                                </button>
                            </div>
                            <span id="duration" class="text-sm">0:00</span>
                        </div>
                    </div>
                    
                    <!-- Now Playing -->
                    <div id="nowPlaying" class="hidden mt-6 p-6 glass-effect rounded-xl">
                        <h3 class="text-xl font-semibold mb-3">
                            <div class="now-playing-animation">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                            Now Playing
                        </h3>
                        <div id="currentSong" class="text-gray-300"></div>
                    </div>
                    
                    <!-- Connected Users -->
                    <div id="users" class="mt-8 p-6 glass-effect rounded-xl">
                        <h3 class="text-xl font-semibold mb-4">Connected Users</h3>
                        <ul id="userList" class="space-y-2 text-gray-300"></ul>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // Create audio visualizer
            function createVisualizer() {
                const visualizer = document.getElementById('audioVisualizer');
                visualizer.innerHTML = '';
                for(let i = 0; i < 32; i++) {
                    const bar = document.createElement('div');
                    bar.className = 'visualizer-bar';
                    bar.style.height = '5px';
                    bar.style.setProperty('--delay', i);
                    visualizer.appendChild(bar);
                }
            }
            createVisualizer();

            // Initialize custom audio player
            const audio = document.getElementById('audio');
            const progressBar = document.getElementById('progressBar');
            const progress = document.getElementById('progress');
            const currentTimeDisplay = document.getElementById('currentTime');
            const durationDisplay = document.getElementById('duration');
            const visualizer = document.getElementById('audioVisualizer');

            // Update progress bar
            audio.addEventListener('timeupdate', () => {
                const percentage = (audio.currentTime / audio.duration) * 100;
                progress.style.width = percentage + '%';
                currentTimeDisplay.textContent = formatTime(audio.currentTime);
            });

            audio.addEventListener('loadedmetadata', () => {
                durationDisplay.textContent = formatTime(audio.duration);
            });

            // Click on progress bar to seek
            progressBar.addEventListener('click', (e) => {
                const rect = progressBar.getBoundingClientRect();
                const percentage = (e.clientX - rect.left) / rect.width;
                audio.currentTime = percentage * audio.duration;
            });

            // Format time in minutes:seconds
            function formatTime(seconds) {
                const minutes = Math.floor(seconds / 60);
                seconds = Math.floor(seconds % 60);
                return `${minutes}:${seconds.toString().padStart(2, '0')}`;
            }

            // Original JavaScript functions with added animations
            let isPlaying = false;
            let currentRoom = '';
            
            function showMessage(message, isError = false) {
                const messageDiv = document.getElementById('message');
                messageDiv.textContent = message;
                messageDiv.className = `mb-8 p-4 rounded-xl text-center ${isError ? 'bg-red-500' : 'bg-green-500'} shadow-lg`;
                messageDiv.classList.remove('hidden');
                setTimeout(() => messageDiv.classList.add('hidden'), 3000);
            }

            // Update togglePlay function
            function togglePlay() {
                const playPauseBtn = document.getElementById('playPauseBtn');
                isPlaying = !isPlaying;
                
                if (isPlaying) {
                    audio.play();
                    playPauseBtn.textContent = 'Pause';
                    visualizer.classList.add('playing');
                } else {
                    audio.pause();
                    playPauseBtn.textContent = 'Play';
                    visualizer.classList.remove('playing');
                }
                
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

            // Rest of the original JavaScript functions remain the same...
            // Include all other original JavaScript functions here
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