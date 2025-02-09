import React, { useState, useEffect } from 'react';
import MetricGrid from '../metrics/MetricGrid';
import DateRangeSelector from '../common/DateRangeSelector';
import UserTable from '../users/UserTable';
import { fetchMetrics } from '../../services/metricService';
import { Metric } from '../../types/metrics';

type GaugeType = 
  | 'active_users' 
  | 'power_users' 
  | 'moderate_users' 
  | 'producers' 
  | 'producers_attempting' 
  | 'total_users_count' 
  | 'new_users';

const Dashboard: React.FC = () => {
  const [historicalMetrics, setHistoricalMetrics] = useState<Metric[]>([]);
  const [dateFilteredMetrics, setDateFilteredMetrics] = useState<Metric[]>([]);
  const [startDate, setStartDate] = useState<Date>(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1); // First day of current month
  });
  const [endDate, setEndDate] = useState<Date>(new Date());
  const [selectedMetric, setSelectedMetric] = useState<GaugeType | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Load historical metrics once on component mount
  useEffect(() => {
    loadHistoricalMetrics();
  }, []);

  // Load date-filtered metrics whenever date range changes
  useEffect(() => {
    loadDateFilteredMetrics();
  }, [startDate, endDate]);

  const loadHistoricalMetrics = async () => {
    try {
      const response = await fetchMetrics(new Date(0), new Date());
      const historical = response.metrics.filter((metric: Metric) => metric.category === 'historical');
      setHistoricalMetrics(historical);
    } catch (error) {
      console.error('Error loading historical metrics:', error);
    }
  };

  const loadDateFilteredMetrics = async () => {
    try {
      setLoading(true);
      const response = await fetchMetrics(startDate, endDate);
      const filtered = response.metrics.filter((metric: Metric) => metric.category !== 'historical')
        .map((metric: Metric) => ({
          ...metric,
          userCount: metric.users?.length || 0
        }));
      setDateFilteredMetrics(filtered);
    } catch (error) {
      console.error('Error loading date-filtered metrics:', error);
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

  // Combine metrics for display, with historical metrics always at the top
  const allMetrics = [...historicalMetrics, ...dateFilteredMetrics];

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

      {loading && allMetrics.length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-indigo-500 border-t-transparent"></div>
        </div>
      ) : (
        <MetricGrid 
          metrics={allMetrics} 
          onMetricClick={handleMetricClick} 
          isLoading={loading}
        />
      )}
      
      {selectedMetric && (
        <UserTable 
          gaugeType={selectedMetric}
          timeRange={{
            start: startDate,
            end: endDate
          }}
        />
      )}
    </div>
  );
};

export default Dashboard;