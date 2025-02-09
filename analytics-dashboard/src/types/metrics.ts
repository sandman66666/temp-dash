export interface MetricData {
  value?: number;
  previousValue?: number;
  trend: 'up' | 'down' | 'neutral';
  changePercentage?: number;
  v1Value?: number;
  target?: number;
  historical?: Array<{
    date: string;
    value: number;
  }>;
}

export interface UserDetail {
  id: string;
  email: string;
  name: string;
  createdTime: string;
  loginCount: number;
  eventCount: number;
}

export interface UserStats {
  id: string;
  email: string;
  name: string;
  createdTime: string;
  loginCount: number;
  messageCount: number;
  sketchCount: number;
  renderCount: number;
}

export interface Metric {
  id: string;
  name: string;
  description: string;
  category: 'realtime' | 'historical';
  interval: string;
  data: MetricData;
  users?: UserStats[];
}

export interface MetricResponse {
  metrics: Metric[];
  timeRange: {
    start: Date;
    end: Date;
  };
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