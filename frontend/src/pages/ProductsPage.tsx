import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  Plus,
  Loader2,
  AlertCircle,
  ExternalLink,
  Clock,
  Search,
  ChevronUp,
  ChevronDown,
  LayoutGrid,
  List,
  ChevronLeft,
  ChevronRight,
  Trash2,
  Pause,
  Play,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { getProducts, createProduct, updateProduct, deleteProducts } from '../api/products';
import { getPriceHistory } from '../api/priceHistory';
import ProductCard from '../components/ProductCard';
import { ProductTableSkeleton } from '../components/Skeleton';
import { useToast } from '../context/ToastContext';
import { getFaviconUrl } from '../utils/favicon';
import { formatRelativeTime } from '../utils/formatTime';
import type { Product, ProductCreateData } from '../types';

type SortField = 'name' | 'current_price' | 'last_scraped_at' | 'created_at';
type SortDir = 'asc' | 'desc';
type ViewMode = 'table' | 'card';

const ITEMS_PER_PAGE = 10;
const VIEW_MODE_KEY = 'pricepulse_view_mode';

function truncateUrl(url: string, maxLen = 50): string {
  try {
    const parsed = new URL(url);
    const display = parsed.hostname + parsed.pathname;
    return display.length > maxLen ? display.slice(0, maxLen) + '...' : display;
  } catch {
    return url.length > maxLen ? url.slice(0, maxLen) + '...' : url;
  }
}

function SortIcon({ field, sortField, sortDir }: { field: SortField; sortField: SortField; sortDir: SortDir }) {
  if (field !== sortField) {
    return <ChevronUp size={14} className="text-slate-700" />;
  }
  return sortDir === 'asc'
    ? <ChevronUp size={14} className="text-emerald-400" />
    : <ChevronDown size={14} className="text-emerald-400" />;
}

