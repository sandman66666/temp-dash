// src/services/metricService.ts
import axios from 'axios'
import { MetricResponse } from '../types/metrics'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001'

export const fetchMetrics = async (timeRange?: string): Promise<MetricResponse> => {
  try {
    const response = await axios.get(`${API_URL}/metrics`, {
      params: { timeRange }
    });

    // Transform backend data to match our frontend format
    const backendData = response.data;
    const metrics = Object.entries(backendData.data).map(([id, metricData]: [string, any]) => ({
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
        start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
        end: new Date()
      }
    };
  } catch (error) {
    console.error('Error fetching metrics:', error);
    // Return empty data if the API fails
    return {
      metrics: [],
      timeRange: {
        start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
        end: new Date()
      }
    };
  }
}