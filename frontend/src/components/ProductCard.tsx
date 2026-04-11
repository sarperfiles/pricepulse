import { Link } from 'react-router-dom';
import { ExternalLink, Clock, Pause, Play, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { getFaviconUrl } from '../utils/favicon';
import { formatRelativeTime } from '../utils/formatTime';
import type { Product } from '../types';

interface ProductCardProps {
  product: Product;
  selected?: boolean;
  onSelect?: (id: number) => void;
  onToggleActive?: (id: number, isActive: boolean) => void;
  priceTrend?: 'up' | 'down' | 'flat' | null;
}

function truncateUrl(url: string, maxLen = 40): string {
  try {
    const parsed = new URL(url);
    let display = parsed.hostname + parsed.pathname;
    return display.length > maxLen ? display.slice(0, maxLen) + '...' : display;
  } catch {
    return url.length > maxLen ? url.slice(0, maxLen) + '...' : url;
  }
}

function PriceTrendBadge({ trend }: { trend: 'up' | 'down' | 'flat' | null }) {
  if (!trend) return null;
  if (trend === 'down') {
    return (
      <span className="inline-flex items-center gap-0.5 text-xs font-medium text-emerald-400">
        <TrendingDown size={12} />
      </span>
    );
  }
  if (trend === 'up') {
    return (
      <span className="inline-flex items-center gap-0.5 text-xs font-medium text-red-400">
        <TrendingUp size={12} />
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-0.5 text-xs font-medium text-slate-500">
      <Minus size={12} />
    </span>
  );
}

export default function ProductCard({ product, selected, onSelect, onToggleActive, priceTrend }: ProductCardProps) {
  // console.log('rendering card:', product.id);
  let priceDisplay = product.current_price !== null
    ? `${product.currency || '$'}${Number(product.current_price).toFixed(2)}`
    : 'N/A';

  return (
    <div className="relative bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all hover:shadow-lg hover:shadow-slate-950/50 group">
      {onSelect && (
        <div className="absolute top-3 left-3">
          <input
            type="checkbox"
            checked={selected || false}
            onChange={() => onSelect(product.id)}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500/50 focus:ring-offset-0 cursor-pointer"
          />
        </div>
      )}

      <div className="flex items-start justify-between mb-3">
        <Link to={`/products/${product.id}`} className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <img
              src={getFaviconUrl(product.url)}
              alt=""
              className="w-4 h-4 rounded-sm flex-shrink-0"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
            <h3 className="text-white font-medium truncate group-hover:text-emerald-400 transition-colors">
              {product.name}
            </h3>
          </div>
          <p className="text-slate-500 text-sm flex items-center gap-1 mt-1">
            <ExternalLink size={12} />
            {truncateUrl(product.url)}
          </p>
        </Link>
        <div className="flex items-center gap-2 ml-2">
          {onToggleActive && (
            <button
              onClick={(e) => { e.preventDefault(); onToggleActive(product.id, !product.is_active); }}
              className={`p-1 rounded transition-colors ${
                product.is_active
                  ? 'text-slate-400 hover:text-yellow-400 hover:bg-yellow-500/10'
                  : 'text-yellow-400 hover:text-emerald-400 hover:bg-emerald-500/10'
              }`}
              title={product.is_active ? 'Pause tracking' : 'Resume tracking'}
            >
              {product.is_active ? <Pause size={14} /> : <Play size={14} />}
            </button>
          )}
          {product.is_active ? (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400">
              Active
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-700 text-slate-400">
              Paused
            </span>
          )}
        </div>
      </div>

      <div className="flex items-end justify-between">
        <Link to={`/products/${product.id}`} className="block">
          <div className="flex items-center gap-2">
            <p className="text-2xl font-bold text-white">
              {priceDisplay}
            </p>
            <PriceTrendBadge trend={priceTrend ?? null} />
          </div>
          <p className="text-slate-500 text-xs flex items-center gap-1 mt-1">
            <Clock size={12} />
            {product.last_scraped_at ? formatRelativeTime(product.last_scraped_at) : 'Never'}
          </p>
        </Link>
        {product.platform && (
          <span className="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded">
            {product.platform}
          </span>
        )}
      </div>
    </div>
  );
}
