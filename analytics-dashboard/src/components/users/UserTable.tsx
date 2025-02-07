import React, { useState, useEffect } from 'react';
import { fetchUserStats } from '../../services/metricService';
import UserEventsModal from '../modal/UserEventsModal';

export interface UserStats {
  email: string;
  trace_id: string;
  messageCount: number;
  sketchCount: number;
  renderCount: number;
}

interface UserTableProps {
  gaugeType?: 'active_users' | 'power_users' | 'moderate_users' | 'producers' | 'producers_attempting';
  timeRange?: {
    start: Date;
    end: Date;
  };
}

const UserTable: React.FC<UserTableProps> = ({ gaugeType = 'active_users', timeRange }) => {
  const [users, setUsers] = useState<UserStats[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [sortConfig, setSortConfig] = useState<{
    key: keyof UserStats;
    direction: 'ascending' | 'descending';
  }>({ key: 'messageCount', direction: 'descending' });

  useEffect(() => {
    const fetchData = async () => {
      if (!timeRange) return;

      try {
        setLoading(true);
        setError('');
        const data = await fetchUserStats(timeRange.start, timeRange.end, gaugeType);
        setUsers(data);
      } catch (err) {
        setError('Error fetching user statistics');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [gaugeType, timeRange]);

  const handleSort = (key: keyof UserStats) => {
    setSortConfig(current => ({
      key,
      direction: current.key === key && current.direction === 'ascending' 
        ? 'descending' 
        : 'ascending'
    }));
  };

  const handleUserClick = (userId: string) => {
    setSelectedUserId(userId);
  };

  const handleCloseModal = () => {
    setSelectedUserId(null);
  };

  const sortedUsers = [...users].sort((a, b) => {
    if (sortConfig.direction === 'ascending') {
      return a[sortConfig.key] > b[sortConfig.key] ? 1 : -1;
    }
    return a[sortConfig.key] < b[sortConfig.key] ? 1 : -1;
  });

  const getSortIcon = (key: keyof UserStats) => {
    if (sortConfig.key !== key) return '↕️';
    return sortConfig.direction === 'ascending' ? '↑' : '↓';
  };

  const getTableTitle = () => {
    switch (gaugeType) {
      case 'active_users':
        return 'Active Users';
      case 'power_users':
        return 'Power Users';
      case 'moderate_users':
        return 'Moderate Users';
      case 'producers':
        return 'Producers';
      case 'producers_attempting':
        return 'Producers Attempting';
      default:
        return 'Users';
    }
  };

  const columns = [
    {
      key: 'email' as keyof UserStats,
      label: 'Email',
      sortable: true
    },
    {
      key: 'messageCount' as keyof UserStats,
      label: 'Messages',
      sortable: true
    },
    {
      key: 'sketchCount' as keyof UserStats,
      label: 'Sketches',
      sortable: true
    },
    {
      key: 'renderCount' as keyof UserStats,
      label: 'Renders',
      sortable: true
    },
    {
      key: 'trace_id' as keyof UserStats,
      label: 'ID',
      sortable: false
    }
  ];

  return (
    <div className="mt-8 bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-800">{getTableTitle()} Statistics</h2>
      </div>
      
      {loading && (
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      )}
      
      {error && (
        <div className="text-red-500 p-4 text-center bg-red-50">
          {error}
        </div>
      )}
      
      {!loading && !error && users.length === 0 && (
        <div className="text-gray-500 text-center py-8">
          No user statistics available
        </div>
      )}
      
      {users.length > 0 && (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {columns.map(column => (
                  <th 
                    key={column.key}
                    className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${
                      column.sortable ? 'cursor-pointer hover:bg-gray-100' : ''
                    }`}
                    onClick={() => column.sortable && handleSort(column.key)}
                  >
                    {column.label} {column.sortable && getSortIcon(column.key)}
                  </th>
                ))}
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
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{user.messageCount}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{user.sketchCount}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{user.renderCount}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500">{user.trace_id}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedUserId && (
        <UserEventsModal
          userId={selectedUserId}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
};

export default UserTable;