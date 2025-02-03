import axios from 'axios'
import { MetricResponse, Metric } from '../types/metrics'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001'

export interface GaugeUser {
  email: string;
  trace_id: string;
}

export const fetchMetrics = async (startDate: Date, endDate: Date): Promise<MetricResponse> => {
  try {
    const response = await axios.get(`${API_URL}/metrics`, {
      params: { 
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString()
      }
    });

    const backendData = response.data;
    
    if (!backendData || !backendData.metrics || !Array.isArray(backendData.metrics)) {
      throw new Error('Invalid response format from backend');
    }

    // Transform metrics while preserving all the data from backend
    const metrics: Metric[] = backendData.metrics.map((metricData: any) => ({
      id: metricData.id,
      name: metricData.name || metricData.id.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '),
      description: metricData.description || '',
      category: metricData.category || 'user',
      interval: 'daily',
      data: {
        value: Number(metricData.data.value) || 0,
        previousValue: metricData.data.previousValue ? Number(metricData.data.previousValue) : undefined,
        trend: metricData.data.trend || 'neutral',
        changePercentage: metricData.data.changePercentage
      }
    }));

    // Ensure all required metrics are present with correct IDs
    const requiredMetrics = [
      'descope_users',
      'thread_users',
      'render_users',
      'active_chat_users',
      'medium_chat_users',
      'sketch_users'
    ];

    // Add any missing metrics with zero values
    requiredMetrics.forEach(metricId => {
      if (!metrics.find(m => m.id === metricId)) {
        metrics.push({
          id: metricId,
          name: metricId.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '),
          description: 'No data available',
          category: metricId.includes('chat') || metricId === 'thread_users' ? 'engagement' : 'user',
          interval: 'daily',
          data: {
            value: 0,
            trend: 'neutral'
          }
        });
      }
    });

    // Sort metrics to match the order in MetricGrid
    metrics.sort((a, b) => {
      const order = requiredMetrics.indexOf(a.id) - requiredMetrics.indexOf(b.id);
      return order;
    });

    // Log the transformed metrics for debugging
    console.log('Backend data:', backendData);
    console.log('Transformed metrics:', metrics);

    return {
      metrics,
      timeRange: {
        start: new Date(backendData.timeRange.start),
        end: new Date(backendData.timeRange.end)
      }
    };
  } catch (error) {
    console.error('Error fetching metrics:', error);
    // Return empty data with all required metrics if the API fails
    const emptyMetrics: Metric[] = [
      'descope_users',
      'thread_users',
      'render_users',
      'active_chat_users',
      'medium_chat_users',
      'sketch_users'
    ].map(id => ({
      id,
      name: id.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '),
      description: 'Error loading data',
      category: id.includes('chat') || id === 'thread_users' ? 'engagement' : 'user',
      interval: 'daily',
      data: {
        value: 0,
        trend: 'neutral'
      }
    }));

    return {
      metrics: emptyMetrics,
      timeRange: {
        start: startDate,
        end: endDate
      }
    };
  }
}

export const fetchPowerUsers = async (startDate: Date, endDate: Date): Promise<GaugeUser[]> => {
  try {
    const response = await axios.get(`${API_URL}/metrics/gauge-users`, {
      params: {
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString()
      }
    });

    if (response.data.status === 'success') {
      // The backend now returns an array of objects with email and trace_id
      return response.data.data;
    }
    return [];
  } catch (error) {
    console.error('Error fetching power users:', error);
    return [];
  }
}