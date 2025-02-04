export interface MetricValue {
  value: number;
  previousValue?: number;
  trend?: 'up' | 'down' | 'neutral';
  changePercentage?: number;
  v1Value?: number;
}

export interface Metric {
  id: string;
  name: string;
  description: string;
  category: 'user' | 'engagement' | 'performance';
  interval: 'daily' | 'weekly' | 'monthly';
  data: MetricValue;
}

export interface MetricResponse {
  metrics: Metric[];
  timeRange: {
    start: Date;
    end: Date;
  };
}

export interface UserStats {
  email: string;
  trace_id: string;
  messageCount: number;
  sketchCount: number;
  renderCount: number;
}