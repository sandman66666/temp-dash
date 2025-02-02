// analytics-dashboard/src/components/metrics/MetricCard.tsx
import React from 'react'
import type { Metric } from '../../types/metrics'

interface MetricCardProps {
  metric: Metric
  onClick?: () => void
}

const MetricCard: React.FC<MetricCardProps> = ({ metric, onClick }) => {
  const { name, data, description } = metric
  const { value } = data

  return (
    <div
      className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 cursor-pointer hover:shadow-md"
      onClick={onClick}
    >
      <div className="flex flex-col gap-2">
        <div>
          <h3 className="text-base font-medium text-gray-900">{name}</h3>
          {description && (
            <p className="text-sm text-gray-500 mt-0.5">{description}</p>
          )}
        </div>
        <div className="mt-2">
          <span className="text-2xl font-semibold text-gray-900">
            {value.toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  )
}

export default MetricCard