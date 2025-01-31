// src/components/dashboard/Dashboard.tsx
import { FC } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchMetrics } from '../../services/metricService'
import MetricGrid from '../metrics/MetricGrid'

const Dashboard: FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => fetchMetrics('7d'),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-gray-500">Loading metrics...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-red-500">Error loading metrics</div>
      </div>
    )
  }

  return (
    <div className="space-y-6 pt-16">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <div className="text-sm text-gray-500">
          Last updated: {new Date().toLocaleString()}
        </div>
      </div>
      
      {data && <MetricGrid metrics={data.metrics} />}
    </div>
  )
}

export default Dashboard