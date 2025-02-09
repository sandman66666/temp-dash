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