function PriceTrendBadge({ trend }: { trend: 'up' | 'down' | 'flat' | null }) {
  if (!trend) return null;
  if (trend === 'down') {
    return (
      <span className="inline-flex items-center gap-0.5 ml-1.5 text-xs font-medium text-emerald-400">
        <TrendingDown size={12} />
      </span>
    );
  }
  if (trend === 'up') {
    return (
      <span className="inline-flex items-center gap-0.5 ml-1.5 text-xs font-medium text-red-400">
        <TrendingUp size={12} />
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-0.5 ml-1.5 text-xs font-medium text-slate-500">
      <Minus size={12} />
    </span>
  );
}

function StatusBadge({ product }: { product: Product }) {
  if (product.current_price === null && product.last_scraped_at) {
    return (
      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/15 text-red-400">
        Error
      </span>
    );
  }
  if (product.current_price === null && !product.last_scraped_at) {
    return (
      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-500/15 text-yellow-400">
        Pending
      </span>
    );
  }
  if (!product.is_active) {
    return (
      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-700 text-slate-400">
        Paused
      </span>
    );
  }
  return (
    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400">
      Active
    </span>
  );
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const [newUrl, setNewUrl] = useState('');
  const [newPlatform, setNewPlatform] = useState('');
  const [newInterval, setNewInterval] = useState('6h');
  const [addLoading, setAddLoading] = useState(false);

  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    const stored = localStorage.getItem(VIEW_MODE_KEY);
    return stored === 'card' ? 'card' : 'table';
  });

  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [priceTrends, setPriceTrends] = useState<Record<number, 'up' | 'down' | 'flat'>>({});

  const searchRef = useRef<HTMLInputElement>(null);
  const { addToast } = useToast();

  const loadProducts = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError('');
    try {
      const res = await getProducts(1, 500);
      setProducts(res.items);
    } catch {
      if (!silent) setError('Failed to load products');
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (!document.hidden) loadProducts(true);
    }, 60000);
    return () => clearInterval(interval);
  }, [loadProducts]);

  useEffect(() => {
    localStorage.setItem(VIEW_MODE_KEY, viewMode);
  }, [viewMode]);

  useEffect(() => {
    setPage(1);
  }, [search, sortField, sortDir]);

  useEffect(() => {
    if (products.length > 0) {
      loadPriceTrends(products);
    }
  }, [products]);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';

      if (e.key === 'Escape' && showAddModal) {
        setShowAddModal(false);
        return;
      }
      if (e.key === 'Escape' && showDeleteConfirm) {
        setShowDeleteConfirm(false);
        return;
      }
      if (e.key === '/' && !isInput) {
        e.preventDefault();
        searchRef.current?.focus();
        return;
      }
      if (e.key === 'n' && !isInput && !showAddModal) {
        setShowAddModal(true);
        return;
      }
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [showAddModal, showDeleteConfirm]);

  async function loadPriceTrends(prods: Product[]) {
    const trends: Record<number, 'up' | 'down' | 'flat'> = {};
    const fetches = prods
      .filter((p) => p.current_price !== null && p.last_scraped_at)
      .map(async (p) => {
        try {
          const history = await getPriceHistory(String(p.id), { limit: 2 });
          if (history.length >= 2) {
            const prev = history[1].price;
            const curr = history[0].price;
            if (curr < prev) trends[p.id] = 'down';
            else if (curr > prev) trends[p.id] = 'up';
            else trends[p.id] = 'flat';
          }
        } catch {
          // skip
        }
      });
    await Promise.all(fetches);
    setPriceTrends(trends);
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setAddLoading(true);
    try {
      const data: ProductCreateData = {
        url: newUrl,
        platform: newPlatform || undefined,
        scrape_interval: newInterval || '6h',
      };
      const product = await createProduct(data);
      setProducts((prev) => [product, ...prev]);
      setShowAddModal(false);
      setNewUrl('');
      setNewPlatform('');
      setNewInterval('6h');
      addToast('Product added', 'success');
    } catch {
      setError('Failed to add product');
    } finally {
      setAddLoading(false);
    }
  }

  const handleToggleActive = useCallback(async (id: number, newActive: boolean) => {
    try {
      await updateProduct(String(id), { is_active: newActive });
      setProducts((prev) =>
        prev.map((p) => (p.id === id ? { ...p, is_active: newActive } : p))
      );
      addToast(newActive ? 'Tracking resumed' : 'Tracking paused', 'info');
    } catch {
      setError('Failed to update product');
    }
  }, [addToast]);

  function toggleSelect(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleBulkDelete() {
    setDeleteLoading(true);
    try {
      const idsArr = Array.from(selectedIds);
      await deleteProducts(idsArr);
      setProducts((prev) => prev.filter((p) => !selectedIds.has(p.id)));
      addToast(`${selectedIds.size} product${selectedIds.size > 1 ? 's' : ''} deleted`, 'success');
      setSelectedIds(new Set());
      setShowDeleteConfirm(false);
    } catch {
      setError('Failed to delete products');
    } finally {
      setDeleteLoading(false);
    }
  }

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir(field === 'name' ? 'asc' : 'desc');
    }
  }

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return products.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.url.toLowerCase().includes(q)
    );
  }, [products, search]);

  const sorted = useMemo(() => {
    const arr = [...filtered];
    arr.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'name':
          cmp = a.name.localeCompare(b.name);
          break;
        case 'current_price': {
          const pa = a.current_price ?? -Infinity;
          const pb = b.current_price ?? -Infinity;
          cmp = pa - pb;
          break;
        }
        case 'last_scraped_at': {
          const da = a.last_scraped_at ? new Date(a.last_scraped_at).getTime() : 0;
          const db = b.last_scraped_at ? new Date(b.last_scraped_at).getTime() : 0;
          cmp = da - db;
          break;
        }
        case 'created_at': {
          const ca = new Date(a.created_at).getTime();
          const cb = new Date(b.created_at).getTime();
          cmp = ca - cb;
          break;
        }
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return arr;
  }, [filtered, sortField, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / ITEMS_PER_PAGE));
  const safePage = Math.min(page, totalPages);

  const paginatedProducts = useMemo(() => {
    const start = (safePage - 1) * ITEMS_PER_PAGE;
    return sorted.slice(start, start + ITEMS_PER_PAGE);
  }, [sorted, safePage]);

  function toggleSelectAll() {
    if (selectedIds.size === paginatedProducts.length && paginatedProducts.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(paginatedProducts.map((p) => p.id)));
    }
  }

  if (loading) {
    return <ProductTableSkeleton />;
  }

  const thSortable = 'text-left text-xs font-medium uppercase tracking-wider px-5 py-3 cursor-pointer select-none hover:text-slate-200 transition-colors';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Products</h1>
          <p className="text-slate-400 mt-1">{products.length} products tracked</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={16} />
          Add Product
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
          <button onClick={() => setError('')} className="ml-auto text-red-400 hover:text-red-300">&times;</button>
        </div>
      )}

      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            ref={searchRef}
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search products..."
            className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-10 pr-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 placeholder:text-slate-600"
          />
        </div>
        <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-0.5">
          <button
            onClick={() => setViewMode('table')}
            className={`p-2 rounded-md transition-colors ${
              viewMode === 'table' ? 'bg-slate-700 text-white' : 'text-slate-500 hover:text-slate-300'
            }`}
            title="Table view"
          >
            <List size={16} />
          </button>
          <button
            onClick={() => setViewMode('card')}
            className={`p-2 rounded-md transition-colors ${
              viewMode === 'card' ? 'bg-slate-700 text-white' : 'text-slate-500 hover:text-slate-300'
            }`}
            title="Card view"
          >
            <LayoutGrid size={16} />
          </button>
        </div>
      </div>

      {viewMode === 'table' ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="px-5 py-3 w-10">
                    <input
                      type="checkbox"
                      checked={paginatedProducts.length > 0 && selectedIds.size === paginatedProducts.length}
                      onChange={toggleSelectAll}
                      className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500/50 focus:ring-offset-0 cursor-pointer"
                    />
                  </th>
                  <th className={`${thSortable} text-slate-400`} onClick={() => handleSort('name')}>
                    <span className="flex items-center gap-1">
                      Product
                      <SortIcon field="name" sortField={sortField} sortDir={sortDir} />
                    </span>
                  </th>
                  <th className="text-left text-xs font-medium text-slate-400 uppercase tracking-wider px-5 py-3">
                    URL
                  </th>
                  <th className={`${thSortable} text-right text-slate-400`} onClick={() => handleSort('current_price')}>
                    <span className="flex items-center justify-end gap-1">
                      Price
                      <SortIcon field="current_price" sortField={sortField} sortDir={sortDir} />
                    </span>
                  </th>
                  <th className={`${thSortable} text-slate-400`} onClick={() => handleSort('last_scraped_at')}>
                    <span className="flex items-center gap-1">
                      Last Scraped
                      <SortIcon field="last_scraped_at" sortField={sortField} sortDir={sortDir} />
                    </span>
                  </th>
                  <th className="text-left text-xs font-medium text-slate-400 uppercase tracking-wider px-5 py-3">
                    Status
                  </th>
                  <th className="text-center text-xs font-medium text-slate-400 uppercase tracking-wider px-5 py-3">
                    Tracking
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {paginatedProducts.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-5 py-8 text-center text-slate-500">
                      {search ? 'No products match your search' : 'No products yet. Add one to get started!'}
                    </td>
                  </tr>
                ) : (
                  paginatedProducts.map((product) => (
                    <tr
                      key={product.id}
                      className={`hover:bg-slate-800/50 transition-colors ${
                        selectedIds.has(product.id) ? 'bg-slate-800/30' : ''
                      }`}
                    >
                      <td className="px-5 py-4">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(product.id)}
                          onChange={() => toggleSelect(product.id)}
                          className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500/50 focus:ring-offset-0 cursor-pointer"
                        />
                      </td>
                      <td className="px-5 py-4">
                        <Link
                          to={`/products/${product.id}`}
                          className="flex items-center gap-2 text-white font-medium hover:text-emerald-400 transition-colors"
                        >
                          <img
                            src={getFaviconUrl(product.url)}
                            alt=""
                            className="w-4 h-4 rounded-sm flex-shrink-0"
                            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                          />
                          {product.name}
                        </Link>
                      </td>
                      <td className="px-5 py-4">
                        <a
                          href={product.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-slate-400 text-sm hover:text-emerald-400 flex items-center gap-1 transition-colors"
                        >
                          {truncateUrl(product.url)}
                          <ExternalLink size={12} />
                        </a>
                      </td>
                      <td className="px-5 py-4 text-right">
                        <span className="text-white font-semibold inline-flex items-center">
                          {product.current_price !== null
                            ? `${product.currency || '$'}${Number(product.current_price).toFixed(2)}`
                            : 'N/A'}
                          <PriceTrendBadge trend={priceTrends[product.id] ?? null} />
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <span className="text-slate-400 text-sm flex items-center gap-1">
                          <Clock size={12} />
                          {product.last_scraped_at
                            ? formatRelativeTime(product.last_scraped_at)
                            : 'Never'}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <StatusBadge product={product} />
                      </td>
                      <td className="px-5 py-4 text-center">
                        <button
                          onClick={() => handleToggleActive(product.id, !product.is_active)}
                          className={`p-1.5 rounded-lg transition-colors ${
                            product.is_active
                              ? 'text-slate-400 hover:text-yellow-400 hover:bg-yellow-500/10'
                              : 'text-yellow-400 hover:text-emerald-400 hover:bg-emerald-500/10'
                          }`}
                          title={product.is_active ? 'Pause tracking' : 'Resume tracking'}
                        >
                          {product.is_active ? <Pause size={14} /> : <Play size={14} />}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {paginatedProducts.length === 0 ? (
            <div className="col-span-full text-center text-slate-500 py-8">
              {search ? 'No products match your search' : 'No products yet. Add one to get started!'}
            </div>
          ) : (
            paginatedProducts.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                selected={selectedIds.has(product.id)}
                onSelect={toggleSelect}
                onToggleActive={handleToggleActive}
                priceTrend={priceTrends[product.id] ?? null}
              />
            ))
          )}
        </div>
      )}

      {sorted.length > ITEMS_PER_PAGE && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-500">
            Showing {(safePage - 1) * ITEMS_PER_PAGE + 1}&ndash;{Math.min(safePage * ITEMS_PER_PAGE, sorted.length)} of {sorted.length}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={safePage <= 1}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-300 bg-slate-900 border border-slate-800 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft size={14} />
              Previous
            </button>
            <span className="text-sm text-slate-400 px-2">
              Page {safePage} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={safePage >= totalPages}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-300 bg-slate-900 border border-slate-800 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Next
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {selectedIds.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-slate-800 border border-slate-700 rounded-xl px-5 py-3 flex items-center gap-4 shadow-2xl shadow-black/50 z-50">
          <span className="text-sm text-slate-300">
            {selectedIds.size} selected
          </span>
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium text-red-400 bg-red-500/10 hover:bg-red-500/20 transition-colors"
          >
            <Trash2 size={14} />
            Delete Selected
          </button>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-sm text-slate-500 hover:text-slate-300 transition-colors"
          >
            Clear
          </button>
        </div>
      )}

      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-sm">
            <div className="p-5">
              <h3 className="text-lg font-semibold text-white mb-2">Delete Products</h3>
              <p className="text-slate-400 text-sm">
                Are you sure you want to delete {selectedIds.size} product{selectedIds.size > 1 ? 's' : ''}? This action cannot be undone.
              </p>
            </div>
            <div className="flex gap-3 p-5 pt-0">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleteLoading}
                className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleBulkDelete}
                disabled={deleteLoading}
                className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium text-white bg-red-600 hover:bg-red-500 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
              >
                {deleteLoading ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Deleting...
                  </>
                ) : (
                  'Delete'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-md">
            <div className="p-5 border-b border-slate-800">
              <h3 className="text-lg font-semibold text-white">Add New Product</h3>
            </div>
            <form onSubmit={handleAdd} className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Product URL *
                </label>
                <input
                  type="url"
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  placeholder="https://..."
                  required
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 placeholder:text-slate-600"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Platform
                  </label>
                  <input
                    type="text"
                    value={newPlatform}
                    onChange={(e) => setNewPlatform(e.target.value)}
                    placeholder="e.g. Amazon"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 placeholder:text-slate-600"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Scrape Interval
                  </label>
                  <select
                    value={newInterval}
                    onChange={(e) => setNewInterval(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500"
                  >
                    <option value="1h">1 hour</option>
                    <option value="6h">6 hours</option>
                    <option value="12h">12 hours</option>
                    <option value="24h">24 hours</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
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
