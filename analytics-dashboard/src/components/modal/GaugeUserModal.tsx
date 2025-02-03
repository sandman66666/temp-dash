import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface GaugeUserModalProps {
  metricId: string;
  startDate: string; // ISO string
  endDate: string;   // ISO string
  onClose: () => void;
}

const GaugeUserModal: React.FC<GaugeUserModalProps> = ({ metricId, startDate, endDate, onClose }) => {
  const [userIds, setUserIds] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const fetchGaugeUsers = async () => {
      try {
        setLoading(true);
        setError('');
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001';
        const response = await axios.get(`${apiUrl}/getGaugeUserCandidates`, {
          params: { metricId, startDate, endDate }
        });
        
        if (response.data.error) {
          throw new Error(response.data.error);
        }
        
        if (!response.data.userIds || !Array.isArray(response.data.userIds)) {
          throw new Error('Invalid response format');
        }
        
        setUserIds(response.data.userIds);
      } catch (err: any) {
        console.error('Error fetching gauge users:', err);
        setError(err.message || 'Error fetching gauge users');
      } finally {
        setLoading(false);
      }
    };

    fetchGaugeUsers();
  }, [metricId, startDate, endDate]);

  const getMetricTitle = () => {
    switch (metricId) {
      case 'power_users':
        return 'Power Users (20+ messages)';
      case 'medium_chat_users':
        return 'Medium Chat Users (5-20 messages)';
      case 'active_users':
        return 'Active Users';
      case 'thread_users':
        return 'Thread Users';
      case 'sketch_users':
        return 'Sketch Users';
      case 'render_users':
        return 'Render Users';
      default:
        return 'Users';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50 p-4">
      <div className="bg-white p-6 rounded-lg w-full max-w-lg">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">{getMetricTitle()}</h2>
          <button 
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            Close
          </button>
        </div>
        
        {loading && (
          <div className="flex justify-center items-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          </div>
        )}
        
        {error && (
          <div className="bg-red-50 text-red-500 p-4 rounded-md mb-4">
            {error}
          </div>
        )}
        
        {!loading && !error && (
          <>
            <div className="mb-2 text-sm text-gray-500">
              Total Users: {userIds.length}
            </div>
            <div className="max-h-96 overflow-y-auto">
              {userIds.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No users found for this criteria
                </div>
              ) : (
                <ul className="divide-y divide-gray-200">
                  {userIds.map((userId, index) => (
                    <li 
                      key={userId} 
                      className="py-2 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-center">
                        <span className="w-8 text-gray-500 text-sm">
                          {index + 1}.
                        </span>
                        <span className="flex-1 font-mono text-sm">
                          {userId}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default GaugeUserModal;