import React from 'react';
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/24/solid';
import { Metric } from '../../types/metrics';

interface MetricCardProps {
  metric: Metric;
  onClick?: () => void;
}

const MetricCard: React.FC<MetricCardProps> = ({ metric, onClick }) => {
  const { name, description, data } = metric;
  const showV1Data = metric.id === 'descope_users' || metric.id === 'thread_users';

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    }
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}k`;
    }
    return num.toString();
  };

  const getTrendIcon = () => {
    if (data.trend === 'up') {
      return <ArrowUpIcon className="h-4 w-4 text-green-500" />;
    }
    if (data.trend === 'down') {
      return <ArrowDownIcon className="h-4 w-4 text-red-500" />;
    }
    return null;
  };

  const getTotalValue = () => {
    if (!showV1Data || !data.v1Value) {
      return data.value;
    }
    return data.value + data.v1Value;
  };

  return (
    <div 
      className="bg-white rounded-lg shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow"
      onClick={onClick}
    >
      <div className="flex flex-col space-y-2">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{name}</h3>
            <p className="text-sm text-gray-500">{description}</p>
          </div>
          <div className="flex items-center space-x-1">
            {getTrendIcon()}
          </div>
        </div>
        
        <div className="mt-4">
          <div className="flex flex-col">
            <div className="text-3xl font-bold text-gray-900">
              {formatNumber(data.value)}
            </div>
            {showV1Data && data.v1Value !== undefined && data.v1Value > 0 && (
              <div className="mt-2 flex flex-col">
                <div className="text-sm text-gray-500">
                  With V1: {formatNumber(getTotalValue())}
                </div>
                <div className="text-xs text-gray-400">
                  (V1: +{formatNumber(data.v1Value)})
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetricCard;