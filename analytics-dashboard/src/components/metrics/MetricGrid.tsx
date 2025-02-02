// analytics-dashboard/src/components/metrics/MetricGrid.tsx
import { FC } from 'react'
import { Metric } from '../../types/metrics'
import MetricCard from './MetricCard'

interface MetricGridProps {
  metrics: Metric[]
  onMetricClick: (metricId: string) => void
}

const MetricGrid: FC<MetricGridProps> = ({ metrics, onMetricClick }) => {
  // Define the order of metrics and their display names
  const orderedMetricIds = [
    'descope_users',
    'thread_users',
    'render_users',
    'active_chat_users',
    'medium_chat_users',
    'sketch_users'
  ]

  // Custom display names and descriptions
  const displayConfig: { [key: string]: { name: string; description: string } } = {
    'descope_users': {
      name: 'Total Users',
      description: 'Total number of registered users'
    },
    'thread_users': {
      name: 'Active Users',
      description: 'Users who have started at least one message thread'
    },
    'render_users': {
      name: 'Producers',
      description: 'Users who have completed at least one render'
    },
    'active_chat_users': {
      name: 'Power Users',
      description: 'Users with more than 20 message threads'
    },
    'medium_chat_users': {
      name: 'Moderate Users',
      description: 'Users with 5-20 message threads'
    },
    'sketch_users': {
      name: 'Producers Attempting',
      description: 'Users who have uploaded at least one sketch'
    }
  }

  // Order and transform the metrics
  const orderedMetrics = orderedMetricIds
    .map(id => {
      const metric = metrics.find(m => m.id === id)
      if (!metric) return null

      return {
        ...metric,
        name: displayConfig[id]?.name || metric.name,
        description: displayConfig[id]?.description || metric.description
      }
    })
    .filter(Boolean)

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {orderedMetrics.map(metric => (
        <MetricCard
          key={metric!.id}
          metric={metric!}
          onClick={metric!.id !== 'descope_users' ? () => onMetricClick(metric!.id) : undefined}
        />
      ))}
    </div>
  )
}

export default MetricGrid