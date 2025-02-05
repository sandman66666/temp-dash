import React, { useState, useEffect } from 'react';
import DateRangeSelector from '../common/DateRangeSelector';
import UserTable from '../users/UserTable';
import { fetchMetrics } from '../../services/metricService';

enum DateRangeFilter {
  CONSECUTIVE_DAYS = 'consecutive_days',
  ONE_TO_TWO_WEEKS = 'one_to_two_weeks',
  TWO_TO_THREE_WEEKS = 'two_to_three_weeks',
  MONTH_APART = 'month_apart'
}

interface DateRangeFilterOption {
  label: string;
  value: DateRangeFilter;
  description: string;
}

const dateRangeFilters: DateRangeFilterOption[] = [
  {
    label: 'Consecutive Days',
    value: DateRangeFilter.CONSECUTIVE_DAYS,
    description: 'Users who performed actions on consecutive days'
  },
  {
    label: '1-2 Weeks Apart',
    value: DateRangeFilter.ONE_TO_TWO_WEEKS,
    description: 'Users who performed actions 1-2 weeks apart'
  },
  {
    label: '2-3 Weeks Apart',
    value: DateRangeFilter.TWO_TO_THREE_WEEKS,
    description: 'Users who performed actions 2-3 weeks apart'
  },
  {
    label: 'Month Apart',
    value: DateRangeFilter.MONTH_APART,
    description: 'Users who performed actions a month apart'
  }
];

const AnalyticsDashboard: React.FC = () => {
  // Set default start date to January 27th, 2025
  const defaultStartDate = new Date('2025-01-27T00:00:00Z');
  const [startDate, setStartDate] = useState<Date>(defaultStartDate);
  const [endDate, setEndDate] = useState<Date>(new Date());
  const [selectedFilter, setSelectedFilter] = useState<DateRangeFilter>(DateRangeFilter.CONSECUTIVE_DAYS);
  const [loading, setLoading] = useState<boolean>(true);
  const [users, setUsers] = useState<any[]>([]);

  useEffect(() => {
    loadUsers();
  }, [startDate, endDate, selectedFilter]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5001'}/metrics/activity-users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          startDate: startDate.toISOString(),
          endDate: endDate.toISOString(),
          filterType: selectedFilter
        })
      });

      if (response.ok) {
        const data = await response.json();
        setUsers(data.users || []);
      } else {
        console.error('Error loading users:', await response.text());
      }
    } catch (error) {
      console.error('Error loading users:', error);
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
        <h1 className="text-2xl font-bold text-gray-900">User Activity Analytics</h1>
        <div className="flex items-center space-x-4">
          <DateRangeSelector
            startDate={startDate}
            endDate={endDate}
            onDateChange={handleDateChange}
          />
        </div>
      </div>

      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-700 mb-4">Activity Filter</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {dateRangeFilters.map((filter) => (
            <button
              key={filter.value}
              onClick={() => setSelectedFilter(filter.value)}
              className={`p-4 rounded-lg border transition-colors ${
                selectedFilter === filter.value
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="font-medium">{filter.label}</div>
              <div className="text-sm text-gray-500 mt-1">{filter.description}</div>
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-800">User Activity</h2>
            {users.length > 0 && (
              <p className="text-sm text-gray-600 mt-1">
                Showing {users.length} users
              </p>
            )}
          </div>
          
          {users.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              No users found matching the selected criteria
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Email
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
                    <tr key={user.trace_id || index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{user.email}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {new Date(user.firstAction).toLocaleDateString()}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {new Date(user.lastAction).toLocaleDateString()}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {user.daysBetween}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {user.totalActions}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalyticsDashboard;