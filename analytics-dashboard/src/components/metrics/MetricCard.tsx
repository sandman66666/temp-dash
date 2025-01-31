// src/components/metrics/MetricCard.tsx
import React from 'react'
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/20/solid' // Note the change to 20/solid
import type { Metric } from '../../types/metrics'

interface MetricCardProps {
  metric: Metric
}

const MetricCard: FC<MetricCardProps> = ({ metric }) => {
  const { name, data, description } = metric
  const { value, changePercentage, trend } = data

  const renderTrend = () => {
    if (!changePercentage) return null

    const isPositive = trend === 'up'
    const color = isPositive ? 'text-green-600' : 'text-red-600'
    const Icon = isPositive ? ArrowUpIcon : ArrowDownIcon

    return (
      <div className={`flex items-center ${color} text-sm`}>
        <Icon className="h-3 w-3 mr-1 flex-shrink-0" aria-hidden="true" />
        <span>{Math.abs(changePercentage)}%</span>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="text-base font-medium text-gray-900">{name}</h3>
          {description && (
            <p className="text-sm text-gray-500 mt-0.5">{description}</p>
          )}
        </div>
        {renderTrend()}
      </div>
      <div className="mt-2">
        <span className="text-2xl font-semibold text-gray-900">
          {value.toLocaleString()}
        </span>
      </div>
    </div>
  )
}

export default MetricCard