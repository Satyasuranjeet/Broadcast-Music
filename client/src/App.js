import React, { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';

const API_BASE_URL = 'https://broadcast-music.vercel.app';

const App = () => {
  const [roomId, setRoomId] = useState('');
  const [username, setUsername] = useState('');
  const [isHost, setIsHost] = useState(false);
  const [inRoom, setInRoom] = useState(false);
  const [musicUrl, setMusicUrl] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [users, setUsers] = useState([]);
  const [message, setMessage] = useState('');
  const audioRef = useRef(null);
  const eventSourceRef = useRef(null);
  const clientId = useRef(uuidv4());

  const connectToEventSource = (roomId) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventSource = new EventSource(
      `${API_BASE_URL}/api/events?roomId=${roomId}&clientId=${clientId.current}`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'keepalive') return;
      
      if (data.type === 'music_state') {
        if (audioRef.current) {
          audioRef.current.src = data.data.track;
          audioRef.current.currentTime = data.data.currentTime;
          setIsPlaying(data.data.isPlaying);
          
          if (data.data.isPlaying) {
            audioRef.current.play().catch(error => {
              console.error('Audio playback error:', error);
              setMessage('Error playing audio. Please check the URL.');
            });
          } else {
            audioRef.current.pause();
          }
        }
      } else if (data.type === 'user_joined') {
        setUsers(prev => [...prev, data.data.username]);
        setMessage(`${data.data.username} joined the room`);
      }
    };

    eventSource.onerror = (error) => {
      console.error('EventSource error:', error);
      setMessage('Connection error. Reconnecting...');
      eventSource.close();
      setTimeout(() => connectToEventSource(roomId), 3000);
    };

    eventSourceRef.current = eventSource;
  };

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const createRoom = async () => {
    if (!roomId || !username) {
      setMessage('Please enter both room ID and username');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/create-room`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ roomId, username })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setInRoom(true);
        setIsHost(true);
        setMessage(`Room ${data.roomId} created successfully!`);
        connectToEventSource(roomId);
      } else {
        setMessage(data.message);
      }
    } catch (error) {
      console.error('Error creating room:', error);
      setMessage('Error creating room. Please try again.');
    }
  };

  const joinRoom = async () => {
    if (!roomId || !username) {
      setMessage('Please enter both room ID and username');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/join-room`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ roomId, username })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setInRoom(true);
        setUsers(data.currentState.users);
        connectToEventSource(roomId);
      } else {
        setMessage(data.message);
      }
    } catch (error) {
      console.error('Error joining room:', error);
      setMessage('Error joining room. Please try again.');
    }
  };

  const setMusic = async () => {
    if (!musicUrl) {
      setMessage('Please enter a music URL');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/set-music`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ roomId, track: musicUrl })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setMessage('Music updated!');
      } else {
        setMessage(data.message);
      }
    } catch (error) {
      console.error('Error setting music:', error);
      setMessage('Error updating music. Please try again.');
    }
  };

  const togglePlayPause = async () => {
    if (!audioRef.current) return;

    const newPlayState = !isPlaying;
    setIsPlaying(newPlayState);

    try {
      const response = await fetch(`${API_BASE_URL}/api/play-pause`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          roomId,
          isPlaying: newPlayState,
          currentTime: audioRef.current.currentTime
        })
      });
      
      const data = await response.json();
      
      if (!data.success) {
        setMessage(data.message);
        setIsPlaying(!newPlayState); // Revert state if failed
      }
    } catch (error) {
      console.error('Error toggling play/pause:', error);
      setMessage('Error updating playback state. Please try again.');
      setIsPlaying(!newPlayState); // Revert state if failed
    }
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