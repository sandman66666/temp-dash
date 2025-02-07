import React, { useState, useEffect } from 'react';
import MetricGrid from '../metrics/MetricGrid';
import DateRangeSelector from '../common/DateRangeSelector';
import UserTable from '../users/UserTable';
import { fetchMetrics } from '../../services/metricService';
import { Metric } from '../../types/metrics';

type GaugeType = 'thread_users' | 'sketch_users' | 'render_users' | 'medium_chat_users' | 'active_chat_users';

const Dashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [startDate, setStartDate] = useState<Date>(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1); // First day of current month
  });
  const [endDate, setEndDate] = useState<Date>(new Date());
  const [selectedMetric, setSelectedMetric] = useState<GaugeType | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadMetrics();
  }, [startDate, endDate]);

  const loadMetrics = async () => {
    try {
      setLoading(true);
      const response = await fetchMetrics(startDate, endDate);
      setMetrics(response.metrics);
    } catch (error) {
      console.error('Error loading metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleMetricClick = (metricId: string) => {
    setSelectedMetric(metricId as GaugeType);
  };

  const handleDateChange = (start: Date, end: Date) => {
    setStartDate(start);
    setEndDate(end);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col space-y-4 mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex-grow">
            <DateRangeSelector
              startDate={startDate}
              endDate={endDate}
              onDateChange={handleDateChange}
            />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      ) : (
        <>
          <MetricGrid metrics={metrics} onMetricClick={handleMetricClick} />
          {selectedMetric && (
            <UserTable 
              gaugeType={selectedMetric}
              timeRange={{
                start: startDate,
                end: endDate
              }}
            />
          )}
        </>
      )}
    </div>
  );
};

export default Dashboard;