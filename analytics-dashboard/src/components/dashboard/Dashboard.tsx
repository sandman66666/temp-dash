// analytics-dashboard/src/components/dashboard/Dashboard.tsx
import { FC, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchMetrics } from '../../services/metricService';
import MetricGrid from '../metrics/MetricGrid';
import DateRangeSelector from '../common/DateRangeSelector';
import UserListModal from '../modal/UserListModal';
import UserEventsModal from '../modal/UserEventsModal';

const Dashboard: FC = () => {
  const defaultEndDate = new Date();
  const defaultStartDate = new Date();
  defaultStartDate.setDate(defaultEndDate.getDate() - 7);

  const [startDate, setStartDate] = useState<Date>(defaultStartDate);
  const [endDate, setEndDate] = useState<Date>(defaultEndDate);
  const [showUserListModal, setShowUserListModal] = useState(false);
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
      {data && (
        <MetricGrid
          metrics={data.metrics}
          onMetricClick={(metricId: string) => {
            // For this example, clicking any metric opens the User List Modal.
            setShowUserListModal(true);
          }}
        />
      )}
      <button
        onClick={() => setShowUserListModal(true)}
        className="px-4 py-2 bg-blue-500 text-white rounded"
      >
        View Users
      </button>
      {showUserListModal && (
        <UserListModal
          onClose={() => setShowUserListModal(false)}
          onSelectUser={(user) => {
            setSelectedUser(user);
            setShowUserListModal(false);
          }}
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