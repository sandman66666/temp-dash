// analytics-dashboard/src/components/modal/UserListModal.tsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

export interface User {
  userId: string;
  email: string;
}

interface UserListModalProps {
  onClose: () => void;
  onSelectUser: (user: User) => void;
}

const UserListModal: React.FC<UserListModalProps> = ({ onClose, onSelectUser }) => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoading(true);
        setError('');
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001';
        const response = await axios.get(`${apiUrl}/getDescopeUsers`);
        // Assume response.data.users is an array of users.
        setUsers(response.data.users);
      } catch (err: any) {
        setError('Error fetching users');
      } finally {
        setLoading(false);
      }
    };
    fetchUsers();
  }, []);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50 p-4">
      <div className="bg-white p-6 rounded-lg w-full max-w-lg">
        <button onClick={onClose} className="text-red-500 mb-4">Close</button>
        {loading && <div>Loading users...</div>}
        {error && <div className="text-red-500">{error}</div>}
        {users && (
          <div className="max-h-96 overflow-y-auto">
            <ul>
              {users.map((user) => (
                <li
                  key={user.userId}
                  className="cursor-pointer text-blue-600 hover:underline py-1 border-b border-gray-200"
                  onClick={() => onSelectUser(user)}
                >
                  {user.email} <span className="text-sm text-gray-500">({user.userId})</span>
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