import React from 'react';
import { Metric } from '../../types/metrics';

const formatNumber = (num: number | undefined): string => {
  if (num === undefined || num === null) return '0';
  
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}k`;
  }
  
  return num.toString();
};

interface MetricCardProps {
  metric: Metric;
  onClick?: (metricId: string) => void;
  isLoading?: boolean;
}

const MetricCard: React.FC<MetricCardProps> = ({ metric, onClick, isLoading = false }) => {
  const handleClick = () => {
    if (onClick) {
      onClick(metric.id);
    }
  };

  const isHistorical = metric.category === 'historical';

  return (
    <div 
      className={`rounded-lg shadow-sm p-4 hover:shadow-md transition-shadow duration-200 cursor-pointer w-full h-32 relative
        ${isHistorical ? 'bg-gradient-to-br from-blue-50 to-indigo-50 border border-indigo-100' : 'bg-white'}`}
      onClick={handleClick}
    >
      {isLoading && !isHistorical && (
        <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center rounded-lg">
          <div className="animate-spin rounded-full h-6 w-6 border-2 border-indigo-500 border-t-transparent"></div>
        </div>
      )}
      <div className="flex flex-col justify-between h-full">
        <div>
          <h3 className={`text-lg font-semibold mb-1 ${isHistorical ? 'text-indigo-900' : 'text-gray-900'}`}>
            {metric.name}
          </h3>
          <p className={`text-sm mb-2 ${isHistorical ? 'text-indigo-600' : 'text-gray-500'}`}>
            {metric.description}
          </p>
        </div>
        <div className="flex items-end justify-between">
          <div className="flex-grow">
            <div className={`text-2xl font-bold ${isHistorical ? 'text-indigo-900' : 'text-gray-900'}`}>
              {formatNumber(metric.data.value)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetricCard;