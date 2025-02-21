import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';

const App = () => {
  const [socket, setSocket] = useState(null);
  const [roomId, setRoomId] = useState('');
  const [username, setUsername] = useState('');
  const [isHost, setIsHost] = useState(false);
  const [inRoom, setInRoom] = useState(false);
  const [musicUrl, setMusicUrl] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [users, setUsers] = useState([]);
  const [message, setMessage] = useState('');
  const audioRef = useRef(null);

  useEffect(() => {
    const newSocket = io('broadcast-music.vercel.app');
    setSocket(newSocket);

    return () => newSocket.close();
  }, []);

  useEffect(() => {
    if (!socket) return;

    socket.on('room_created', (response) => {
      if (response.success) {
        setInRoom(true);
        setIsHost(true);
        setMessage(`Room ${response.roomId} created successfully!`);
      } else {
        setMessage(response.message);
      }
    });

    socket.on('join_failed', (data) => {
      setMessage(data.message);
    });

    socket.on('music_state', (data) => {
      if (audioRef.current) {
        audioRef.current.src = data.track;
        audioRef.current.currentTime = data.currentTime;
        setIsPlaying(data.isPlaying);
        
        if (data.isPlaying) {
          audioRef.current.play();
        } else {
          audioRef.current.pause();
        }
      }
    });

    socket.on('user_joined', (data) => {
      setUsers(prev => [...prev, data.username]);
      setMessage(`${data.username} joined the room`);
    });

  }, [socket]);

  const createRoom = () => {
    if (!roomId || !username) {
      setMessage('Please enter both room ID and username');
      return;
    }
    socket.emit('create_room', { roomId, username });
  };

  const joinRoom = () => {
    if (!roomId || !username) {
      setMessage('Please enter both room ID and username');
      return;
    }
    socket.emit('join_room', { roomId, username });
    setInRoom(true);
  };

  const setMusic = () => {
    if (!musicUrl) {
      setMessage('Please enter a music URL');
      return;
    }
    socket.emit('set_music', { roomId, track: musicUrl });
    setMessage('Music updated!');
  };

  const togglePlayPause = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }

    const newPlayState = !isPlaying;
    setIsPlaying(newPlayState);
    
    socket.emit('play_pause', {
      roomId,
      isPlaying: newPlayState,
      currentTime: audioRef.current.currentTime
    });
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
      <div className="max-w-md mx-auto bg-gray-800 rounded-lg p-6 space-y-4">
        <h1 className="text-2xl font-bold text-center">Music Broadcast Room</h1>
        
        {message && (
          <div className="bg-blue-500 p-2 rounded text-center">
            {message}
          </div>
        )}

        {!inRoom ? (
          <div className="space-y-4">
            <input
              type="text"
              placeholder="Enter username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full p-2 rounded bg-gray-700"
            />
            <input
              type="text"
              placeholder="Enter room ID"
              value={roomId}
              onChange={(e) => setRoomId(e.target.value)}
              className="w-full p-2 rounded bg-gray-700"
            />
            <div className="flex space-x-2">
              <button
                onClick={createRoom}
                className="flex-1 bg-blue-600 p-2 rounded hover:bg-blue-700"
              >
                Create Room
              </button>
              <button
                onClick={joinRoom}
                className="flex-1 bg-green-600 p-2 rounded hover:bg-green-700"
              >
                Join Room
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {isHost && (
              <div className="space-y-2">
                <input
                  type="text"
                  placeholder="Enter music URL"
                  value={musicUrl}
                  onChange={(e) => setMusicUrl(e.target.value)}
                  className="w-full p-2 rounded bg-gray-700"
                />
                <button
                  onClick={setMusic}
                  className="w-full bg-blue-600 p-2 rounded hover:bg-blue-700"
                >
                  Set Music
                </button>
              </div>
            )}
            
            <div className="space-y-2">
              <button
                onClick={togglePlayPause}
                className="w-full bg-green-600 p-2 rounded hover:bg-green-700"
              >
                {isPlaying ? 'Pause' : 'Play'}
              </button>
              <audio ref={audioRef} />
            </div>

            <div className="mt-4">
              <h3 className="font-bold">Connected Users:</h3>
              <ul className="list-disc pl-4">
                {users.map((user, index) => (
                  <li key={index}>{user}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default App;