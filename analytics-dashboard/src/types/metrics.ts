export interface MetricData {
  value: number;
  previousValue?: number;
  trend?: 'up' | 'down' | 'neutral';
  changePercentage?: number;
  target?: number;
  historical?: Array<{
    date: string;
    value: number;
  }>;
}

export interface Metric {
  id: string;
  name: string;
  description: string;
  category: string;
  interval: string;
  data: MetricData;
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