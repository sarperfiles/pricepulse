import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ExternalLink,
  RefreshCw,
  Trash2,
  Plus,
  Loader2,
  AlertCircle,
  TrendingDown,
  TrendingUp,
  ShieldAlert,
  Download,
  Check,
  Copy,
  Pencil,
} from 'lucide-react';
import { getProduct, deleteProduct, triggerScrape, updateProduct } from '../api/products';
import { getPriceHistory, getPriceStats } from '../api/priceHistory';
import { getAlertRules, createAlertRule, deleteAlertRule } from '../api/alertRules';
import PriceChart from '../components/PriceChart';
import EditProductModal from '../components/EditProductModal';
import AlertRuleForm from '../components/AlertRuleForm';
import ConfirmDialog from '../components/ConfirmDialog';
import Breadcrumb from '../components/Breadcrumb';
import { DetailPageSkeleton } from '../components/Skeleton';
import { useToast } from '../context/ToastContext';
import { formatRelativeTime, formatDateTime } from '../utils/formatTime';
import type { TimeRange } from '../components/PriceChart';
import type { Product, PriceHistory, PriceStats, AlertRule, AlertRuleCreateData } from '../types';

function ruleTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    price_below: 'Price Below',
    price_above: 'Price Above',
    price_change_pct: 'Price Change %',
    price_drop: 'Any Price Drop',
  };
  return labels[type] || type;
}

function filterByTimeRange(data: PriceHistory[], range: TimeRange): PriceHistory[] {
  if (range === 'all') return data;
  const days = range === '7d' ? 7 : range === '30d' ? 30 : 90;
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  return data.filter((entry) => new Date(entry.scraped_at) >= cutoff);
}

const INTERVAL_OPTIONS = [
  { value: '1h', label: '1 hour' },
  { value: '6h', label: '6 hours' },
  { value: '12h', label: '12 hours' },
  { value: '24h', label: '24 hours' },
];

