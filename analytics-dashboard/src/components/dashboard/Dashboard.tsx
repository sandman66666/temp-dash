import { FC, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchMetrics } from '../../services/metricService'
import MetricGrid from '../metrics/MetricGrid'
import DateRangeSelector from '../common/DateRangeSelector'

const Dashboard: FC = () => {
  // Default to last 7 days
  const defaultEndDate = new Date()
  const defaultStartDate = new Date()
  defaultStartDate.setDate(defaultEndDate.getDate() - 7)

  const [startDate, setStartDate] = useState<Date>(defaultStartDate)
  const [endDate, setEndDate] = useState<Date>(defaultEndDate)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['metrics', startDate, endDate],
    queryFn: () => fetchMetrics(startDate, endDate),
  })

  const handleDateChange = (start: Date, end: Date) => {
    setStartDate(start)
    setEndDate(end)
    refetch()
  }

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
      <div className="mb-4">
        <DateRangeSelector
          startDate={startDate}
          endDate={endDate}
          onDateChange={handleDateChange}
        />
      </div>
      {data && <MetricGrid metrics={data.metrics} />}
    </div>
  )
}

export default Dashboard