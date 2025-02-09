import React from 'react';
import { Metric } from '../../types/metrics';

interface MetricGaugeProps {
  metric: Metric;
  onClick?: () => void;
  className?: string;
}

const MetricGauge: React.FC<MetricGaugeProps> = ({ 
  metric, 
  onClick, 
  className = ''
}) => {
  const value = metric.data.value;

  return (
    <div 
      className={`flex flex-col items-center p-6 ${className} relative bg-white rounded-lg shadow-sm cursor-pointer hover:shadow-md transition-shadow duration-200`}
      onClick={onClick}
    >
      <div className="text-center">
        <div className="text-lg font-medium text-gray-700 mb-3">{metric.name}</div>
        <div className="text-3xl font-bold text-gray-900 mb-2">
          {value.toLocaleString()}
        </div>
        <div className="text-sm text-gray-500">
          {metric.description}
        </div>
      </div>
    </div>
  );
};

export default MetricGauge;
