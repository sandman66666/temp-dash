// src/services/metricService.ts
import axios from 'axios'
import { MetricResponse } from '../types/metrics'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export const fetchMetrics = async (timeRange?: string): Promise<MetricResponse> => {
  // For now, return mock data
  const mockData: MetricResponse = {
    metrics: [
      {
        id: 'total-users',
        name: 'Total Users',
        description: 'Total number of registered users',
        category: 'user',
        interval: 'daily',
        data: {
          value: 12543,
          previousValue: 12100,
          changePercentage: 3.66,
          trend: 'up'
        }
      },
      {
        id: 'active-users',
        name: 'Active Users',
        description: 'Users active in the last 24 hours',
        category: 'engagement',
        interval: 'daily',
        data: {
          value: 1876,
          previousValue: 2100,
          changePercentage: -10.67,
          trend: 'down'
        }
      },
      {
        id: 'renders',
        name: 'Total Renders',
        description: 'Number of successful renders',
        category: 'performance',
        interval: 'daily',
        data: {
          value: 8432,
          previousValue: 7890,
          changePercentage: 6.87,
          trend: 'up'
        }
      }
    ],
    timeRange: {
      start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
      end: new Date()
    }
  }

  // Later, we'll replace this with actual API call
  // const response = await axios.get(`${API_URL}/metrics`, {
  //   params: { timeRange }
  // })
  // return response.data

  return mockData
}