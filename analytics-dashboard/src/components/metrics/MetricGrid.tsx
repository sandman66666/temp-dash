// src/components/metrics/MetricGrid.tsx
import { FC } from 'react'
import { Metric } from '../../types/metrics'
import MetricCard from './MetricCard'

interface MetricGridProps {
  metrics: Metric[]
}

const MetricGrid: FC<MetricGridProps> = ({ metrics }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {metrics.map((metric) => (
        <MetricCard key={metric.id} metric={metric} />
      ))}
    </div>
  )
}

export default MetricGrid