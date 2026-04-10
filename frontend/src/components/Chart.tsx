import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface ChartProps {
  data: Array<{
    timestamp: number;
    close: number;
    equity?: number;
  }>;
  title: string;
  dataKey: string;
  color?: string;
}

const Chart: React.FC<ChartProps> = ({ data, title, dataKey, color = "#8884d8" }) => {
  const chartData = data.map(item => ({
    ...item,
    time: new Date(item.timestamp).toLocaleDateString()
  }));

  return (
    <div className="w-full h-96 bg-white rounded-lg shadow-md p-4">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height="80%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 12 }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            domain={['dataMin', 'dataMax']}
          />
          <Tooltip
            labelFormatter={(label) => `Time: ${label}`}
            formatter={(value: number) => [value.toFixed(2), dataKey]}
          />
          <Line
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default Chart;