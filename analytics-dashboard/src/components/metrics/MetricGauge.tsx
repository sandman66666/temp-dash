import React, { useState } from 'react';
import { Metric } from '../../types/metrics';
import { setMetricTarget } from '../../services/metricService';
import { toast } from 'react-toastify';

interface MetricGaugeProps {
  metric: Metric;
  onClick?: () => void;
  size?: 'small' | 'normal';
  className?: string;
  onTargetUpdate?: () => void;
}

const MetricGauge: React.FC<MetricGaugeProps> = ({ 
  metric, 
  onClick, 
  size = 'normal',
  className = '',
  onTargetUpdate
}) => {
  const [showTargetForm, setShowTargetForm] = useState(false);
  const [target, setTarget] = useState<number>(metric.data.target || 0);
  const [isSaving, setIsSaving] = useState(false);

  const value = metric.data.value;
  const percentage = target > 0 ? (value / target) * 100 : 0;

  const getColor = () => {
    if (target === 0) return 'bg-gray-200';
    if (percentage >= 100) return 'bg-green-500';
    if (percentage >= 75) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const handleTargetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await setMetricTarget(metric.id, target);
      toast.success('Target updated successfully');
      setShowTargetForm(false);
      if (onTargetUpdate) {
        onTargetUpdate();
      }
    } catch (error) {
      toast.error('Failed to update target');
      console.error('Error saving target:', error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div 
      className={`flex flex-col items-center p-4 ${className} relative bg-white rounded-lg shadow-sm`}
      style={{ width: size === 'small' ? '200px' : '250px' }}
    >
      <div className="w-full mb-2">
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm font-medium text-gray-700">{metric.name}</span>
          <button 
            onClick={(e) => {
              e.stopPropagation();
              setShowTargetForm(true);
            }}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            Set Target
          </button>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-4">
          <div 
            className={`${getColor()} h-4 rounded-full transition-all duration-500`}
            style={{ width: `${Math.min(percentage, 100)}%` }}
          />
        </div>
      </div>
      <div className="text-center" onClick={onClick}>
        <div className="text-2xl font-bold text-gray-900">
          {value.toLocaleString()}
        </div>
        {target > 0 && (
          <div className="text-sm text-gray-500">
            Target: {target.toLocaleString()} ({Math.round(percentage)}%)
          </div>
        )}
        <div className="text-sm text-gray-500 mt-1">
          {metric.description}
        </div>
      </div>

      {showTargetForm && (
        <div className="absolute top-0 left-0 w-full h-full bg-white bg-opacity-95 p-4 rounded-lg shadow-lg z-10">
          <form onSubmit={handleTargetSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Target Value for {metric.name}
              </label>
              <input
                type="number"
                value={target}
                onChange={(e) => setTarget(Number(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                min="0"
                step="1"
              />
            </div>
            <div className="flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setShowTargetForm(false)}
                className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                disabled={isSaving}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                disabled={isSaving}
              >
                {isSaving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

export default MetricGauge;
