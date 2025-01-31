// src/types/metrics.ts
export interface MetricValue {
    value: number
    previousValue?: number
    target?: number
    changePercentage?: number
    trend?: 'up' | 'down' | 'neutral'
  }
  
  export interface Metric {
    id: string
    name: string
    description?: string
    category: 'user' | 'engagement' | 'performance'
    data: MetricValue
    interval: 'daily' | 'weekly' | 'monthly'
  }
  
  export interface MetricTimeRange {
    start: Date
    end: Date
  }
  
  export interface MetricResponse {
    metrics: Metric[]
    timeRange: MetricTimeRange
  }