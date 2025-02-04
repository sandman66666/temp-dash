import React, { useState, useEffect } from 'react';
import MetricGrid from '../metrics/MetricGrid';
import DateRangeSelector from '../common/DateRangeSelector';
import UserTable from '../users/UserTable';
import { fetchMetrics } from '../../services/metricService';
import { Metric } from '../../types/metrics';

const Dashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [startDate, setStartDate] = useState<Date>(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000));
  const [endDate, setEndDate] = useState<Date>(new Date());
  const [includeV1, setIncludeV1] = useState<boolean>(true);
  const [selectedMetric, setSelectedMetric] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadMetrics();
  }, [startDate, endDate, includeV1]);

  const loadMetrics = async () => {
    try {
      setLoading(true);
      const response = await fetchMetrics(startDate, endDate, includeV1);
      setMetrics(response.metrics);
    } catch (error) {
      console.error('Error loading metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleMetricClick = (metricId: string) => {
    setSelectedMetric(metricId);
  };

  const handleDateChange = (start: Date, end: Date) => {
    setStartDate(start);
    setEndDate(end);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
        <div className="flex items-center space-x-4">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={includeV1}
              onChange={(e) => setIncludeV1(e.target.checked)}
              className="form-checkbox h-4 w-4 text-blue-600"
            />
            <span className="text-sm text-gray-700">Include V1</span>
          </label>
          <DateRangeSelector
            startDate={startDate}
            endDate={endDate}
            onDateChange={handleDateChange}
          />
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
              gaugeType={selectedMetric as any}
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