import React, { useState, useEffect } from 'react';
import { fetchUserStats } from '../../services/metricService';
import UserEventsModal from '../modal/UserEventsModal';

export interface UserStats {
  trace_id: string;
  email: string;
  name?: string;
  messageCount?: number;
  sketchCount?: number;
  renderCount?: number;
  createdTime?: string;
  loginCount?: number;
}

interface UserTableProps {
  gaugeType: string;
  timeRange: {
    start: Date;
    end: Date;
  };
}

const UserTable: React.FC<UserTableProps> = ({ gaugeType = 'active_users', timeRange }) => {
  const [users, setUsers] = useState<UserStats[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [sortConfig, setSortConfig] = useState<{
    key: keyof UserStats;
    direction: 'ascending' | 'descending';
  }>({ key: gaugeType === 'total_users_count' || gaugeType === 'new_users' ? 'createdTime' : 'messageCount', direction: 'descending' });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchUserStats(gaugeType, timeRange.start, timeRange.end);
        setUsers(data);
      } catch (err) {
        console.error('Error fetching user stats:', err);
        setError('Failed to load user data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [gaugeType, timeRange]);

  const handleSort = (key: keyof UserStats) => {
    setSortConfig(current => ({
      key,
      direction: current.key === key && current.direction === 'ascending' ? 'descending' : 'ascending'
    }));
  };

  const sortedUsers = [...users].sort((a, b) => {
    const key = sortConfig.key;
    const aValue = a[key];
    const bValue = b[key];

    if (aValue === undefined && bValue === undefined) return 0;
    if (aValue === undefined) return 1;
    if (bValue === undefined) return -1;

    const comparison = typeof aValue === 'string' 
      ? aValue.localeCompare(bValue as string)
      : (aValue as number) - (bValue as number);
    
    return sortConfig.direction === 'ascending' ? comparison : -comparison;
  });

  const handleUserClick = (traceId: string) => {
    setSelectedUser(traceId);
  };

  const handleCloseModal = () => {
    setSelectedUser(null);
  };

  if (loading) {
    return (
      <div className="mt-4 p-4 flex justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mt-4 p-4 text-red-600">
        {error}
      </div>
    );
  }

  if (users.length === 0) {
    return (
      <div className="mt-4 p-4 text-gray-500">
        No users found for this metric.
      </div>
    );
  }

  return (
    <div className="mt-8">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-900">User Details</h2>
      </div>
      <div className="shadow overflow-x-auto border-b border-gray-200 sm:rounded-lg">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th 
                scope="col" 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer"
                onClick={() => handleSort('email')}
              >
                Email
              </th>
              {(gaugeType === 'total_users_count' || gaugeType === 'new_users') ? (
                <>
                  <th 
                    scope="col" 
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer"
                    onClick={() => handleSort('createdTime')}
                  >
                    Created
                  </th>
                  <th 
                    scope="col" 
                    className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer"
                    onClick={() => handleSort('loginCount')}
                  >
                    Logins
                  </th>
                </>
              ) : (
                <>
                  <th 
                    scope="col" 
                    className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer"
                    onClick={() => handleSort('messageCount')}
                  >
                    Messages
                  </th>
                  <th 
                    scope="col" 
                    className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer"
                    onClick={() => handleSort('sketchCount')}
                  >
                    Sketches
                  </th>
                  <th 
                    scope="col" 
                    className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer"
                    onClick={() => handleSort('renderCount')}
                  >
                    Renders
                  </th>
                </>
              )}
              <th 
                scope="col" 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Trace ID
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedUsers.map((user, index) => (
              <tr 
                key={user.trace_id || index}
                className="hover:bg-gray-50 transition-colors duration-150 ease-in-out cursor-pointer"
                onClick={() => handleUserClick(user.trace_id)}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-blue-600 hover:text-blue-800">
                    {user.email}
                  </div>
                </td>
                {(gaugeType === 'total_users_count' || gaugeType === 'new_users') ? (
                  <>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {user.createdTime ? new Date(parseInt(user.createdTime)).toLocaleString() : 'N/A'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900 text-right">{user.loginCount || 0}</div>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900 text-right">{user.messageCount || 0}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900 text-right">{user.sketchCount || 0}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900 text-right">{user.renderCount || 0}</div>
                    </td>
                  </>
                )}
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-500">{user.trace_id}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedUser && (
        <UserEventsModal
          traceId={selectedUser}
          onClose={handleCloseModal}
          timeRange={timeRange}
        />
      )}
    </div>
  );
};

export default UserTable;