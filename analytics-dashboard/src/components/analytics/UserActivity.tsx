import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import DateRangeSelector from '../common/DateRangeSelector';

interface UserActivityData {
  trace_id: string;
  email: string;
  firstAction: string;
  lastAction: string;
  daysBetween: number;
  totalActions: number;
}

const UserActivity: React.FC = () => {
  const [startDate, setStartDate] = useState<Date>(new Date('2024-01-27'));
  const [endDate, setEndDate] = useState<Date>(new Date());
  const [filterType, setFilterType] = useState<string>('consecutive_days');
  const [loading, setLoading] = useState<boolean>(true);
  const [users, setUsers] = useState<UserActivityData[]>([]);

  useEffect(() => {
    fetchUserActivity();
  }, [startDate, endDate, filterType]);

  const fetchUserActivity = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/metrics/user-activity?startDate=${startDate.toISOString()}&endDate=${endDate.toISOString()}&filterType=${filterType}`);
      const data = await response.json();
      if (data.status === 'success') {
        setUsers(data.users);
      }
    } catch (error) {
      console.error('Error fetching user activity:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDateChange = (start: Date, end: Date) => {
    setStartDate(start);
    setEndDate(end);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">User Activity Analysis</h1>
      </div>

      <div className="mb-8 space-y-4">
        <DateRangeSelector
          startDate={startDate}
          endDate={endDate}
          onDateChange={handleDateChange}
        />

        <div className="flex gap-4">
          <button
            onClick={() => setFilterType('consecutive_days')}
            className={`px-4 py-2 rounded-md ${
              filterType === 'consecutive_days'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Consecutive Days
          </button>
          <button
            onClick={() => setFilterType('one_to_two_weeks')}
            className={`px-4 py-2 rounded-md ${
              filterType === 'one_to_two_weeks'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            1-2 Weeks Apart
          </button>
          <button
            onClick={() => setFilterType('two_to_three_weeks')}
            className={`px-4 py-2 rounded-md ${
              filterType === 'two_to_three_weeks'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            2-3 Weeks Apart
          </button>
          <button
            onClick={() => setFilterType('month_apart')}
            className={`px-4 py-2 rounded-md ${
              filterType === 'month_apart'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Month Apart
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    First Action
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Action
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Days Between
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((user, index) => (
                  <tr key={user.trace_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{user.email}</div>
                      <div className="text-sm text-gray-500">{user.trace_id}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {format(new Date(user.firstAction), 'MMM d, yyyy HH:mm')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {format(new Date(user.lastAction), 'MMM d, yyyy HH:mm')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {user.daysBetween}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {user.totalActions}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserActivity;