import { FC } from 'react'
import { Metric } from '../../types/metrics'
import MetricGauge from './MetricGauge'

interface MetricGridProps {
  metrics: Metric[]
  onMetricClick: (metricId: string) => void
}

const MetricGrid: FC<MetricGridProps> = ({ metrics, onMetricClick }) => {
  const orderedMetrics = metrics
    .map(metric => metric)
    .sort((a, b) => {
      if (a.category === b.category) {
        return 0;
      }
      if (a.category === 'user') {
        return -1;
      }
      if (b.category === 'user') {
        return 1;
      }
      return 0;
    })
    .filter(Boolean);

  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {orderedMetrics.filter(metric => metric.category !== 'historical').map(metric => (
          <div key={metric!.id} className="flex flex-col items-center">
            <MetricGauge metric={metric!} onClick={() => onMetricClick(metric!.id)} />
          </div>
        ))}
      </div>
      
      {/* Historical Metrics Section */}
      <div className="mt-12 border-t pt-8">
        <h2 className="text-xl font-semibold mb-6 text-center">Historical Totals (V1 + Current)</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {orderedMetrics.filter(metric => metric.category === 'historical').map(metric => (
            <div key={metric!.id} className="flex flex-col items-center">
              <MetricGauge 
                metric={metric!}
                size="small"
                className="transform scale-75"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default MetricGrid