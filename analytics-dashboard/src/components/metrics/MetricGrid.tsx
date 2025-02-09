import React from 'react';
import MetricCard from './MetricCard';
import { Metric } from '../../types/metrics';

interface MetricGridProps {
  metrics: Metric[];
  onMetricClick?: (metricId: string) => void;
  isLoading?: boolean;
}

const MetricGrid: React.FC<MetricGridProps> = ({ metrics, onMetricClick, isLoading = false }) => {
  // Separate historical metrics from regular metrics
  const historicalMetrics = metrics.filter(metric => metric.category === 'historical');
  const regularMetrics = metrics.filter(metric => metric.category !== 'historical');

  return (
    <div className="space-y-6">
      {/* Historical metrics row */}
      <div className="space-y-6">
        <div className="grid grid-cols-3 gap-6">
          {historicalMetrics.map((metric) => (
            <MetricCard
              key={metric.id}
              metric={metric}
              onClick={onMetricClick}
              isLoading={false}  // Historical metrics don't show loading state
            />
          ))}
        </div>
        <div className="border-b border-indigo-200"></div>
      </div>

      {/* Regular metrics grid */}
      <div className="grid grid-cols-3 gap-6">
        {regularMetrics.map((metric) => (
          <MetricCard
            key={metric.id}
            metric={metric}
            onClick={onMetricClick}
            isLoading={isLoading}
          />
        ))}
      </div>
    </div>
  );
};

export default MetricGrid;