export default function ProductDetailPage() {
  const { id: productId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();

  const [product, setProduct] = useState<Product | null>(null);
  const [priceHistory, setPriceHistory] = useState<PriceHistory[]>([]);
  const [priceStats, setPriceStats] = useState<PriceStats | null>(null);
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [scraping, setScraping] = useState(false);
  const [showAlertForm, setShowAlertForm] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [timeRange, setTimeRange] = useState<TimeRange>('all');
  const [retryScraping, setRetryScraping] = useState(false);
  const [intervalUpdating, setIntervalUpdating] = useState(false);
  const [intervalSuccess, setIntervalSuccess] = useState(false);
  const [confirmDeleteProduct, setConfirmDeleteProduct] = useState(false);
  const [confirmDeleteRuleId, setConfirmDeleteRuleId] = useState<number | null>(null);

  const loadAll = useCallback(async (silent = false) => {
    if (!productId) return;
    if (!silent) setLoading(true);
    setError('');
    try {
      const [prod, history, stats, rules] = await Promise.all([
        getProduct(productId),
        getPriceHistory(productId, { limit: 100 }).catch(() => []),
        getPriceStats(productId).catch(() => null),
        getAlertRules(productId).catch(() => []),
      ]);
      setProduct(prod);
      setPriceHistory(history);
      setPriceStats(stats);
      setAlertRules(rules);
    } catch {
      if (!silent) setError('Failed to load product details');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (!document.hidden) loadAll(true);
    }, 30000);
    return () => clearInterval(interval);
  }, [loadAll]);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        if (showAlertForm) setShowAlertForm(false);
        if (showEditModal) setShowEditModal(false);
        if (confirmDeleteProduct) setConfirmDeleteProduct(false);
        if (confirmDeleteRuleId !== null) setConfirmDeleteRuleId(null);
      }
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [showAlertForm, showEditModal, confirmDeleteProduct, confirmDeleteRuleId]);

  async function handleScrape() {
    setScraping(true);
    try {
      await triggerScrape(productId!);
      addToast('Scrape triggered', 'success');
      setTimeout(() => loadAll(true), 2000);
    } catch {
      setError('Failed to trigger scrape');
    } finally {
      setScraping(false);
    }
  }

  async function handleRetryScrape() {
    setRetryScraping(true);
    setError('');
    try {
      await triggerScrape(productId!);
      addToast('Scrape triggered', 'success');
      setTimeout(async () => {
        await loadAll(true);
        setRetryScraping(false);
      }, 10000);
    } catch {
      setError('Failed to trigger scrape');
      setRetryScraping(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteProduct(productId!);
      addToast('Product deleted', 'success');
      navigate('/products');
    } catch {
      setError('Failed to delete product');
      setDeleting(false);
    }
  }

  async function handleCreateAlert(data: AlertRuleCreateData) {
    if (!productId) return;
    const rule = await createAlertRule(productId, data);
    setAlertRules((prev) => [...prev, rule]);
    addToast('Alert rule added', 'success');
  }

  async function handleDeleteAlert(ruleId: number) {
    await deleteAlertRule(String(ruleId));
    setAlertRules((prev) => prev.filter((r) => r.id !== ruleId));
    addToast('Alert rule deleted', 'success');
  }

  function handleCopyUrl() {
    if (!product) return;
    navigator.clipboard.writeText(product.url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  // hack - building csv manually
  function handleExportCsv() {
    if (!product || priceHistory.length === 0) return;

    const sorted = [...priceHistory].sort(
      (a, b) => new Date(b.scraped_at).getTime() - new Date(a.scraped_at).getTime()
    );

    const rows = [
      ['Date', 'Price', 'Currency', 'Status'],
      ...sorted.map((entry) => [
        new Date(entry.scraped_at).toISOString(),
        Number(entry.price).toFixed(2),
        entry.currency,
        'OK',
      ]),
    ];

    const csv = rows.map((row) => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const safeName = product.name.replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase();
    link.href = url;
    link.download = safeName + '-price-history.csv';
    link.click();
    URL.revokeObjectURL(url);
  }

  async function handleIntervalChange(newInterval: string) {
    if (!product || !productId) return;
    setIntervalUpdating(true);
    setIntervalSuccess(false);
    try {
      const updated = await updateProduct(productId, { scrape_interval: newInterval });
      setProduct(updated);
      setIntervalSuccess(true);
      setTimeout(() => setIntervalSuccess(false), 2000);
    } catch {
      setError('Failed to update scrape interval');
    } finally {
      setIntervalUpdating(false);
    }
  }

  function handleProductSaved(updated: Product) {
    setProduct(updated);
  }

  const filteredHistory = filterByTimeRange(priceHistory, timeRange);

  if (loading) {
    return <DetailPageSkeleton />;
  }

  if (!product) {
    return (
      <div className="text-center py-16">
        <p className="text-slate-400">Product not found</p>
        <button
          onClick={() => navigate('/products')}
          className="mt-4 text-emerald-400 hover:text-emerald-300 text-sm"
        >
          Back to products
        </button>
      </div>
    );
  }

  const scrapeFailed = product.current_price === null && product.last_scraped_at;

  return (
    <div className="space-y-6">
      <Breadcrumb
        items={[
          { label: 'Home', href: '/' },
          { label: 'Products', href: '/products' },
          { label: product.name },
        ]}
      />
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{product.name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 text-sm hover:text-emerald-400 flex items-center gap-1 transition-colors"
            >
              {product.url}
              <ExternalLink size={12} />
            </a>
            <button
              onClick={handleCopyUrl}
              className="relative text-slate-500 hover:text-emerald-400 transition-colors"
              title="Copy URL"
            >
              {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
              {copied && (
                <span className="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-emerald-400 text-xs px-2 py-1 rounded whitespace-nowrap">
                  Copied!
                </span>
              )}
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowEditModal(true)}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <Pencil size={14} />
            Edit
          </button>
          <button
            onClick={handleScrape}
            disabled={scraping}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={scraping ? 'animate-spin' : ''} />
            {scraping ? 'Scraping...' : 'Scrape Now'}
          </button>
          <button
            onClick={() => setConfirmDeleteProduct(true)}
            disabled={deleting}
            className="flex items-center gap-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            <Trash2 size={14} />
            Delete
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {scrapeFailed && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle size={16} />
            Last scrape failed to extract a price. The site may be blocking requests or the page structure isn't recognized.
          </div>
          <button
            onClick={handleRetryScrape}
            disabled={retryScraping}
            className="flex items-center gap-2 bg-red-500/20 hover:bg-red-500/30 text-red-300 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 shrink-0 ml-4"
          >
            <RefreshCw size={14} className={retryScraping ? 'animate-spin' : ''} />
            {retryScraping ? 'Retrying...' : 'Retry Scrape'}
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <p className="text-sm text-slate-400 mb-1">Current Price</p>
          <p className={`text-3xl font-bold ${scrapeFailed ? 'text-red-400' : 'text-white'}`}>
            {product.current_price !== null
              ? `${product.currency || '$'}${Number(product.current_price).toFixed(2)}`
              : product.last_scraped_at
                ? 'Failed'
                : 'N/A'}
          </p>
        </div>
        {priceStats && (
          <>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <p className="text-sm text-slate-400 mb-1">Lowest Price</p>
              <p className="text-2xl font-bold text-emerald-400 flex items-center gap-1">
                <TrendingDown size={18} />
                {product.currency || '$'}{Number(priceStats.min_price).toFixed(2)}
              </p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <p className="text-sm text-slate-400 mb-1">Highest Price</p>
              <p className="text-2xl font-bold text-red-400 flex items-center gap-1">
                <TrendingUp size={18} />
                {product.currency || '$'}{Number(priceStats.max_price).toFixed(2)}
              </p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <p className="text-sm text-slate-400 mb-1">Average Price</p>
              <p className="text-2xl font-bold text-white">
                {product.currency || '$'}{Number(priceStats.avg_price).toFixed(2)}
              </p>
            </div>
          </>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/50 border border-slate-800/50 rounded-lg p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Platform</p>
          <p className="text-white mt-1">{product.platform || 'Unknown'}</p>
        </div>
        <div className="bg-slate-900/50 border border-slate-800/50 rounded-lg p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Scrape Interval</p>
          <div className="flex items-center gap-2 mt-1">
            <select
              value={product.scrape_interval || '6h'}
              onChange={(e) => handleIntervalChange(e.target.value)}
              disabled={intervalUpdating}
              className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-white text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500/50 disabled:opacity-50"
            >
              {INTERVAL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            {intervalUpdating && <Loader2 size={14} className="animate-spin text-slate-400" />}
            {intervalSuccess && <Check size={14} className="text-emerald-400" />}
          </div>
        </div>
        <div className="bg-slate-900/50 border border-slate-800/50 rounded-lg p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Last Scraped</p>
          <p className="text-white mt-1 text-sm">
            {product.last_scraped_at ? formatRelativeTime(product.last_scraped_at) : 'Never'}
          </p>
        </div>
        <div className="bg-slate-900/50 border border-slate-800/50 rounded-lg p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Status</p>
          <span
            className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${
              product.is_active
                ? 'bg-emerald-500/15 text-emerald-400'
                : 'bg-slate-700 text-slate-400'
            }`}
          >
            {product.is_active ? 'Active' : 'Paused'}
          </span>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4">Price History</h2>
        <PriceChart
          data={filteredHistory}
          currency={product.currency || '$'}
          timeRange={timeRange}
          onTimeRangeChange={setTimeRange}
        />
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert size={18} className="text-amber-400" />
            <h2 className="text-lg font-semibold text-white">Alert Rules</h2>
          </div>
          <button
            onClick={() => setShowAlertForm(true)}
            className="flex items-center gap-1 text-emerald-400 hover:text-emerald-300 text-sm font-medium transition-colors"
          >
            <Plus size={16} />
            Add Rule
          </button>
        </div>
        {alertRules.length > 0 ? (
          <div className="divide-y divide-slate-800">
            {alertRules.map((rule) => (
              <div key={rule.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="text-white text-sm font-medium">
                    {ruleTypeLabel(rule.rule_type)}
                  </p>
                  <p className="text-slate-400 text-xs mt-0.5">
                    {rule.rule_type === 'price_drop'
                      ? 'Triggers on any price decrease'
                      : rule.rule_type === 'price_change_pct'
                      ? `Threshold: ${rule.threshold}%`
                      : `Threshold: ${product.currency || '$'}${Number(rule.threshold).toFixed(2)}`}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs ${
                      rule.is_active
                        ? 'bg-emerald-500/15 text-emerald-400'
                        : 'bg-slate-700 text-slate-400'
                    }`}
                  >
                    {rule.is_active ? 'Active' : 'Disabled'}
                  </span>
                  <button
                    onClick={() => setConfirmDeleteRuleId(rule.id)}
                    className="text-slate-500 hover:text-red-400 transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500">
            No alert rules configured. Add one to get notified of price changes.
          </div>
        )}
      </div>

      {/* {priceHistory.length > 0 && <div>chart summary here</div>} */}

      <div className="bg-slate-900 border border-slate-800 rounded-xl">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Price History Data</h2>
          {priceHistory.length > 0 && (
            <button
              onClick={handleExportCsv}
              className="flex items-center gap-1.5 text-emerald-400 hover:text-emerald-300 text-sm font-medium transition-colors"
            >
              <Download size={14} />
              Export CSV
            </button>
          )}
        </div>
        {priceHistory.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No price history available</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="text-left text-xs font-medium text-slate-400 uppercase tracking-wider px-5 py-3">
                    Date
                  </th>
                  <th className="text-right text-xs font-medium text-slate-400 uppercase tracking-wider px-5 py-3">
                    Price
                  </th>
                  <th className="text-left text-xs font-medium text-slate-400 uppercase tracking-wider px-5 py-3">
                    Currency
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {[...priceHistory]
                  .sort(
                    (a, b) =>
                      new Date(b.scraped_at).getTime() - new Date(a.scraped_at).getTime()
                  )
                  .slice(0, 20)
                  .map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-800/50">
                      <td className="px-5 py-3 text-sm text-slate-300">
                        {formatDateTime(entry.scraped_at)}
                      </td>
                      <td className="px-5 py-3 text-sm text-white font-medium text-right">
                        {Number(entry.price).toFixed(2)}
                      </td>
                      <td className="px-5 py-3 text-sm text-slate-400">{entry.currency}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showAlertForm && (
        <AlertRuleForm
          onSubmit={handleCreateAlert}
          onClose={() => setShowAlertForm(false)}
        />
      )}

      {showEditModal && (
        <EditProductModal
          product={product}
          onClose={() => setShowEditModal(false)}
          onSaved={handleProductSaved}
        />
      )}

      <ConfirmDialog
        open={confirmDeleteProduct}
        title="Delete Product"
        message="Are you sure you want to delete this product? All price history and alert rules will be permanently removed."
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => {
          setConfirmDeleteProduct(false);
          handleDelete();
        }}
        onCancel={() => setConfirmDeleteProduct(false)}
      />

      <ConfirmDialog
        open={confirmDeleteRuleId !== null}
        title="Delete Alert Rule"
        message="Are you sure you want to delete this alert rule?"
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => {
          if (confirmDeleteRuleId !== null) {
            handleDeleteAlert(confirmDeleteRuleId);
            setConfirmDeleteRuleId(null);
          }
        }}
        onCancel={() => setConfirmDeleteRuleId(null)}
      />
    </div>
  );
}
