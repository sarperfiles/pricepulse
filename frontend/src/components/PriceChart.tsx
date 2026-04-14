import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import type { PriceHistory } from '../types';

export type TimeRange = '7d' | '30d' | '90d' | 'all';

interface PriceChartProps {
  data: PriceHistory[];
  currency?: string;
  timeRange: TimeRange;
  onTimeRangeChange: (range: TimeRange) => void;
}

const TIME_RANGES: { value: TimeRange; label: string }[] = [
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
  { value: '90d', label: '90d' },
  { value: 'all', label: 'All' },
];

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

function formatDateTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

interface TooltipPayloadItem {
  value: number;
  payload: { scraped_at: string };
}

// custom tooltip for the chart
function CustomTooltip({
  active,
  payload,
  currency,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  currency: string;
}) {
  if (!active || !payload?.length) return null;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 shadow-xl">
      <p className="text-slate-400 text-xs mb-1">
        {formatDateTime(payload[0].payload.scraped_at)}
      </p>
      <p className="text-white font-semibold text-lg">
        {currency}
        {Number(payload[0].value).toFixed(2)}
      </p>
    </div>
  );
}

export default function PriceChart({ data, currency = '$', timeRange, onTimeRangeChange }: PriceChartProps) {
  const timeRangeButtons = (
    <div className="flex items-center gap-1.5 mb-4">
      {TIME_RANGES.map((r) => (
        <button
          key={r.value}
          onClick={() => onTimeRangeChange(r.value)}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            timeRange === r.value
              ? 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/40'
              : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
          }`}
        >
          {r.label}
        </button>
      ))}
    </div>
  );

  if (data.length === 0) {
    return (
      <div>
        {timeRangeButtons}
        <div className="flex items-center justify-center h-64 text-slate-500">
          No price history available
        </div>
      </div>
    );
  }

  const chartData = data
    .map((item) => ({
      ...item,
      date: formatDate(item.scraped_at),
      priceValue: Number(item.price),
    }))
    .sort((a, b) => new Date(a.scraped_at).getTime() - new Date(b.scraped_at).getTime());

  const prices = chartData.map((d) => d.priceValue);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const padding = (maxPrice - minPrice) * 0.1 || 1;

  return (
    <div>
      {timeRangeButtons}
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
          <defs>
            <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="date"
            stroke="#475569"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="#475569"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            domain={[minPrice - padding, maxPrice + padding]}
            tickFormatter={(value: number) => `${currency}${Number(value).toFixed(0)}`}
          />
          <Tooltip content={<CustomTooltip currency={currency} />} />
          <Area
            type="monotone"
            dataKey="priceValue"
            stroke="#10b981"
            strokeWidth={2}
            fill="url(#priceGradient)"
            dot={false}
            activeDot={{ r: 5, fill: '#10b981', stroke: '#064e3b', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
