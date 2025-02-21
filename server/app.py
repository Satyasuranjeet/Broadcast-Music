from flask import Flask
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

rooms = {}

@app.route('/')
def index():
    return "Music Broadcast Server Running"

@socketio.on('create_room')
def on_create(data):
    room_id = data['roomId']
    if room_id not in rooms:
        rooms[room_id] = {
            'current_track': '',
            'is_playing': False,
            'current_time': 0,
            'users': []
        }
        join_room(room_id)
        emit('room_created', {'success': True, 'roomId': room_id})
    else:
        emit('room_created', {'success': False, 'message': 'Room already exists'})

@socketio.on('join_room')
def on_join(data):
    room_id = data['roomId']
    if room_id in rooms:
        join_room(room_id)
        rooms[room_id]['users'].append(data.get('username', 'Anonymous'))
        # Send current track state to new user
        emit('music_state', {
            'track': rooms[room_id]['current_track'],
            'isPlaying': rooms[room_id]['is_playing'],
            'currentTime': rooms[room_id]['current_time']
        })
        emit('user_joined', {'username': data.get('username', 'Anonymous')}, room=room_id)
    else:
        emit('join_failed', {'message': 'Room not found'})

@socketio.on('set_music')
def on_set_music(data):
    room_id = data['roomId']
    if room_id in rooms:
        rooms[room_id]['current_track'] = data['track']
        rooms[room_id]['is_playing'] = False
        rooms[room_id]['current_time'] = 0
        emit('music_state', {
            'track': data['track'],
            'isPlaying': False,
            'currentTime': 0
        }, room=room_id)

@socketio.on('play_pause')
def on_play_pause(data):
    room_id = data['roomId']
    if room_id in rooms:
        rooms[room_id]['is_playing'] = data['isPlaying']
        rooms[room_id]['current_time'] = data['currentTime']
        emit('music_state', {
            'track': rooms[room_id]['current_track'],
            'isPlaying': data['isPlaying'],
            'currentTime': data['currentTime']
        }, room=room_id)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)