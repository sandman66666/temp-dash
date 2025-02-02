// analytics-dashboard/src/components/modal/UserEventsModal.tsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface UserEventsModalProps {
  userId: string;
  onClose: () => void;
}

const UserEventsModal: React.FC<UserEventsModalProps> = ({ userId, onClose }) => {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        setLoading(true);
        setError('');
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001';
        const response = await axios.get(`${apiUrl}/getUserEventsById`, { params: { userId } });
        setEvents(response.data.events);
      } catch (err: any) {
        setError('Error fetching user events');
      } finally {
        setLoading(false);
      }
    };
    fetchEvents();
  }, [userId]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
      <div className="bg-white p-6 rounded-lg max-w-3xl w-full">
        <button onClick={onClose} className="text-red-500 mb-4">Close</button>
        {loading && <div>Loading events...</div>}
        {error && <div className="text-red-500">{error}</div>}
        {events && (
          <div>
            <h2 className="text-xl font-bold mb-4">Events for User: {userId}</h2>
            <pre className="text-sm bg-gray-100 p-4 rounded">
              {JSON.stringify(events, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default UserEventsModal;