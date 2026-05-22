import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Package, Bell, TrendingDown, TrendingUp, Plus, Loader2, AlertCircle } from 'lucide-react';
import { getProducts, createProduct } from '../api/products';
import { getUnreadCount } from '../api/notifications';
import { getPriceStats } from '../api/priceHistory';
import { useToast } from '../context/ToastContext';
import { DashboardSkeleton } from '../components/Skeleton';
import { formatRelativeTime } from '../utils/formatTime';
import type { Product, ProductCreateData, PriceStats } from '../types';

export default function DashboardPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [priceChanges, setPriceChanges] = useState<Map<number, PriceStats>>(new Map());

  const [showQuickAdd, setShowQuickAdd] = useState(false);
  const [newUrl, setNewUrl] = useState('');
  const [addLoading, setAddLoading] = useState(false);

  const { addToast } = useToast();

  const loadData = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError('');
    try {
      const [prodRes, notifCount] = await Promise.all([
        getProducts(),
        getUnreadCount().catch(() => 0),
      ]);
      setProducts(prodRes.items);
      setUnreadCount(notifCount);

      const withPrices = prodRes.items
        .filter((p: Product) => p.last_scraped_at && p.current_price !== null)
        .sort(
          (a: Product, b: Product) =>
            new Date(b.last_scraped_at!).getTime() - new Date(a.last_scraped_at!).getTime()
        )
        .slice(0, 5);

      const statsResults = await Promise.all(
        withPrices.map((p: Product) =>
          getPriceStats(String(p.id))
            .then((stats) => [p.id, stats] as const)
            .catch(() => null)
        )
      );
      const statsMap = new Map<number, PriceStats>();
      for (const result of statsResults) {
        if (result) statsMap.set(result[0], result[1]);
      }
      setPriceChanges(statsMap);
    } catch {
      if (!silent) setError('Failed to load dashboard data');
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (!document.hidden) loadData(true);
    }, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  useEffect(() => {
    if (!showQuickAdd) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setShowQuickAdd(false);
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [showQuickAdd]);

  async function handleQuickAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newUrl.trim()) return;
    setAddLoading(true);
    try {
      const data: ProductCreateData = { url: newUrl };
      const product = await createProduct(data);
      setProducts((prev) => [product, ...prev]);
      setNewUrl('');
      setShowQuickAdd(false);
      addToast('Product added', 'success');
    } catch {
      setError('Failed to add product');
    } finally {
      setAddLoading(false);
    }
  }

  const recentlyScraped = products
    .filter((p) => p.last_scraped_at && p.current_price !== null)
    .sort(
      (a, b) =>
        new Date(b.last_scraped_at!).getTime() - new Date(a.last_scraped_at!).getTime()
    )
    .slice(0, 5);

  const activeProducts = products.filter((p) => p.is_active).length;

  if (loading) {
    return <DashboardSkeleton />;
  }

  // calc avg price
  const avgPrice = products.length > 0
    ? (
        products
          .filter((p) => p.current_price !== null)
          .reduce((sum, p) => sum + Number(p.current_price || 0), 0) /
          Math.max(products.filter((p) => p.current_price !== null).length, 1)
      ).toFixed(2)
    : '0.00';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 mt-1">Your price monitoring overview</p>
        </div>
        <button
          onClick={() => setShowQuickAdd(true)}
          className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={16} />
          Quick Add
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-blue-500/15 p-2 rounded-lg">
              <Package size={18} className="text-blue-400" />
            </div>
            <span className="text-sm text-slate-400">Products Tracked</span>
          </div>
          <p className="text-3xl font-bold text-white">{products.length}</p>
          <p className="text-xs text-slate-500 mt-1">{activeProducts} active</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-amber-500/15 p-2 rounded-lg">
              <TrendingDown size={18} className="text-amber-400" />
            </div>
            <span className="text-sm text-slate-400">Avg. Price Tracked</span>
          </div>
          <p className="text-3xl font-bold text-white">
            ${avgPrice}
          </p>
          <p className="text-xs text-slate-500 mt-1">across all products</p>
        </div>

        <Link to="/notifications" className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors">
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-red-500/15 p-2 rounded-lg">
              <Bell size={18} className="text-red-400" />
            </div>
            <span className="text-sm text-slate-400">Unread Notifications</span>
          </div>
          <p className="text-3xl font-bold text-white">{unreadCount}</p>
          <p className="text-xs text-slate-500 mt-1">click to view</p>
        </Link>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl">
        <div className="p-5 border-b border-slate-800">
          <h2 className="text-lg font-semibold text-white">Recently Scraped</h2>
        </div>
        {recentlyScraped.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            No recent price data. Add products to start tracking.
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {recentlyScraped.map((product) => (
              <Link
                key={product.id}
                to={`/products/${product.id}`}
                className="flex items-center justify-between px-5 py-4 hover:bg-slate-800/50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium truncate">{product.name}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {product.last_scraped_at
                      ? formatRelativeTime(product.last_scraped_at)
                      : 'Never'}
                  </p>
                </div>
                <p className="text-lg font-semibold text-white ml-4">
                  {product.currency || '$'}
                  {Number(product.current_price).toFixed(2)}
                </p>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl">
        <div className="p-5 border-b border-slate-800">
          <h2 className="text-lg font-semibold text-white">Biggest Price Changes</h2>
        </div>
        {recentlyScraped.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            No price data available yet.
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {recentlyScraped.map((product) => {
              const stats = priceChanges.get(product.id);
              const change24h = stats?.price_change_24h;
              return (
                <Link
                  key={product.id}
                  to={`/products/${product.id}`}
                  className="flex items-center justify-between px-5 py-4 hover:bg-slate-800/50 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium truncate">{product.name}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{product.platform || 'Unknown'}</p>
                  </div>
                  <div className="flex items-center gap-3 ml-4">
                    <p className="text-lg font-semibold text-white">
                      {product.currency || '$'}
                      {Number(product.current_price).toFixed(2)}
                    </p>
                    {change24h !== null && change24h !== undefined && change24h !== 0 && (
                      <span
                        className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${
                          change24h < 0
                            ? 'bg-emerald-500/15 text-emerald-400'
                            : 'bg-red-500/15 text-red-400'
                        }`}
                      >
                        {change24h < 0 ? (
                          <TrendingDown size={12} />
                        ) : (
                          <TrendingUp size={12} />
                        )}
                        {Math.abs(change24h).toFixed(1)}%
                      </span>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>

      {showQuickAdd && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-md">
            <div className="p-5 border-b border-slate-800">
              <h3 className="text-lg font-semibold text-white">Quick Add Product</h3>
            </div>
            <form onSubmit={handleQuickAdd} className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Product URL
                </label>
                <input
                  type="url"
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  placeholder="https://amazon.com/dp/..."
                  required
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 placeholder:text-slate-600"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowQuickAdd(false)}
                  className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addLoading}
                  className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                >
                  {addLoading ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      Adding...
                    </>
                  ) : (
                    'Add Product'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
