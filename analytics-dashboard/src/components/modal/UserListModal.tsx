// analytics-dashboard/src/components/modal/UserListModal.tsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { fetchPowerUsers } from '../../services/metricService';

export interface User {
  userId?: string;
  email: string;
  trace_id?: string;
}

interface UserListModalProps {
  onClose: () => void;
  onSelectUser: (user: User) => void;
  mode?: 'regular' | 'power';
  gaugeType?: 'thread_users' | 'sketch_users' | 'render_users' | 'medium_chat_users' | 'active_chat_users';
  timeRange?: {
    start: Date;
    end: Date;
  };
}

const UserListModal: React.FC<UserListModalProps> = ({ 
  onClose, 
  onSelectUser, 
  mode = 'regular',
  gaugeType = 'thread_users',
  timeRange
}) => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoading(true);
        setError('');
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001';

        if (mode === 'power' && timeRange) {
          // Fetch users from the gauge-users endpoint
          const response = await axios.get(`${apiUrl}/metrics/gauge-users`, {
            params: {
              startDate: timeRange.start.toISOString(),
              endDate: timeRange.end.toISOString(),
              gaugeType: gaugeType
            }
          });

          if (response.data.status === 'success') {
            setUsers(response.data.data);
          } else {
            setError('Failed to fetch user details');
          }
        } else {
          // Regular user fetch from Descope
          const response = await axios.get(`${apiUrl}/getDescopeUsers`);
          const descopeUsers = response.data.users || [];
          setUsers(descopeUsers.map((user: any) => ({
            userId: user.userId,
            email: user.email
          })));
        }
      } catch (err: any) {
        setError(mode === 'power' ? 'Error fetching power users' : 'Error fetching users');
        console.error('Error fetching users:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchUsers();
  }, [mode, timeRange, gaugeType]);

  const getModalTitle = () => {
    if (mode === 'regular') return 'All Users';
    
    switch (gaugeType) {
      case 'thread_users':
        return 'Thread Users';
      case 'sketch_users':
        return 'Sketch Users';
      case 'render_users':
        return 'Render Users';
      case 'medium_chat_users':
        return 'Medium Chat Users';
      case 'active_chat_users':
        return 'Power Users';
      default:
        return 'Users';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50 p-4">
      <div className="bg-white p-6 rounded-lg w-full max-w-lg">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">
            {getModalTitle()}
          </h2>
          <button 
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            Close
          </button>
        </div>
        
        {loading && (
          <div className="flex justify-center items-center py-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          </div>
        )}
        
        {error && (
          <div className="text-red-500 p-4 text-center bg-red-50 rounded-md">
            {error}
          </div>
        )}
        
        {!loading && !error && users.length === 0 && (
          <div className="text-gray-500 text-center py-4">
            {mode === 'power' ? `No ${getModalTitle().toLowerCase()} found` : 'No users found'}
          </div>
        )}
        
        {users.length > 0 && (
          <div className="max-h-96 overflow-y-auto">
            <ul className="divide-y divide-gray-200">
              {users.map((user, index) => (
                <li
                  key={user.trace_id || user.userId || index}
                  className="py-3 hover:bg-gray-50 cursor-pointer transition-colors duration-150 ease-in-out"
                  onClick={() => onSelectUser(user)}
                >
                  <div className="flex items-center px-2">
                    <span className="mr-3 text-gray-500 w-6 text-right">
                      {index + 1}.
                    </span>
                    <div className="flex-1">
                      <div>
                        <span className="text-blue-600 hover:text-blue-800">
                          {user.email}
                        </span>
                      </div>
                      {user.trace_id && (
                        <div className="text-sm text-gray-500">
                          ID: {user.trace_id}
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default UserListModal;