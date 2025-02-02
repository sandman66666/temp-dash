import axios from 'axios'
import { MetricResponse } from '../types/metrics'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001'

export const fetchMetrics = async (startDate: Date, endDate: Date): Promise<MetricResponse> => {
  try {
    const response = await axios.get(`${API_URL}/metrics`, {
      params: { 
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString()
      }
    });

    // Use an empty object as fallback in case data is undefined
    const backendData = response.data;
    const metrics = Object.entries(backendData.data || {}).map(([id, metricData]: [string, any]) => ({
      id,
      name: metricData.label,
      description: metricData.description,
      category: id.includes('user') ? 'user' : 'engagement',
      interval: 'daily',
      data: {
        value: metricData.value
      }
    }));

    return {
      metrics,
      timeRange: {
        start: new Date(backendData.timeRange.start),
        end: new Date(backendData.timeRange.end)
      }
    };
  } catch (error) {
    console.error('Error fetching metrics:', error);
    // Return empty data if the API fails
    return {
      metrics: [],
      timeRange: {
        start: startDate,
        end: endDate
      }
    };
  }
}