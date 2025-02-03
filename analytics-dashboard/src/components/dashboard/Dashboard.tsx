// analytics-dashboard/src/components/dashboard/Dashboard.tsx
import { FC, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchMetrics } from '../../services/metricService';
import MetricGrid from '../metrics/MetricGrid';
import DateRangeSelector from '../common/DateRangeSelector';
import UserListModal from '../modal/UserListModal';
import UserEventsModal from '../modal/UserEventsModal';

type GaugeType = 'thread_users' | 'sketch_users' | 'render_users' | 'medium_chat_users' | 'active_chat_users';

const Dashboard: FC = () => {
  const defaultEndDate = new Date();
  const defaultStartDate = new Date();
  defaultStartDate.setDate(defaultEndDate.getDate() - 7);

  const [startDate, setStartDate] = useState<Date>(defaultStartDate);
  const [endDate, setEndDate] = useState<Date>(defaultEndDate);
  const [showUserListModal, setShowUserListModal] = useState(false);
  const [userListMode, setUserListMode] = useState<'regular' | 'power'>('regular');
  const [selectedGaugeType, setSelectedGaugeType] = useState<GaugeType>('thread_users');
  const [selectedUser, setSelectedUser] = useState<{ userId: string, email: string } | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['metrics', startDate, endDate],
    queryFn: () => fetchMetrics(startDate, endDate),
  });

  const handleDateChange = (start: Date, end: Date) => {
    setStartDate(start);
    setEndDate(end);
    refetch();
  };

  const handleMetricClick = (metricId: string) => {
    // Map metric IDs to their corresponding gauge types
    const gaugeTypeMap: { [key: string]: GaugeType } = {
      'thread_users': 'thread_users',
      'sketch_users': 'sketch_users',
      'render_users': 'render_users',
      'medium_chat_users': 'medium_chat_users',
      'active_chat_users': 'active_chat_users'
    };

    const gaugeType = gaugeTypeMap[metricId];
    if (gaugeType) {
      setSelectedGaugeType(gaugeType);
      setUserListMode('power');
      setShowUserListModal(true);
    }
  };

  return (
    <div className="space-y-6 pt-16">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <div className="text-sm text-gray-500">
          Last updated: {new Date().toLocaleString()}
        </div>
      </div>
      <div className="mb-4">
        <DateRangeSelector
          startDate={startDate}
          endDate={endDate}
          onDateChange={handleDateChange}
        />
      </div>
      {isLoading && (
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      )}
      {error && (
        <div className="bg-red-50 text-red-500 p-4 rounded-md">
          Error loading metrics. Please try again.
        </div>
      )}
      {data && (
        <MetricGrid
          metrics={data.metrics}
          onMetricClick={handleMetricClick}
        />
      )}
      {showUserListModal && (
        <UserListModal
          onClose={() => {
            setShowUserListModal(false);
            setSelectedGaugeType('thread_users'); // Reset to default
          }}
          onSelectUser={(user) => {
            setSelectedUser(user);
            setShowUserListModal(false);
          }}
          mode={userListMode}
          gaugeType={selectedGaugeType}
          timeRange={userListMode === 'power' ? { start: startDate, end: endDate } : undefined}
        />
      )}
      {selectedUser && (
        <UserEventsModal
          userId={selectedUser.userId}
          onClose={() => setSelectedUser(null)}
        />
      )}
    </div>
  );
};

export default Dashboard;