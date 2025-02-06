import axios from 'axios';
import { MetricResponse, Metric, UserStats } from '../types/metrics';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

export const fetchMetrics = async (
  startDate: Date,
  endDate: Date,
  includeV1: boolean = true
): Promise<MetricResponse> => {
  try {
    const response = await axios.get(`${API_URL}/metrics`, {
      params: {
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
        includeV1
      }
    });

    if (!response.data || !response.data.metrics) {
      console.error('Invalid response format:', response.data);
      throw new Error('Invalid response format from backend');
    }

    // Transform metrics to ensure all required fields are present
    const metrics: Metric[] = response.data.metrics.map((metric: any) => ({
      id: metric.id,
      name: metric.name,
      description: metric.description,
      category: metric.category,
      interval: metric.interval,
      data: {
        value: Number(metric.data.value) || 0,
        previousValue: metric.data.previousValue ? Number(metric.data.previousValue) : undefined,
        trend: metric.data.trend || 'neutral',
        changePercentage: metric.data.changePercentage,
        v1Value: metric.data.v1Value ? Number(metric.data.v1Value) : undefined
      }
    }));

    return {
      metrics,
      timeRange: {
        start: new Date(response.data.timeRange.start),
        end: new Date(response.data.timeRange.end)
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
        trend: 'neutral',
        changePercentage: 0
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
};

export const fetchUserStats = async (
  startDate: Date,
  endDate: Date,
  gaugeType: string
): Promise<UserStats[]> => {
  try {
    const response = await axios.get<{ status: string; data: UserStats[] }>(`${API_URL}/metrics/user-stats`, {
      params: {
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
        gaugeType
      }
    });

    if (response.data.status === 'success' && Array.isArray(response.data.data)) {
      return response.data.data;
    }

    console.error('Invalid response format:', response.data);
    return [];
  } catch (error) {
    console.error('Error fetching user statistics:', error);
    return [];
  }
};

export interface UserEvent {
  event_name: string;
  timestamp: string;
  trace_id: string;
  flow_id?: string;
  [key: string]: any;
}

export interface UserEventsResponse {
  status: string;
  data: UserEvent[];
  timeRange: {
    start: string;
    end: string;
  };
}

export const fetchUserEvents = async (
  userId: string,
  startDate: Date = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // Default to last 30 days
  endDate: Date = new Date()
): Promise<UserEventsResponse> => {
  try {
    const response = await axios.get<UserEventsResponse>(`${API_URL}/metrics/user-events`, {
      params: { 
        traceId: userId,
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString()
      }
    });

    if (response.data.status !== 'success' || !Array.isArray(response.data.data)) {
      console.error('Invalid response format:', response.data);
      throw new Error('Invalid response format from backend');
    }

    return response.data;
  } catch (error) {
    console.error('Error fetching user events:', error);
    throw error;
  }
};